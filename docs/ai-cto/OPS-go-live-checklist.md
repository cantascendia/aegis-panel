# OPS — GO-LIVE Checklist（首位付费客户前自检）

> 防止 paid customer 撞 silent bug：在邀第一个付费客户前，跑完本清单。
> 每项 PASS 才算"可邀客户"。

---

## ① 基础设施健康（5 分钟）

```bash
ssh root@VPS << 'EOF'
echo '== 1. Panel image is current ($AEGIS_VERSION matches latest tag) =='
docker inspect aegis-panel --format '{{.Config.Image}}'
grep AEGIS_VERSION /opt/aegis/.env

echo
echo '== 2. Marznode v0.5.7+ (Backend API) =='
docker inspect aegis-marznode --format '{{.Config.Image}}'
grep MARZNODE_VERSION /opt/aegis/.env

echo
echo '== 3. Both containers healthy =='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml ps

echo
echo '== 4. Panel API live =='
curl -fsS -o /dev/null -w '/openapi.json HTTP %{http_code}\n' http://127.0.0.1:8443/openapi.json
EOF
```

**期望**：panel + marznode `Up (healthy)`；panel `/openapi.json` 200。

---

## ② panel↔marznode RPC 连通（3 分钟）

```bash
ssh root@VPS << 'EOF'
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=ADMIN&password=PASS' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

echo '== 5. Node connection_backend = grpcio (匹配 marznode INSECURE=True) =='
curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8443/api/nodes | \
  python3 -c 'import json,sys; [print(n["name"], n["connection_backend"], n["status"]) for n in json.loads(sys.stdin.read())["items"]]'

echo
echo '== 6. Panel grpcio connected log =='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  logs --since=5m panel 2>&1 | grep -iE 'Connected to node|SyncUsers stream' | tail -3
EOF
```

**期望**：node `grpcio` + `healthy`；panel log 含 `Connected to node 1` 和 `SyncUsers stream opened`。

❌ 若缺 `Connected to node` → 走 `OPS-marznode-debug-runbook.md` 诊断。

---

## ③ 用户增删 RPC 端到端（2 分钟）

```bash
ssh root@VPS << 'EOF'
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=ADMIN&password=PASS' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

count() {
  curl -fsS -H "Authorization: Bearer $TOKEN" \
    http://127.0.0.1:8443/api/system/stats/users \
    | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["active"])'
}

echo "== 7. baseline active count: $(count)"
echo
echo '== 8. create golive_smoke user =='
curl -fsS -X POST http://127.0.0.1:8443/api/users \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"username":"golive_smoke","service_ids":[1],"data_limit":1073741824,"data_limit_reset_strategy":"no_reset","expire_strategy":"never"}' > /dev/null
sleep 3
echo "active count after create: $(count) (should +1)"

echo
echo '== 9. delete golive_smoke =='
curl -sS -X DELETE http://127.0.0.1:8443/api/users/golive_smoke \
  -H "Authorization: Bearer $TOKEN" > /dev/null
sleep 3
echo "active count after delete: $(count) (back to baseline)"
EOF
```

**期望**：active count `+1` then `-1`，每步 ≤3s。

---

## ④ 订阅 URL 端到端（2 分钟）

```bash
ssh root@VPS << 'EOF'
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=ADMIN&password=PASS' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

# 用任意现有用户测
USERNAME="riku_self"
KEY=$(docker exec aegis-panel python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/marzneshin/db.sqlite3')
print(c.execute(\"select key from users where username='$USERNAME'\").fetchone()[0])
")

echo "== 10. fetch sub URL =="
curl -fsS -i "https://nilou.cc/sub/$USERNAME/$KEY" 2>&1 | head -3

echo
echo '== 11. decode + validate vless URI =='
curl -fsS "https://nilou.cc/sub/$USERNAME/$KEY" 2>&1 | base64 -d | grep -oE 'vless://[^#]+' | head -1
EOF
```

**期望**：HTTP 200 + 完整 vless URI（含 `security=reality`、`sni=...`、`pbk=...`、`sid=...`、`flow=xtls-rprx-vision`）。

---

## ⑤ Audit log 工作（1 分钟）

