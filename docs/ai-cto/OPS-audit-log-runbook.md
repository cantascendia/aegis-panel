# OPS Runbook — Audit Log (S-AL session)

> 控制面 admin mutate 行为审计 trail 的 operator 操作手册。
> 适用范围: aegis-panel v0.3+ (S-AL Phase 1-4 落地后)。
>
> **每次开新 panel 部署时按 §1 走一遍即可上线。**

---

## §1 部署 (5 段流程)

### 1.1 生成 Fernet 加密密钥

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

输出形如 `_oPoeI8xQpwL...` 一行字符串。

### 1.2 写入 `.env`

```bash
# 必填
AUDIT_SECRET_KEY="<上一步输出>"

# 可选 — 默认 90 天 retention，0 = 关闭审计
AUDIT_RETENTION_DAYS=90

# 可选 — 反向代理 trust list (D-012 模式)
# 走 Cloudflare Tunnel 用 cf 的 egress CIDR
# 走 Nginx on same host 用 127.0.0.1/32
AUDIT_TRUSTED_PROXIES="127.0.0.1/32,::1/128"

# 可选 — 扩展 redact 字段 (BASE list 永远会 redact，extras 是 union 追加)
# EU GDPR 部署
AUDIT_EXTRA_REDACT_FIELDS="email,phone,real_name,id_card"
```

### 1.3 启动 panel (boot 验证 fail-loud)

```bash
make start
```

**正常启动日志** (audit 启用):
```
INFO ops.audit.config: Audit log enabled (retention=90 days, key configured). ...
INFO ops.audit.scheduler: audit scheduler started (retention=90d, cron=03:00 UTC daily)
```

**异常 — 缺 key + retention > 0**:
```
RuntimeError: Audit log is enabled (AUDIT_RETENTION_DAYS=90) but
AUDIT_SECRET_KEY is not set. Generate a Fernet key with `python -c
'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`
and place it in .env, OR set AUDIT_RETENTION_DAYS=0 to disable
audit entirely. Refusing to boot to avoid silent event-drop.
```

**这是设计的** — panel 拒绝启动比静默丢 audit 事件好。**永远不要** 把 `AUDIT_SECRET_KEY` 设成空字符串绕过这个检查。

### 1.4 烟测

部署后用 sudo admin token 调用一个 mutate endpoint，再查列表确认有 row:

```bash
TOKEN="<sudo admin JWT>"

# 触发一个 audit 事件
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://panel.example.com/api/billing/admin/plans \
  -H "Content-Type: application/json" \
  -d '{"display_name_en": "test", "price_fen": 100}'

# 查列表
curl -H "Authorization: Bearer $TOKEN" \
  https://panel.example.com/api/audit/events?limit=10
```

应看到一行 `actor_username = <你的 username>`, `action = ...`, `result = success/failure`。

### 1.5 配置 Prometheus 监控 (可选)

`audit_retention_sweep` 任务的 deletion count 写在 INFO 日志:

```
INFO ops.audit.scheduler: audit retention sweep deleted N rows (cutoff=...)
```

把 panel log 接 Loki / Promtail 后可在 Grafana 设警报:
- "audit_retention_sweep" 关键字日 ≥ 1 次 → 任务正常
- 7 天内未见 → scheduler 挂了，告警

---

## §2 日常查询

### 2.1 找到 "谁改了 X 套餐"

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://panel.example.com/api/audit/events?target_type=billing.plan&target_id=42"
```

### 2.2 找到 "alice 这周做了什么"

```bash
SINCE=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)
curl -H "Authorization: Bearer $TOKEN" \
  "https://panel.example.com/api/audit/events?actor_username=alice&since=$SINCE"
```

### 2.3 看所有 403/401 (越权尝试)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://panel.example.com/api/audit/events?result=denied"
```

### 2.4 导出整月 CSV

```bash
SINCE=2026-04-01T00:00:00
UNTIL=2026-04-30T23:59:59
curl -H "Authorization: Bearer $TOKEN" \
  "https://panel.example.com/api/audit/events/export.csv?since=$SINCE&until=$UNTIL" \
  -o audit-2026-04.csv
```

CSV 上限 10000 行 — 超量需要走 psql + `COPY` 直查 DB。

### 2.5 看单条详情 (含解密的 before/after state)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://panel.example.com/api/audit/events/12345"
```

`before_state` / `after_state` 字段是 JSON。**敏感字段已 redact** 为 `"<REDACTED>"`，看不到原始值是设计 — base list (password / jwt / merchant_key / hashed_password / subscription_url / trc20_private_key 等) frozenset 锁定，运营方无法解除。

---

## §3 应急 wipe (D-003 法律张力 / 被胁迫场景)

### 3.1 Dashboard 不暴露 wipe 按钮

设计选择 — 单点社工攻击面 + 误操作面太大。Wipe 走 SSH + psql，门槛高 (D-018 TBD-1 SEALED)。

### 3.2 整表 TRUNCATE (< 1 秒)

```bash
ssh panel.example.com
sudo -u postgres psql aegis -c "TRUNCATE aegis_audit_events;"
```

