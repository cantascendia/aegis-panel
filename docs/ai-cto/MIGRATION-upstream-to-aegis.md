# MIGRATION — upstream Marzneshin → aegis-panel

> **状态**: live runbook,首版触发于 2026-04-30 用户披露 nilou.cc 在 upstream Marzneshin (3 测试用户)。
>
> **适用**: 已经在 production 跑 upstream `marzneshin/marzneshin` 的运营者,想平迁到本 fork (aegis-panel) 享受 hardening / health / billing / audit-log / iplimit 等差异化能力。
>
> **配套脚本**: [`deploy/migrate-from-upstream.sh`](../../deploy/migrate-from-upstream.sh) — 自动化段 1-4。
>
> **不适用**: 全新部署 (走 [`deploy/install/install.sh`](../../deploy/install/install.sh) + [`OPS-deploy-runbook.md`](./OPS-deploy-runbook.md)) / 跨大版本(>2025-10-02 之后的 upstream commit,先走 §1.5 schema 冲突检测) / 跨 panel(从 Marzban / Sanaei / X-UI 迁) 不在本文档范围。
>
> **回滚承诺**: 任一段失败,5 分钟内可回 upstream(段 2 备份 + 段 3.x 的 `--rollback` 路径)。
>
> **核心结论 (兼容性已离线核对)**:
> - ✅ 自研 9 张表全部 `aegis_*` 前缀(`aegis_iplimit_*` 4 张 + `aegis_billing_*` 5 张 + `aegis_audit_events`)→ 与 upstream schema 零冲突
> - ✅ Alembic 链增量延伸:upstream tip(2024 年某迁移) → 自研 `20260422_*` / `20260423_*` / `20260424_*` / `20260430_*`,只加表/列,不动 upstream
> - ✅ Feature flags(`RATE_LIMIT_ENABLED` / `BILLING_TRC20_ENABLED` / `AUDIT_RETENTION_DAYS=0` / iplimit 默认 disabled-state)全 OFF → 启动后行为等同 upstream
> - ⚠️ `app/marzneshin.py` 第 32/70 行(`from hardening.panel import apply_panel_hardening` + `apply_panel_hardening(app)`)是 fork-only 调用,自带 NOOP 闸门,不需手动改
> - ⚠️ 通过 docker swap 达成 `<5 min downtime`(SQLite 场景);Postgres + 蓝绿可达 `<60s downtime`

---

## 0. 触发触发器(read first)

**3 个用户阶段的强烈建议**:**走段 1 + 段 2 + 段 3.1 + 段 4 + 段 6,跳过段 5(全 feature flag 留在 OFF)**。

理由:
1. 3 用户的运营复杂度,iplimit / billing / audit-log 全是负担,启用即意味着多一份配置 / 监控 / runbook。
2. fork 装上后,**被动收益已经到位**:`apply_panel_hardening()` 调用、`/api/aegis/health` 端点、Reality config audit CLI、SNI selector skill — 都不需要 flag 开。
3. 等用户 ≥ 50 / 商业化变现 / 安全审计要求时,再按 §5.1 / §5.2 / §5.3 渐进开。

---

## 段 1 — 前置检查

### 1.1 确认 upstream 版本 (硬指标)

```bash
# Docker 部署
docker exec marzneshin python -c "from app import __version__; print(__version__)" 2>/dev/null \
  || docker exec marzneshin git -C /code log -1 --format='%H %s %ci' 2>/dev/null \
  || docker exec marzneshin cat /code/VERSION 2>/dev/null

# 裸金属
cd /opt/marzneshin && git log -1 --format='%H %ci %s'
```

通过判据:
- 若版本 / commit ≤ `d3b25e2` (2025-10-02,本 fork 的分叉点) → ✅ schema 同源,直接走段 2
- 若版本 / commit > `d3b25e2` → ⚠️ 进段 1.5 做 schema 冲突检测
- 若指令全 fail → ⚠️ 直跑 `docker exec marzneshin alembic current` 拿当前迁移 head,记下 revision id

