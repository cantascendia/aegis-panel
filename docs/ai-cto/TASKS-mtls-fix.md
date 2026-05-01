# TASKS — L-032 panel↔marznode gRPC mTLS 修复

> 状态：**TASKS**（spec-driven phase 3/3，等 PLAN merged 后才能开始）
> 上游：SPEC-mtls-fix.md（merged） + PLAN-mtls-fix.md（pending merge PR #157）
> 下游：实现 + AC 验证 + LESSONS L-032 闭环

---

## T0：前置（5 min）

- [ ] T0.1 通知 friend_b/c 维护时段（TBD-2 锁定 C 路径）：
  - 文案模板：`晚上 X:XX-Y:YY 后端维护，期间订阅可能短暂断 1-2 分钟，已恢复后照常用，不必重新导入订阅`
- [ ] T0.2 SSH 备份当前 xray_config.json + .env 到 `/opt/aegis-backup-mtls-fix/<ts>/`
- [ ] T0.3 记录基线：`select id, username from users` + `jq '.inbounds[].settings.clients' xray_config.json`
- [ ] T0.4 确认回滚脚本：`/usr/local/bin/aegis-mtls-rollback`（T1.4 写）

---

## T1：Phase A — 数据净化 + H-E 实证（45 min）

### T1.1 SSH + 备份（沿用 T0.2）

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 "
TS=\$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/aegis-backup-mtls-fix/\$TS
cp /opt/aegis/data/marznode/xray_config.json /opt/aegis-backup-mtls-fix/\$TS/
cp /opt/aegis/.env /opt/aegis-backup-mtls-fix/\$TS/
echo \"backup at /opt/aegis-backup-mtls-fix/\$TS\"
"
```

### T1.2 清空 clients

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 '
F=/opt/aegis/data/marznode/xray_config.json
jq ".inbounds[].settings.clients = []" "$F" > "$F.tmp" && mv "$F.tmp" "$F"
echo "clients cleared:"
jq ".inbounds[].settings.clients | length" "$F"
'
```

### T1.3 重启 marznode

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 "
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml restart marznode
"
```

### T1.4 写回滚脚本（在执行 T1.5 前）

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 'cat > /usr/local/bin/aegis-mtls-rollback << "EOF"
#!/usr/bin/env bash
# Restore xray_config.json from latest backup + restart marznode
set -euo pipefail
LATEST=$(ls -1dt /opt/aegis-backup-mtls-fix/*/ 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "no backup found"; exit 2
fi
cp "${LATEST}xray_config.json" /opt/aegis/data/marznode/xray_config.json
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml restart marznode
echo "rolled back to $LATEST"
EOF
chmod +x /usr/local/bin/aegis-mtls-rollback'
```

### T1.5 等待 + 观察 panel 自动 sync（60s）

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 "
echo '--- waiting 60s for _monitor_channel to reconnect + _sync ---'
sleep 60
echo
echo '=== panel logs (filtered for sync activity) ==='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml logs --since=2m panel 2>&1 | grep -iE 'connected to node|opened the stream|_sync|_repopulate|GRPCError|StreamTerminat' | tail -20
echo
echo '=== xray_config clients now ==='
jq '.inbounds[].settings.clients | length' /opt/aegis/data/marznode/xray_config.json
jq -r '.inbounds[].settings.clients[] | .email + \"=\" + .id' /opt/aegis/data/marznode/xray_config.json 2>&1 | head -10
"
```

**判定**：
- clients 长度 ≥ 4 + log 含 `Connected to node` / `opened the stream` → ✅ H-E 正确，跳到 T4 验证
- clients 仍 0 → ❌ H-E 不全对，进 T2 Phase B

---

## T2：Phase B — 仅 T1 失败时（90 min）

### T2.1 启用 panel verbose log + 抓 _sync 异常

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 "
# 临时改 .env 加 LOG_LEVEL（如果 panel 支持）
grep -q '^LOG_LEVEL=' /opt/aegis/.env || echo 'LOG_LEVEL=DEBUG' >> /opt/aegis/.env
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml up -d --force-recreate panel
"
```

### T2.2 直接调 grpclib._sync 看异常

```bash
ssh -i ~/.ssh/id_ed25519 root@202.182.120.132 'docker exec aegis-panel python3 << "EOF"
import asyncio, traceback
from app.db import GetDB
from app.marznode.grpclib import MarzNodeGRPCLIB
from app.db import models as m

with GetDB() as db:
    node = db.query(m.Node).first()
    cert = open("/etc/marzneshin/ssl_client_cert.pem").read() if False else None  # TBD locate
    # Fallback: panel issues its own cert via NodeSettings; need to construct from DB
    # ... skip if too complex, rely on logs from T2.1

print("inspect logs from T2.1 instead")
EOF'
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml logs --since=3m panel 2>&1 | grep -B2 -A10 -iE 'sync failed|GRPCError|StreamTerminat|RepopulateUsers' | tail -50
```

### T2.3 修代码（grpclib.py）

**改动 1**：line 88-90 显式记录异常
```python
# 改前
try:
    await self._sync()
except:
    pass

# 改后
try:
    await self._sync()
except Exception as e:
    logger.error("sync failed for node %i: %s", self.id, e, exc_info=True)
    # 不 raise — 即使 sync 失败也要让 streaming task spawn（改动 2）
```