### 3.3 物理回收存储 (paranoid)

`TRUNCATE` 标记页可重用，但磁盘上原 ciphertext 字节仍存在直到页被覆写。彻底回收:

```bash
sudo -u postgres psql aegis -c "VACUUM FULL aegis_audit_events;"
```

注意 `VACUUM FULL` 会锁表 — panel 不能写 audit row 期间。停 panel 5-10s 跑完再启。

### 3.4 关闭审计但保留历史

把 `AUDIT_RETENTION_DAYS=0` 写入 `.env`，重启 panel:
- middleware 不再写新 row
- scheduler 不再 sweep 老 row
- 已有 row 全部保留 (可读)

切回 `AUDIT_RETENTION_DAYS=90` 即重新启用，无丢失。

### 3.5 永久销毁所有 (审计自身也销毁)

```bash
# 1. 关 audit 写入
sed -i 's/AUDIT_RETENTION_DAYS=.*/AUDIT_RETENTION_DAYS=0/' .env

# 2. 重启 panel (启动日志显示 disabled)
make start

# 3. wipe 表
sudo -u postgres psql aegis -c "TRUNCATE aegis_audit_events;"
sudo -u postgres psql aegis -c "VACUUM FULL aegis_audit_events;"

# 4. 销毁加密密钥 (历史 ciphertext 即使被恢复也无解密路径)
shred -u .env
# 重新 cp .env.example .env 但 AUDIT_SECRET_KEY 留空
```

---

## §4 密钥轮换

### 4.1 单密钥替换 (不保留历史可读)

```bash
# 生成新 key
NEW=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# 替换 .env
sed -i "s|AUDIT_SECRET_KEY=.*|AUDIT_SECRET_KEY=\"$NEW\"|" .env

# 重启 panel
make start
```

**代价**: 旧 row 无法解密，list endpoint 仍能列 metadata，detail endpoint 跑 decrypt 时 raise `AuditMisconfigured` → 500。运营方应该:
- 先 export 老数据 CSV (只 metadata，不含 state diff)
- 重启后旧 row 详情不可读 (新 row 正常)

### 4.2 多密钥 (MultiFernet) 轮换 — 保留历史可读

`ops/audit/crypto.py` 默认用 `Fernet`，单密钥。需要持续解密历史时升级到 `MultiFernet([new_key, old_key])` — 加密用 new，解密两个都试。这是非破坏性升级路径，**未来需要时**再改:

1. 改 `_fernet()` 函数返回 `MultiFernet([Fernet(new), Fernet(old)])`
2. 加 env: `AUDIT_SECRET_KEYS_OLD="key1,key2,..."` 多个老 key
3. 加密永远用第一个 key (new)，解密尝试整个 list

---

## §5 troubleshooting

### 5.1 Audit row 没出现

按顺序排查:

| 检查 | 命令 |
|---|---|
| Panel 在跑? | `systemctl status marzneshin` |
| Audit enabled? | `grep AUDIT_RETENTION_DAYS .env` 应该 > 0 |
| Boot 日志有 `Audit log enabled`? | `journalctl -u marzneshin \| grep audit` |
| 路径在 audit scope? | 检查 `ops/audit/middleware.py` `_AUDIT_PATH_PATTERNS` |
| Method 是 mutate? | GET/HEAD/OPTIONS 不审计 |
| Audit DB 写失败? | `journalctl -u marzneshin \| grep "audit row write failed"` |

### 5.2 IP 字段全是 127.0.0.1

Panel 在 reverse proxy (Nginx / CF) 后但没设 `AUDIT_TRUSTED_PROXIES`。修:

```bash
echo 'AUDIT_TRUSTED_PROXIES="127.0.0.1/32,::1/128"' >> .env  # Nginx 同机
# 或 CF Tunnel egress IPs
make start
```

### 5.3 Detail 5xx — `AuditMisconfigured: wrong key`

`AUDIT_SECRET_KEY` 被改过。要么:
- 找回历史值 (从 backup .env)
- 或承认丢失，新 key 之前的 row 详情不可读 (metadata 仍可见)

### 5.4 Sweep 没跑

```bash
journalctl -u marzneshin --since "yesterday 02:00" | grep "audit retention sweep"
```

应每天 03:00 UTC 出现一行。没有的话:
- Panel 在 02-04 UTC 重启过? → 下一天再看
- APScheduler 卡住? → `systemctl restart marzneshin`

---

## §6 参考

- SPEC: [`docs/ai-cto/SPEC-audit-log.md`](./SPEC-audit-log.md)
- SEALED 决策: D-018 (issue #103)
- 实现 PR 链: #125 schema → #126 redact → #127 crypto → #128 config → #131 sweep → #132 middleware MVP → #133 actor decode → #134 read API
- 模式参考: [`docs/ai-cto/OPS-iplimit-runbook.md`](./OPS-iplimit-runbook.md) / [`docs/ai-cto/OPS-trc20-runbook.md`](./OPS-trc20-runbook.md)
