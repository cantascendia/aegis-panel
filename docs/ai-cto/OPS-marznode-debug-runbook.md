# OPS — marznode 调试 runbook（防再被诊断 endpoint 误导）

> 起源：L-035/L-036/L-037。wave-2/3/4 全程被错误的"诊断 endpoint"误导，
> 烧了一整天精力修"不工作的 RPC"，**实际 RPC 早就工作了**。本 runbook
> 给操作员一套**可信的观测信号**清单，避免再踩坑。

---

## 问题描述

panel 创建 / 删除 / 修改用户后，怀疑没同步到 marznode（节点客户端连不上）。

---

## ❌ 不要看（误导信号）

| 看错了什么 | 为什么不可信 |
|---|---|
| `GET /api/nodes/{id}/xray/config` 返回的 clients[] | **返回的是 boot-time `xray_config.json` 文件**，不是 xray-core 内存运行时。marznode 通过 xray gRPC `add_inbound_user` 动态加用户，**不写回文件**。文件视角看"没变化"≠ 同步失败。 |
| `cat /opt/aegis/data/marznode/xray_config.json` | 同上 — 文件是 boot-time snapshot |
| panel `node.status='unhealthy'` | wave-3 v0.3.7 加 N=3 consecutive timeout 后才会标 unhealthy；瞬时 unhealthy 不代表 RPC 真断 |
| panel `node.message='timeout'` | 历史值，可能是 18 小时前的；看 `last_status_change` 字段才知道更新时间 |

---

## ✅ 可信观测信号

### 信号 1：panel 用户活跃数（最简单）

```bash
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=riku&password=...' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8443/api/system/stats/users
# {"total":N, "active":M, ...}
```

创建一个用户 → `active` count +1 → ✅ 同步成功。

### 信号 2：panel grpcio INFO 日志（v0.3.8+）

```bash
docker compose logs --since=30s panel | grep -iE 'syncusers|stream|queue'
```

期待的日志序列（v0.3.8 之后永久打开）：
```
Connected to node 1
node 1: SyncUsers stream opening
node 1: SyncUsers stream opened, awaiting queue
node 1: queueing update_user user=alice id=99 inbounds=['Reality-VLESS']
node 1: dequeued user alice (id=99)
node 1: wrote user alice to SyncUsers stream
```

任意一行缺 → 链断在该步。

### 信号 3：marznode DEBUG 日志（临时打开）

DEBUG 默认关闭（性能 + 日志体积）。**调试时**临时打开：

```bash
# 1. 编辑 compose 加 DEBUG: "True" 到 marznode 的 environment 块
sed -i '/INSECURE: "True"/a\      DEBUG: "True"  # tmp debug — REVERT' \
  /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml

# 2. 重建容器
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  --env-file /opt/aegis/.env up -d --force-recreate marznode

# 3. 看 DEBUG 日志
docker compose logs --since=30s marznode | grep -iE 'adding user|removing user'
```

期待：
```
DEBUG - marznode.service.service: adding user `alice` to inbound `Reality-VLESS`
DEBUG - marznode.backends.xray.xray_backend: xtls-rprx-vision
```

调完**必须 revert**：
```bash
sed -i '/DEBUG: "True"  # tmp debug — REVERT/d' \
  /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  --env-file /opt/aegis/.env up -d --force-recreate marznode
```

### 信号 4：客户端真实连接（终极测试）

让一个测试账号在 v2rayNG / Shadowrocket 客户端按订阅 URL 连接：
- 连得上 + ip.sb 显示节点 IP → 同步真成功
- 连不上 → 同步真有问题

---

## 常见 bug 模式 + 对应信号

| bug | 信号 1（active） | 信号 2（panel log） | 信号 3（marznode log） | 信号 4（客户端） |
|---|---|---|---|---|
| panel↔marznode RPC 断（L-036 marznode v0.2.0） | 不变 | 无 `Connected to node` / 有 `Missing content-type` | 无 `adding user` | 连不上 |
| streaming task 死（L-032 wave-2） | 增 / 减 | `queueing` 有但 `dequeued` 无 | 无 `adding user` | 连不上 |
| 增量 RPC OK 但 xray API 调用失败 | 增 / 减 | `wrote` 有 | `adding user` 有，但 xray_backend 行无 | 连不上 |
| 一切正常 | 增 / 减 | 4 行全 | `adding user` + `xtls-rprx-vision` | ✅ |

---

## 快速诊断 1 分钟脚本

```bash
ssh root@VPS << 'PYEOF'
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=riku&password=PANEL_PASS' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

echo '=== 1. active count ==='
curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8443/api/system/stats/users

echo
echo '=== 2. panel grpcio recent activity ==='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  logs --since=2m panel 2>&1 | grep -iE 'syncusers|connected to node|missing content' | tail -5

echo
echo '=== 3. node DB row ==='
docker exec aegis-panel python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/marzneshin/db.sqlite3')
print(c.execute('select id, status, message, connection_backend, last_status_change from nodes').fetchone())
"

echo
echo '=== 4. marznode INSECURE + image ==='
docker exec aegis-marznode env | grep -E 'INSECURE|MARZNODE'
docker inspect aegis-marznode --format '{{.Config.Image}}'
PYEOF
```

---

## 如果同步真断了

按 ROI 顺序：

1. **先 PUT 节点触发重同步**（最便宜）：
   ```bash
   TOKEN=...
   NODE=$(curl -fsS -H "Authorization: Bearer $TOKEN" .../api/nodes/1)
   curl -X PUT .../api/nodes/1 -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d "$NODE"
   ```
   → panel 重新 `add_node` → fresh `_monitor_channel` + `_sync` → RepopulateUsers
   → 5 秒内全部用户重新推送

2. **再用 aegis-sync-clients 兜底**（最可靠）：
   ```bash
   aegis-sync-clients
   ```
   → 直接读 panel DB 重写 xray_config.json + restart marznode

3. **panel 重启**（如果 panel 端 streaming task 全死）：
   ```bash
   docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
     --env-file /opt/aegis/.env up -d --force-recreate panel
   ```

4. **检查 panel↔marznode 版本匹配**（L-036）：
   - panel 必须 ≥ v0.3.6（grpcio backend + Backend gRPC API）
   - marznode 必须 ≥ v0.5.0（Backend API + 真 INSECURE 支持）
   - `MARZNODE_VERSION=v0.5.7` in /opt/aegis/.env

---

## 参考

- L-032：streaming task 取消 race（wave-2 workaround + wave-3 监控修）
- L-034：BaseHTTPMiddleware × FastAPI 0.115+ scope 兼容性（wave-6 pure ASGI 修）
- L-035：误判 TLS 错位（wave-3 假设修正）
- L-036：marznode 版本错位（wave-4 真根因，v0.5.7 升级）
- L-037：诊断 endpoint 误导，**RPC 一直在工作**（wave-5 顿悟）