**改动 2**：streaming task 与 sync 解耦（line 86-95 重构）
```python
# 改前
if not self.synced:
    try:
        await self._sync()
    except:
        pass
    else:
        self._streaming_task = asyncio.create_task(
            self._stream_user_updates()
        )
        self.set_status(NodeStatus.healthy)

# 改后
if not self.synced:
    try:
        await self._sync()
    except Exception as e:
        logger.error("sync failed for node %i: %s — will retry next loop", self.id, e, exc_info=True)
    # 无论 sync 是否成功都 spawn streaming task；如果 SyncUsers RPC 在 marznode
    # 端被拒，stream 会抛 GRPCError 自然 cleanup，下个 _monitor_channel 循环重试
    if not self._streaming_task or self._streaming_task.done():
        self._streaming_task = asyncio.create_task(self._stream_user_updates())
    self.set_status(NodeStatus.healthy)
```

**新增 unit test** `tests/test_marznode_grpclib_sync.py`：
- mock `_fetch_backends` 抛异常 → assert `_streaming_task` 仍 spawn
- mock `_repopulate_users` 抛异常 → assert `_streaming_task` 仍 spawn
- mock 一切成功 → assert task spawn + status=healthy

### T2.4 build v0.3.6 + roll

- branch `fix/mtls-grpclib-decouple-streaming`
- commit + push + PR + codex review + self-merge
- tag v0.3.6 + 等 ghcr build
- `aegis-upgrade v0.3.6`

---

## T3：Phase C — workaround（仅 T1+T2 都失败时）

### T3.1 写 `scripts/aegis-sync-clients.sh`

```bash
#!/usr/bin/env bash
# 半自动同步：DB users → xray_config.json clients → restart marznode
set -euo pipefail
DB=/opt/aegis/data/panel/db.sqlite3
XRAY=/opt/aegis/data/marznode/xray_config.json
COMPOSE=/opt/aegis-src/deploy/compose/docker-compose.sqlite.yml

# 备份
cp "$XRAY" "$XRAY.bak.$(date +%s)"

# 从 DB 拉 users，组装 clients 数组
CLIENTS_JSON=$(docker exec aegis-panel python3 -c "
import sqlite3, json
c = sqlite3.connect('/var/lib/marzneshin/db.sqlite3')
clients = []
for row in c.execute('select id, username, key from users where removed=0'):
    uid, uname, key = row
    clients.append({'id': key, 'email': str(uid), 'flow': 'xtls-rprx-vision'})
print(json.dumps(clients))
")

# 写入 xray_config
jq --argjson cs "$CLIENTS_JSON" '.inbounds[].settings.clients = $cs' "$XRAY" > "$XRAY.tmp"
mv "$XRAY.tmp" "$XRAY"

# 重启 marznode
docker compose -f "$COMPOSE" restart marznode
echo "synced $(echo "$CLIENTS_JSON" | jq 'length') clients to xray_config.json"
```

### T3.2 install.sh 自动部署

类似 `deploy_aegis_upgrade_script`，加 `deploy_aegis_sync_clients_script`。

### T3.3 文档：`docs/ai-cto/OPS-mtls-workaround.md`

操作员手册：每次 panel 增删用户后跑 `aegis-sync-clients`。

---

## T4：Phase D — AC-1..8 端到端验证（30 min）

| AC | 命令 | 通过 |
|---|---|---|
| AC-1 | `curl -X POST /api/users -d '{"username":"test_e2e","data_limit":...}' && sleep 5 && jq ... clients` | client UUID 存在 |
| AC-2 | `curl -X DELETE /api/users/test_e2e && sleep 5 && jq` | client UUID 消失 |
| AC-3 | `docker logs aegis-marznode --since=5m \| grep "ValueError int" \| wc -l` | =0 |
| AC-4 | 手机 v2rayNG → friend_b 订阅 → ip.sb | 日本 IP |
| AC-5 | `curl /api/nodes/1/inbounds` | HTTP 200 |
| AC-6 | `select status,message from nodes` | healthy / NULL |
| AC-7 | rollback 演练（aegis-mtls-rollback） + 计时 | ≤30s |
| AC-8 | `docker restart aegis-marznode && sleep 30 && diff <(jq...) <(sql...)` | 完全一致 |

每个 AC pass 在 commit message 列出。

---

## T5：知识固化（30 min）

- [ ] T5.1 LESSONS.md 加 L-032 闭环条目（保留原诊断 + 加最终根因 + 修复路径）
- [ ] T5.2 STATUS.md late-8 wave-2 更新（main thread 收口）
- [ ] T5.3 DECISIONS.md：D-### "panel↔marznode gRPC = grpclib only（grpcio insecure_channel 永久标 deprecated）" + D-### "xray client email 字段 = `<panel_user_id>` 纯数字"
- [ ] T5.4 evals/regression/005-mtls-fix-acceptance.yaml ship（PLAN §5 雏形落地）
- [ ] T5.5 OPS runbook 更新（`docs/ai-cto/OPS-deploy-runbook.md` 删除 "手工注 UUID" 步骤）

---

## T6：清理

- [ ] T6.1 关 `LOG_LEVEL=DEBUG`（如果 T2.1 开过）
- [ ] T6.2 删 friend_b/c 维护通知群消息
- [ ] T6.3 v0.3.6（如 Phase B 触发）docker images prune 旧版本
- [ ] T6.4 关 PR #157 PLAN（merge），关 PR #158（如 Phase B 触发）

---

## 进入实现阶段 checklist

- [x] SPEC merged
- [x] PLAN merged + codex reviewed
- [ ] TASKS merged + codex reviewed（本文件）
- [ ] friend_b/c 通知发出 + 维护时段确认
- [ ] T0 备份脚本验证可执行
- [ ] T1.4 回滚脚本预发到 VPS
- [ ] T2.3 unit test 雏形写好（仅 Phase B 触发时）

执行顺序：T0 → T1 → (判定 T1 通过否) → T4 ✅ OR (T2 → T4) ✅ OR (T3 → 文档) → T5 → T6