### 1.2 确认数据库类型 + 可达性

```bash
# 看 .env / docker compose 决定 DB 类型
grep -E '^(DATABASE_URL|SQLALCHEMY_DATABASE_URI)=' /opt/marzneshin/.env

# SQLite (默认)
ls -la /opt/marzneshin/data/db.sqlite3 || ls -la /opt/marzneshin/db.sqlite3
sqlite3 /opt/marzneshin/data/db.sqlite3 'select count(*) from users;'

# Postgres
PGPASSWORD=$DB_PASS psql -h localhost -U $DB_USER -d $DB_NAME -c 'select count(*) from users;'

# MySQL/MariaDB
mysql -h localhost -u $DB_USER -p$DB_PASS $DB_NAME -e 'select count(*) from users;'
```

通过判据:`select count(*)` 能返回(数字 = 现有用户数,记下来,段 4 验证用)。

### 1.3 确认节点数 + 健康

```bash
# 通过 panel API(假设你能登录)
TOKEN=$(curl -fsSL -X POST https://panel.example.com/api/admins/token \
    -d 'username=admin&password=...' | jq -r .access_token)
curl -fsSL -H "Authorization: Bearer $TOKEN" https://panel.example.com/api/nodes | jq '.[] | {id, name, status}'
```

通过判据:每个 node 的 `status` 应当是 `connected` / `healthy`。记下节点 id 列表。

### 1.4 确认现有用户 active

```bash
curl -fsSL -H "Authorization: Bearer $TOKEN" 'https://panel.example.com/api/users?limit=10' \
  | jq '[.users[] | {username, status, expire}]'
```

通过判据:三个测试用户在列;`status` 是 `active` 或 `on_hold`(不是 `expired` / `limited`)。

### 1.5 (仅 1.1 出现 commit > d3b25e2 才跑) Schema 冲突检测

```bash
# 在迁移目标主机上 clone 两个仓库做 alembic 链 diff
cd /tmp
git clone --depth 50 https://github.com/marzneshin/marzneshin upstream-mz
git clone --depth 50 https://github.com/cantascendia/aegis-panel aegis-mz

# upstream alembic head
ls upstream-mz/app/db/migrations/versions/ | sort | tail -3

# aegis alembic head
ls aegis-mz/app/db/migrations/versions/ | sort | tail -5

# 看 upstream 在 d3b25e2 之后是否新增了 aegis_* 同名表 (理论上不会但要核)
grep -E "create_table\(['\"]aegis_" upstream-mz/app/db/migrations/versions/* || echo "OK: no aegis_* table in upstream"
```

通过判据:
- ✅ upstream 没有 `aegis_*` 表 → 直接走段 2
- ❌ upstream 添加了同名 `aegis_*` 表 → **STOP**,改去 [`docs/ai-cto/UPSTREAM-SYNC-REPORT-*.md`](./UPSTREAM-SYNC-REPORT-2026-04-26.md) + 手动 rebase 自研 alembic chain

---

## 段 2 — 备份 (回滚保险)

> **铁律**: 没跑完段 2,绝不进段 3。备份是回滚的唯一凭证。

### 2.1 创建 stamped 备份目录

```bash
export STAMP=$(date +%Y%m%d-%H%M%S)
export BACKUP_DIR=/opt/aegis-migration-backup/${STAMP}
sudo mkdir -p ${BACKUP_DIR}
echo "Backup destination: ${BACKUP_DIR}"
```

### 2.2 备份 .env

```bash
sudo cp /opt/marzneshin/.env ${BACKUP_DIR}/marzneshin.env
sudo chmod 600 ${BACKUP_DIR}/marzneshin.env

# Sanity check: JWT_SECRET 必须存在且非空(丢了 = 全用户登出,订阅 link 失效)
grep -E '^(JWT_SECRET|SQLALCHEMY_DATABASE_URI|DATABASE_URL|XRAY_)' ${BACKUP_DIR}/marzneshin.env | head -5
```