```bash
ssh root@VPS << 'EOF'
TOKEN=$(curl -fsS -X POST http://127.0.0.1:8443/api/admins/token \
  -d 'username=ADMIN&password=PASS' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])')

echo '== 12. AUDIT_RETENTION_DAYS not zero =='
grep AUDIT_RETENTION_DAYS /opt/aegis/.env

echo
echo '== 13. fork-owned mutating action lands audit row =='
curl -sS -X PATCH http://127.0.0.1:8443/api/users/riku_self/iplimit/override \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"max_concurrent_ips":3}' > /dev/null

docker exec aegis-panel python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/marzneshin/db.sqlite3')
print('audit_events count:', c.execute('select count(*) from aegis_audit_events').fetchone()[0])
print('latest:', c.execute('select actor_username, action, status_code, ts from aegis_audit_events order by id desc limit 1').fetchone())
"
EOF
```

**期望**：count ≥ 1 with recent timestamp + `actor_username=admin name`。

---

## ⑥ 客户端实测（5 分钟，唯一手工步骤）

iPhone 任一客户端（Streisand / V2Box / Shadowrocket）：
1. 复制订阅 URL（Step 10 给的那个，或 aegis-user 输出的）
2. 添加订阅，更新
3. 选 Tokyo Reality 节点
4. Safari 打开 `https://www.youtube.com` 或 `https://ip.sb`

**期望**：YouTube 加载，ip.sb 显示日本 IP。

---

## ⑦ 备份就位（1 分钟）

```bash
ssh root@VPS << 'EOF'
echo '== 14. backups exist =='
ls -lh /opt/aegis-backup-pre-fork/ 2>/dev/null | head -5
ls -lh /opt/aegis-backup-mtls-fix/ 2>/dev/null | head -5

echo
echo '== 15. rollback scripts present =='
ls -la /usr/local/bin/aegis-{upgrade,sync-clients,mtls-rollback} 2>&1
EOF
```

**期望**：`/opt/aegis-backup-pre-fork/` + `/opt/aegis-backup-mtls-fix/` 有内容；3 脚本都 executable。

---

## 全过 = 可邀第一个付费客户

任一项失败 → 不要邀，先修。修完重跑全套。

---

## 邀客户后第 1-7 天监控（每天 1 次）

```bash
ssh root@VPS << 'EOF'
echo '== panel + marznode healthy =='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml ps

echo '== panel error log spike check =='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  logs --since=24h panel 2>&1 | grep -iE 'error|traceback|exception' | wc -l
# (期望 < 50；超过 100 调查)

echo '== marznode error log spike =='
docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml \
  logs --since=24h marznode 2>&1 | grep -iE 'error|traceback' | wc -l

echo '== disk space =='
df -h /opt/aegis | tail -1
# (期望 > 50% 空闲)

echo '== flow stats =='
docker exec aegis-panel python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/marzneshin/db.sqlite3')
total = c.execute('select sum(used_traffic) from users where removed=0').fetchone()[0] or 0
print(f'total traffic this month: {total / 1024**3:.2f} GB')
"
EOF
```

---

## 已知风险（透明记录）

🟡 **L-035 / L-036 / L-037 family**：panel↔marznode 同步链路在 wave-1..6 经历过多次重构。当前生产 v0.3.9 + marznode v0.5.7 + grpcio backend = 已知工作。但若某天升级把任一组件 / 默认值改了，可能再次踩坑。**升级 panel 前先在 staging 试**（wave-7+ 候选 staging VPS workflow 落地后即免操心）。

🟡 **第 2 节点未测**：当前生产单节点（tokyo-1）。第 2 节点（HK 或其他）的 RPC 连通性未端到端验证，加节点时跑完本 checklist 在新节点上。

🟢 **billing infra**：`aegis_billing_plans` / `aegis_billing_channels` 表为空。**这不影响 admin-on-behalf 模式（D-016）**——`aegis-user create alice m1` 直接生成用户，邮件/微信收钱（USDT TRC20 / EPay 出账行外管理）。Web checkout 自助门户是 D-016 反向决策的事，需 ≥3 客户实际请求。

🟢 **bcrypt warning** in panel logs：每次 admin login 喷一次 trapped error reading bcrypt version。无害（passlib 兼容性 noise），不影响功能，**不要花时间修**。

---

## 改动后必读：本 checklist 自身

任何 wave-X+ 改动后（升 panel / 升 marznode / 改 backend default / 改 audit middleware）：
- 重跑 ① ~ ⑦
- 全过才能向客户开门 / 收钱