通过判据:`JWT_SECRET` 行存在,值非空字符串。

### 2.3 备份数据库

**SQLite** (3 用户最常见路径):

```bash
# 优先 .backup 而非裸 cp(避免快照不一致)
SRC_DB=/opt/marzneshin/data/db.sqlite3
sudo sqlite3 "${SRC_DB}" ".backup '${BACKUP_DIR}/db.sqlite3.bak'"
ls -la ${BACKUP_DIR}/db.sqlite3.bak  # 应当 > 1 KiB
```

**Postgres**:

```bash
# 自动化脚本要求 dump 已存在 ${BACKUP_DIR}/postgres.sql.gz 才进 phase 3
# (脚本不会替你跑 pg_dump,因为 DB 容器名 / 凭据各家不同)
DB_NAME=$(grep -E '^SQLALCHEMY_DATABASE_URL=' /opt/marzneshin/.env | sed -E 's|.*/([^?]+).*|\1|')
docker exec -t mz-db pg_dump -U marzneshin "${DB_NAME}" \
  | gzip > ${BACKUP_DIR}/postgres.sql.gz
ls -la ${BACKUP_DIR}/postgres.sql.gz

# 验证 dump 可读
zcat ${BACKUP_DIR}/postgres.sql.gz | head -20

# 若 dump 已经存在(例如云厂商快照),用 --skip-backup-check 跳过本地 dump
# 检查,但**保留** auto-rollback(--no-auto-rollback 是独立的 DEBUG flag)
```

**MySQL/MariaDB**:

```bash
docker exec -t mz-db mysqldump --single-transaction --routines \
  -u marzneshin -p"${DB_PASS}" "${DB_NAME}" \
  | gzip > ${BACKUP_DIR}/mysql.sql.gz
```

通过判据:dump 文件 > 100 KiB(含 schema + 至少 3 个用户的 row 数据)。

### 2.4 备份 xray config + marznode certs

```bash
# Xray config (panel 推送给 marznode 的最近一份)
docker exec marzneshin cat /code/xray.json > ${BACKUP_DIR}/xray.json 2>/dev/null \
  || echo "xray.json not in container; skipping (panel rebuilds on start)"

# Marznode certs (multi-node 时关键,SAN 不变才能 mTLS 持续工作)
for node_dir in /var/lib/marznode/* /opt/marznode/*; do
  [ -d "$node_dir" ] || continue
  sudo cp -r "$node_dir" ${BACKUP_DIR}/marznode-$(basename $node_dir)
done

ls ${BACKUP_DIR}/
```

### 2.5 验证回滚命令(干跑)

```bash
# 这条是回滚契约 — 段 3 失败时按这套指令一字不差地跑
cat <<EOF > ${BACKUP_DIR}/ROLLBACK.sh
#!/usr/bin/env bash
set -euo pipefail
echo "[rollback] stop aegis if running"
cd /opt/aegis && docker compose down 2>/dev/null || true
echo "[rollback] restore .env"
sudo cp ${BACKUP_DIR}/marzneshin.env /opt/marzneshin/.env
echo "[rollback] restore DB"
sudo cp ${BACKUP_DIR}/db.sqlite3.bak /opt/marzneshin/data/db.sqlite3 2>/dev/null \
  || zcat ${BACKUP_DIR}/postgres.sql.gz | docker exec -i mz-db psql -U marzneshin
echo "[rollback] start upstream"
cd /opt/marzneshin && docker compose up -d
echo "[rollback] verify"
sleep 10
curl -fsSL https://panel.example.com/api/system && echo "ROLLBACK OK"
EOF
chmod +x ${BACKUP_DIR}/ROLLBACK.sh
```

通过判据:`ROLLBACK.sh` 文件存在,可执行,内容引用了备份文件路径。**不要现在跑它**,但脑里跑一遍每条指令。

---

## 段 3 — 切换 (平迁)

3 条路径,按部署形态选一条。3 用户场景默认走 **3.1 Docker image 替换**。

### 3.1 Docker image 替换 (推荐 / 3 用户场景)

```bash
# Step 1: 进入维护窗口 (5-15 分钟 downtime;3 用户感知小)
echo "$(date -Iseconds) starting migration" | sudo tee -a /opt/aegis-migration-backup/migration.log

# Step 2: 停 upstream
cd /opt/marzneshin
sudo docker compose down

# Step 3: clone aegis-panel 到旁路目录
sudo mkdir -p /opt/aegis
sudo git clone https://github.com/cantascendia/aegis-panel /opt/aegis/src
cd /opt/aegis/src
sudo git checkout main  # 或最新 tag,例如 v0.2.0

# Step 4: 复制现有 .env(JWT secret / DB URL 一字不改,保证 token / 订阅 link 全活)
sudo cp ${BACKUP_DIR}/marzneshin.env /opt/aegis/src/.env

# Step 5: SQLite 场景 — 把 DB 文件放进新 compose 挂载的 host 路径
# 本 fork docker-compose.yml 把 /var/lib/marzneshin 挂进容器,
# .env 默认 SQLALCHEMY_DATABASE_URL=sqlite:///db.sqlite3 (相对 WORKDIR,
# 解析后落在 /var/lib/marzneshin)。所以**不能**自己造一个 /opt/aegis/data
# 然后期望容器读到 — 必须放进 /var/lib/marzneshin。
sudo mkdir -p /var/lib/marzneshin
sudo cp ${BACKUP_DIR}/db.sqlite3.bak /var/lib/marzneshin/db.sqlite3
# 若 .env 里 SQLALCHEMY_DATABASE_URL 之前指 /opt/...,改成相对路径或绝对路径:
#   SQLALCHEMY_DATABASE_URL=sqlite:///db.sqlite3
# 或 SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzneshin/db.sqlite3

# Postgres 场景 — 不动 DB,只换 panel 容器,.env 里 SQLALCHEMY_DATABASE_URL 不变,
# 新 panel 启动直连同一个 Postgres。无需 step 5。

# Step 6: alembic upgrade head (会跑 4-6 个新迁移,加 9 张 aegis_* 表 + 索引,upstream 表纹丝不动)
cd /opt/aegis/src
sudo docker compose run --rm marzneshin alembic upgrade head 2>&1 | tee -a /opt/aegis-migration-backup/migration.log

# 这一步的预期日志:
#   INFO  [alembic.runtime.migration] Running upgrade <upstream_head> -> 4f7b7c8e9d10, iplimit_policy_tables
#   INFO  [alembic.runtime.migration] Running upgrade 4f7b7c8e9d10 -> a1c4b7f9e201, billing_tables
#   INFO  [alembic.runtime.migration] Running upgrade ... -> d4e5f6a7b8c9, audit_events_table
# 任一 ERROR → 进段 2.5 ROLLBACK.sh

# Step 7: 启动 aegis
sudo docker compose up -d

# Step 8: 等容器 healthy
for i in $(seq 1 30); do
  curl -fsSL http://127.0.0.1:8000/api/aegis/health 2>/dev/null && break
  sleep 2
done
```

> **注**: container 名可能是 `marzneshin` (沿用) 或 `aegis-panel`,取决于 fork 的 `docker-compose.yml`。两者都 OK,但 marznode 端 gRPC 反查的 SAN 必须匹配,见段 4.4。

### 3.2 蓝绿部署 (双 VPS / Postgres / 0 downtime 期望)

```bash
# 在新 VPS-B 上装 aegis-panel (走 deploy/install/install.sh)
ssh root@new-vps "cd /opt && git clone https://github.com/cantascendia/aegis-panel src && cd src && ./deploy/install/install.sh --db postgres --domain panel-staging.example.com"

# Postgres dump → import 到 VPS-B
docker exec mz-db pg_dump -U marzneshin marzneshin | ssh root@new-vps 'docker exec -i aegis-db psql -U aegis aegis'

# 在 VPS-B 上跑 alembic upgrade
ssh root@new-vps "cd /opt/src && docker compose run --rm marzneshin alembic upgrade head"

# 验证 VPS-B 健康(段 4 全套)

# DNS / CF Tunnel 切流量
# - 若用 CF Tunnel: 在 Cloudflare Zero Trust 改 tunnel 的 hostname 路由到 VPS-B
# - 若用 DNS: A record TTL 下调到 60s 提前,改指向 VPS-B IP

# VPS-A 待命 30 min;0 投诉就 docker compose down
```

### 3.3 原地 git pull (裸金属 / 不推荐)

仅当用户没用 docker:

```bash
cd /opt/marzneshin
sudo systemctl stop marzneshin
sudo git remote add aegis https://github.com/cantascendia/aegis-panel
sudo git fetch aegis
sudo git checkout aegis/main  # detached HEAD,不要直接 reset 上 fork 上去,留 upstream 分支

# 装新依赖(本 fork 加了 hardening / ops / aegis_*)
sudo pip install -r requirements.txt

# Alembic
sudo alembic upgrade head

sudo systemctl start marzneshin
sudo systemctl status marzneshin
```

**风险**: 系统 python 污染 / pip 依赖冲突;只对真懂 Python venv 的运维。

---

## 段 4 — 验证

> 任一 ❌ → 立即跑段 2.5 的 `ROLLBACK.sh`。

### 4.1 Health 端点

```bash
# 公开 liveness
curl -fsSL http://127.0.0.1:8000/api/aegis/health
# 期望: {"status":"ok","timestamp":"..."} 或类似

# Sudo 详情(需登录拿 token)
TOKEN=$(curl -fsSL -X POST http://127.0.0.1:8000/api/admins/token -d 'username=admin&password=...' | jq -r .access_token)
curl -fsSL -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/aegis/health/extended | jq .
# 期望:每个 subsystem 的 status 是 "ok" / "skipped"(disabled by flag);不该有 "error"
```

### 4.2 测试用户 login + 订阅 link

```bash
# 用其中一个测试用户的旧 token / 重登
curl -fsSL -X POST http://127.0.0.1:8000/api/users/token -d 'username=test1&password=...' | jq .

# 订阅 link (JWT 编码,如果 secret 没换,旧 link 应当继续工作)
USER_TOKEN=...  # 从 panel 数据库 / dashboard 取
curl -fsSL "http://127.0.0.1:8000/sub/${USER_TOKEN}" | head -20
# 期望: vmess:// / vless:// / trojan:// 字符串列表
```

通过判据:三个测试用户全部 login 成功,订阅 link 返回 ≥ 1 条 protocol URI。

### 4.3 节点 gRPC 健康 + xray clients 数 (L-032 反例核心)

```bash
# Panel 这一侧
curl -fsSL -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/nodes | jq '.[] | {id, name, status}'
# 期望: 每个 node 的 status == "connected"

# Marznode 这一侧 (xray 实际加载的 clients 数)
ssh root@node-1 "docker exec marznode-xray /usr/local/bin/xray api stats --reset --pattern user"
# 或者 panel 端反查
curl -fsSL -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8000/api/nodes/1/xray-config" | jq '.[].settings.clients | length'
```

通过判据:**xray clients 数 == 段 1.4 拿到的 active 用户数**。

> **L-032 反例**: 数为 0 = mTLS broken / panel 没把 user 推到 marznode。这种情况下 ROLLBACK,因为 fork 的 hardening hook 不该破坏 gRPC 路径(段 0 §2 说过自带 NOOP 闸门)。

### 4.4 Feature flag 全 OFF 确认

```bash
# 新 panel 容器内 grep 关键 flag
docker exec marzneshin sh -c 'env | grep -E "(RATE_LIMIT|BILLING_TRC20|BILLING_EPAY|AUDIT_RETENTION|IPLIMIT)"'

# 期望:
# - RATE_LIMIT_ENABLED=false (或 unset → default False)
# - BILLING_TRC20_ENABLED=false
# - AUDIT_RETENTION_DAYS=0 (或 unset → audit 不写表)
# - IPLIMIT 默认是 disabled-state row (在 DB 里看)

# DB 侧的 iplimit 默认状态
docker exec marzneshin python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))
with e.connect() as c:
    print(c.execute(text('select disabled_at from aegis_iplimit_disabled_state')).fetchall())
"
# 期望: 至少一行,disabled_at 不为 NULL → iplimit 关
```

### 4.5 Alembic head 一致

```bash
docker exec marzneshin alembic current
# 期望: d4e5f6a7b8c9 (head) 或更新的(随后续 PR 演进)
```

---

## 段 5 — 启用自研模块 (可选,**3 用户阶段建议跳过**)

只当满足触发条件再开。每个 flag 都有自己的 OPS runbook,本节只列触发条件 + 入口指令。

### 5.1 IP 限制 (≥ 50 用户 / 防共享)

```bash
# 加配置
echo "IPLIMIT_POLL_INTERVAL=30" | sudo tee -a /opt/aegis/src/.env
# 启用 (在 dashboard /iplimit 页面或直接改 disabled_state row)
docker exec marzneshin python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))
with e.connect() as c:
    c.execute(text('update aegis_iplimit_disabled_state set disabled_at = NULL'))
    c.commit()
"
docker compose restart marzneshin
```

完整 runbook: [OPS-iplimit-runbook.md](./OPS-iplimit-runbook.md)。

### 5.2 Billing (商业化变现)

```bash
echo "BILLING_TRC20_ENABLED=true" | sudo tee -a /opt/aegis/src/.env
echo "BILLING_TRC20_RECEIVE_ADDRESS=T..." | sudo tee -a /opt/aegis/src/.env
# EPay 类似,但要先签码商
```

完整 runbook: [OPS-trc20-runbook.md](./OPS-trc20-runbook.md) / [OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md)。

### 5.3 Audit log (合规要求 / 用户敏感操作可追溯)

```bash
# Fernet key 自动生成
KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "AUDIT_ENCRYPTION_KEY=${KEY}" | sudo tee -a /opt/aegis/src/.env
echo "AUDIT_RETENTION_DAYS=90" | sudo tee -a /opt/aegis/src/.env
docker compose restart marzneshin
```

完整 runbook: [OPS-audit-log-runbook.md](./OPS-audit-log-runbook.md)。

### 5.4 Reality config audit (≥ 3 Reality 节点)

```bash
docker exec marzneshin python -m hardening.reality.audit /code/xray.json
# 或在 dashboard /reality 跑 UI 审计
```

完整 runbook: [OPS-reality-runbook.md](./OPS-reality-runbook.md)。

### 5.5 Rate limit (≥ 100 用户 / 公开 panel 防爆破)

```bash
echo "RATE_LIMIT_ENABLED=true" | sudo tee -a /opt/aegis/src/.env
echo "REDIS_URL=redis://redis:6379/0" | sudo tee -a /opt/aegis/src/.env
docker compose --profile redis up -d
docker compose restart marzneshin
```

---

## 段 6 — AGPL §13 合规 (本 fork 商业部署铁律)

> **这是法律义务,不是建议**。AGPL-3.0 §13:**通过网络对用户提供修改版的软件,必须能让用户取得修改版的源码**。本 fork 的差异化覆盖范围决定了任何商业部署都触发这条款。

### 6.1 跑自动化 selfcheck

```bash
cd /opt/aegis/src
bash deploy/compliance/agpl-selfcheck.sh
```

通过判据:exit 0,关键检查全 ✅:
- `LICENSE` 是 AGPL-3.0
- `NOTICE.md` 引用 fork URL (https://github.com/cantascendia/aegis-panel)
- 上游版权头保留 (`app/marzneshin.py` 等不该删)

### 6.2 panel footer / dashboard 暴露 source URL

```bash
# 看 dashboard 是否含 source link
grep -rE "github\.com/cantascendia/aegis-panel|source.code|GPL" dashboard/src/ | head -5
```

若 dashboard 没自带,**手动加** footer 链接到 `https://github.com/cantascendia/aegis-panel/tree/<deployed-commit-sha>`(精确到 deployed sha,不只是 main)。否则 §13 不达标。

### 6.3 二级义务: secret 不外泄

迁移过程中 `.env` / `db.sqlite3` 备份带敏感信息:
- `${BACKUP_DIR}` 权限设 `0700` + owner=root
- 30 天后 `shred + rm` 备份文件
- 千万别把 `${BACKUP_DIR}` 整目录传到 GitHub Issue / Slack 调试

---

## 风险矩阵

| 风险 | 概率 | 影响 | mitigation |
|---|---|---|---|
| Alembic upgrade 失败 (新表创建冲突) | 低 | 中 | 段 2.3 DB dump → ROLLBACK.sh,< 5 min 恢复 |
| JWT secret 没保留 → 用户全登出 | 中 | 中 | 段 2.2 .env 备份 + 段 3.1 step 4 一字不改复用 |
| xray config 不兼容 (fork hardening 改了 inbound 默认值) | 低 | 高 | 段 2.4 备份 xray.json + 段 4.3 验证 clients 数(L-032) |
| Feature flag 错开 (例如默认开了 RATE_LIMIT 但没 redis) | 中 | 高 | 段 4.4 grep 确认全 OFF;段 5 渐进开 |
| marznode mTLS SAN 不匹配 (panel 容器名变了) | 低 | 高 | 段 2.4 备份 certs;段 4.3 验证 gRPC `connected` |
| upstream commit > d3b25e2 引入了与自研冲突的 schema | 低 | 高 | 段 1.5 schema 冲突检测 |
| 维护窗口期用户 panic 投诉 | 中 | 低 | 提前 24h 在订阅页公告;段 3.1 控制在 15 min 内 |
| ROLLBACK.sh 漏改 SQLALCHEMY_DATABASE_URI 路径 | 低 | 高 | 段 2.5 干跑 review 一遍每条命令 |
| 段 5 启用 audit-log 但 AUDIT_ENCRYPTION_KEY 弱 | 低 | 中 | 段 5.3 用 `Fernet.generate_key()`,不要自定义 |
| AGPL §13 不达标(无 source link) → 法律风险 | 低 | 中 | 段 6.2 手动加 footer 链接 |

---

## 段 7 — Acceptance criteria checklist

迁移完成签字前,逐条勾:

- [ ] **段 1**: upstream 版本 / commit 已记录;DB 类型已确认;节点列表已记录;3 个测试用户 active 状态已记录
- [ ] **段 1.5**(若 commit > d3b25e2): schema 冲突检测通过,upstream 没引入 `aegis_*` 表
- [ ] **段 2.1**: `${BACKUP_DIR}` 创建,权限 0700
- [ ] **段 2.2**: `.env` 备份,`JWT_SECRET` 行存在且非空
- [ ] **段 2.3**: DB dump 生成,大小 > 100 KiB(SQLite > 1 KiB)
- [ ] **段 2.4**: xray.json + marznode certs 备份
- [ ] **段 2.5**: `ROLLBACK.sh` 文件存在 + 可执行 + 干跑 review 过
- [ ] **段 3**(选 1): docker swap / 蓝绿 / 原地 git pull,任一路径完成
- [ ] **段 4.1**: `/api/aegis/health` 返回 ok
- [ ] **段 4.1**: `/api/aegis/health/extended` 全 subsystem ok 或 skipped(无 error)
- [ ] **段 4.2**: 3 测试用户 login 成功
- [ ] **段 4.2**: 至少 1 个用户的旧订阅 link 仍工作
- [ ] **段 4.3**: 节点 gRPC `status == connected`
- [ ] **段 4.3**: xray clients 数 == active 用户数(L-032 验证)
- [ ] **段 4.4**: feature flag 全 OFF (env grep 确认 RATE_LIMIT_ENABLED / BILLING_TRC20_ENABLED 都不是 true)
- [ ] **段 4.5**: `alembic current` 是 aegis 自研 head (`d4e5f6a7b8c9` 或更新)
- [ ] **段 5** (可选): 若启用,对应 OPS runbook 全跑过
- [ ] **段 6.1**: `bash deploy/compliance/agpl-selfcheck.sh` exit 0
- [ ] **段 6.2**: panel footer 含 source URL 链接
- [ ] **段 6.3**: 备份目录权限 0700,30 天后清理 calendar 加好

---

## 附录 A — 自研 9 张表清单 (零冲突核对依据)

| 表 | 来源 (alembic revision) | 用途 |
|---|---|---|
| `aegis_iplimit_config` | `4f7b7c8e9d10` | iplimit 全局策略 |
| `aegis_iplimit_override` | `4f7b7c8e9d10` | per-user override |
| `aegis_iplimit_disabled_state` | `4f7b7c8e9d10` | 总开关(默认 disabled_at != NULL) |
| `aegis_iplimit_allowlist_cidrs` | `b2f1c3d4e5a6` | CIDR allowlist (L-022) |
| `aegis_billing_plans` | `a1c4b7f9e201` | 套餐 |
| `aegis_billing_channels` | `a1c4b7f9e201` | 码商凭据 (runtime-editable) |
| `aegis_billing_invoices` | `a1c4b7f9e201` | 订单状态机 |
| `aegis_billing_invoice_lines` | `a1c4b7f9e201` | line items |
| `aegis_billing_payment_events` | `a1c4b7f9e201` | 不可变审计 |
| `aegis_audit_events` | `d4e5f6a7b8c9` | 操作审计(Fernet 加密 metadata) |

> 注: 表数 = 10(含 `aegis_iplimit_allowlist_cidrs`),但 mvp 划分时算 9 张是因为 `allowlist_cidrs` 是 4 张 iplimit 表的辅助。

## 附录 B — 已知 fork-only 改动 (upstream diff 面)

- `app/marzneshin.py:32,70` — `apply_panel_hardening()` import + 调用 (NOOP 闸门,内置)
- `app/db/extra_models.py` — aggregator 文件,把自研 model 注册到 SQLAlchemy metadata (L-014)
- `requirements.txt` — 加了 `cryptography`(Fernet)、`limits`(rate-limit)、`tronpy`(TRC20)等
- `dashboard/src/pages/billing/`、`dashboard/src/pages/iplimit/`、`dashboard/src/pages/reality/` — 自研页面
- `hardening/`、`ops/`、`deploy/` — 整三个目录 fork-only

## 附录 C — 参考资料

- [SPEC-deploy.md](./SPEC-deploy.md) — 全新部署的 SPEC
- [OPS-deploy-runbook.md](./OPS-deploy-runbook.md) — 全新部署的 OPS
- [LESSONS.md](./LESSONS.md) — L-014 (extra_models) / L-022 (CIDR) / L-032 (xray clients 数) / L-018 (worktree)
- [DECISIONS.md](./DECISIONS.md) — D-005 (本 runbook 模板) / D-018 / D-019
- [UPSTREAM-SYNC-REPORT-2026-04-26.md](./UPSTREAM-SYNC-REPORT-2026-04-26.md) — 上游同步先例
- [NOTICE.md](../../NOTICE.md) — AGPL §13 合规声明
- compass_artifact 五件套 (冷门 SNI / 同 ASN / 非标准端口 / CF Tunnel / Vision+短 connIdle) — 启用段 5.4 后参考

---

**最后更新**: 2026-04-30 (首版,触发于 nilou.cc 3 用户 prod 披露)
**维护**: aegis-panel CTO + Tech Lead
**反馈**: 跑完一轮迁移把踩坑写进 LESSONS.md,把 PR 提到本 runbook 升版
