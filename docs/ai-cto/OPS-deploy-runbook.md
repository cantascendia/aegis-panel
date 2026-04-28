# OPS — 部署运维手册(S-D session,D.5 fleshed)

> **状态**:fleshed-out(D.5)。配套 [SPEC-deploy.md](./SPEC-deploy.md) 的 AC-D.5.1/2,
> 每个应急场景按 **检测命令 / 判定条件 / 处置步骤 / 验证命令** 四段式书写。
>
> 关联文档:[SESSIONS.md §S-D](./SESSIONS.md)、[OPS-iplimit-runbook.md](./OPS-iplimit-runbook.md)、
> [OPS-trc20-runbook.md](./OPS-trc20-runbook.md)、[OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md)、
> compass_artifact 五件套(冷门 SNI / 同 ASN / 非标准端口 / CF Tunnel / Vision+短 connIdle)。
>
> 读者:拥有 panel 的运营者(机场主)或被授权的运维。
> 不是:开发教程、架构文档、SPEC(那些去 `SPEC-deploy.md`)。

---

## 0. Prerequisites checklist

跑任何后续章节前必须先满足:

| 前置 | 验证命令 | 通过判据 |
|---|---|---|
| 拥有 root 或 `sudo` 的 Linux VPS | `id -u` | 0 或 `sudo -n true` 无提示 |
| OS 是 tier-1 发行版 | `cat /etc/os-release \| grep -E '^(ID\|VERSION_ID)='` | `ID=ubuntu` (`22.04`/`24.04`) 或 `ID=debian` (`12`) |
| RAM ≥ 2 GiB | `awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo` | ≥ 2048 |
| `/var/lib` ≥ 20 GiB free | `df -BG /var/lib \| awk 'NR==2 {print $4}'` | ≥ 20G |
| docker 已装且 ≥ 24 | `docker --version` | `Docker version 24.x.x` 或更高 |
| `docker compose` v2 插件 | `docker compose version` | `Docker Compose version v2.x.x` |
| `curl openssl jq` | `for c in curl openssl jq; do command -v $c; done` | 三个路径都打印 |
| 域名 DNS 已指向 VPS(若不上 CF Tunnel) | `dig +short $PANEL_DOMAIN` | 返回 VPS IP |
| 拿到了 CF API Token(若上 CF Tunnel) | `curl -fsSL -H "Authorization: Bearer $CF_API_TOKEN" https://api.cloudflare.com/client/v4/user/tokens/verify` | `"status":"active"` |
| 已读 [SPEC-deploy.md](./SPEC-deploy.md) §"用户画像" | — | 你符合操作门槛 |

任一未满足:回 [`deploy/README.md`](../../deploy/README.md) 补环境后再继续。

---

## 1. First install — 单节点 S1 / S2 走查

适用于 SPEC §"场景矩阵" 的 **S1(SQLite + 同机 marznode)**、**S2(Postgres + 同机 marznode + CF Tunnel)**。

### 1.1 拉仓库 + 跑 install.sh

```bash
sudo mkdir -p /opt/aegis/src
sudo git clone https://github.com/cantascendia/aegis-panel /opt/aegis/src
cd /opt/aegis/src
```

S1(轻量):

```bash
sudo ./deploy/install/install.sh \
  --db sqlite \
  --domain panel.example.com \
  --cf-tunnel no
```

S2(推荐生产):

```bash
sudo ./deploy/install/install.sh \
  --db postgres \
  --marznode same-host \
  --domain panel.example.com \
  --cf-tunnel yes
```

中途 Ctrl-C / 进程被 kill 是安全的;`/opt/aegis/.install-step-{1..9}.done` sentinel
保证重跑只补未完成步骤(对齐 [SPEC §"幂等实现"](./SPEC-deploy.md))。完整重置请见 §10.4。

### 1.2 验证 panel 可登录

```bash
# 凭据写入 /opt/aegis/INSTALL-SUMMARY.txt(mode 600)
sudo cat /opt/aegis/INSTALL-SUMMARY.txt | head -20

# 健康端点
curl -fsSL http://127.0.0.1:8443/api/system/info | jq '.version'

# CF Tunnel 模式额外验证
curl -fsSI https://panel.example.com   # 期待 200
```

### 1.3 跑 AGPL 自检(**必跑**,差异化 #4)

```bash
bash deploy/compliance/agpl-selfcheck.sh \
  --url https://panel.example.com
```

期待 `exit 0` 全 PASS。任何 FAIL 直接卡 deployment,见 §8。

### 1.4 关 22 端口 password auth(运营硬约束)

`install.sh` 不动 sshd_config,自己动手:

```bash
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload sshd
```

---

## 2. Multi-node install — Ansible flow(S3 商业运营)

> **依赖 D.3 PR**:`deploy/ansible/`(common + marzneshin + marznode 3 roles +
> inventory template)。本节流程在 D.3 PR 合并前为 **forward-looking**;
> 路径以 D.3 实现为准,如有差异以 [SPEC-deploy.md](./SPEC-deploy.md) §"Ansible 职责" 为锚。

### 2.1 前置

- 控制面 VPS:已按 §1 装好 panel(S2 流程)
- 节点 VPS:N 台干净 Ubuntu 24.04 / Debian 12,SSH key 已下发
- 操作机:本地 macOS / Linux,已装 `ansible-core ≥ 2.16`、`ansible-vault`

### 2.2 渲 inventory + Vault

```bash
cd /opt/aegis/src/deploy/ansible
cp inventory.example.yml inventory.yml

# 编辑填实际 IP / hostname / marznode_id;格式见 SPEC §"Inventory 示例"
$EDITOR inventory.yml

# 生成 marznode gRPC CA + 客户端证书(保留 cert_mode=vault 模式)
ansible-vault create group_vars/all/vault.yml
# 写入: marznode_ca_cert / marznode_ca_key / panel_jwt_secret
```

### 2.3 跑 site.yml

```bash
ansible-playbook -i inventory.yml site.yml --ask-vault-pass
```

预期 ≤ 30 min(对齐 AC-D.3.1)。check-mode 验证幂等性:

```bash
ansible-playbook -i inventory.yml site.yml --ask-vault-pass --check
# 期待:0 changed
```

### 2.4 验证所有节点 online

```bash
# 控制面 dashboard 应显示 N 个节点 status=online
curl -fsSL http://127.0.0.1:8443/api/nodes -H "Authorization: Bearer $TOKEN" \
  | jq '[.[] | {id, name, status}]'
```

期望全部 `"status":"connected"`。任一离线:见 §7.2。

---

## 3. Adding nodes — 给运行中部署增节点

### 3.1 Ansible 模式(推荐)

```bash
cd /opt/aegis/src/deploy/ansible
$EDITOR inventory.yml      # 在 data_plane: 下追加新主机

ansible-playbook -i inventory.yml site.yml --ask-vault-pass --limit data_plane
```

`--limit data_plane` 关键:**不触控制面**(对齐 AC-D.3.2)。

### 3.2 单节点手工模式(无 Ansible)

> **依赖 D.2 PR**:`deploy/marznode/install-node.sh`。D.2 合并前请走 §3.1。

```bash
# 控制面侧:在 dashboard "Nodes" 页 + 一个新节点条目,记下 node_id 和 cert
# 节点 VPS 侧:
sudo ./deploy/marznode/install-node.sh \
  --control-plane=panel.example.com \
  --node-id=3
```

预期 30s 内控制面 dashboard 显示新节点 online(对齐 AC-D.2.1)。

### 3.3 容量边界提醒

参阅 §9 capacity planning。每加一节点先确认:gRPC 端口 `MARZNODE_GRPC_PORT`
在节点 ufw 中只对**控制面 IP** 开放(source 限制),不要 `0.0.0.0/0`。

---

## 4. Upgrades — 升级与回滚

### 4.1 Minor / patch 升级

```bash
cd /opt/aegis/src

# 升级前必跑:数据备份(见 §5)
sudo ./deploy/install/install.sh --upgrade --backup-only

# 拉新 tag
git fetch --tags
git checkout v0.2.1                  # 替换为目标 tag

# install.sh --upgrade:跑 alembic upgrade + compose pull + compose up -d
sudo ./deploy/install/install.sh --upgrade
```

`install.sh --upgrade` 内部顺序(对齐 SPEC §"回滚 / 升级路径"):
1. `alembic current` 记录当前 rev → 写 `/opt/aegis/.upgrade-from-rev`
2. `pg_dump` → `/opt/aegis/backups/pre-upgrade-$(date +%s).sql.gz`
3. `docker compose pull`(只拉 image,不动容器)
4. `alembic upgrade head`(失败立即 abort,不动 compose)
5. `docker compose up -d`(rolling)
6. healthcheck 120s

### 4.2 Major 升级

major 升级 = 跨 `vX.0` 边界 = 可能含破坏性 alembic migration 或 `.env` schema
变更。在 §4.1 之上额外:

- 在 staging VPS 先跑一遍完整流程
- 公告维护窗口(用户通告模板见 §11)
- 升级前 24h 暂停 billing 任务以免支付与维护重叠

### 4.3 回滚(紧急)

⚠️ **L-015 Alembic 不变性约束**:已 merge 的 alembic revision 不能改 `down_revision`。
若 downgrade 语义不干净,**只能滚前不滚后**。

```bash
# Step 1: 先确认目标 prev-rev 是否安全 downgrade
cd /opt/aegis/src
PREV_REV=$(cat /opt/aegis/.upgrade-from-rev)
echo "${PREV_REV}"

# Step 2: 试 downgrade(空跑校验)
docker compose -f deploy/compose/docker-compose.prod.yml exec panel \
  alembic downgrade --sql ${PREV_REV} | head -50
# 阅读输出:DROP COLUMN / DROP TABLE 是否会丢数据?

# Step 3a: 安全则正式 downgrade + 切代码
docker compose -f deploy/compose/docker-compose.prod.yml exec panel \
  alembic downgrade ${PREV_REV}
git checkout v0.1.x                 # 旧 tag
docker compose -f deploy/compose/docker-compose.prod.yml up -d

# Step 3b: 不安全(downgrade 会丢数据)→ 走备份还原(§6)
```

**验证**:`curl http://127.0.0.1:8443/api/system/info | jq .version` 显示旧 tag。

### 4.4 镜像 tag 回滚(配置不变,仅换 image)

某些场景仅 image 出问题,DB schema 没动:

```bash
export AEGIS_VERSION=v0.2.0          # 旧 tag
sudo sed -i "s/^AEGIS_VERSION=.*/AEGIS_VERSION=${AEGIS_VERSION}/" /opt/aegis/.env
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml pull
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml up -d
```

---

## 5. Backups — 备份策略

### 5.1 PostgreSQL 备份(daily,核心)

最小可用脚本(放 `/opt/aegis/scripts/backup-pg.sh`,owner root,mode 700,
**本 PR 不入仓库** — 见 §13 "已知遗留",待后续 OPS 迭代落到
`deploy/install/lib/backup-pg.sh` 并入 `install.sh --backup-only` 旗):

```bash
#!/usr/bin/env bash
set -euo pipefail
ts=$(date -u +%Y%m%dT%H%M%SZ)
out="/opt/aegis/backups/pg-${ts}.sql.gz"
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml \
  exec -T postgres pg_dump -U aegis -d aegis | gzip -9 > "${out}"
chmod 600 "${out}"
# 异地:rclone 到 R2(配置见 ~/.config/rclone/rclone.conf)
rclone copy "${out}" r2:aegis-backups/pg/ --quiet
# 本地保留 14 份
ls -1t /opt/aegis/backups/pg-*.sql.gz | tail -n +15 | xargs -r rm -f
```

cron 项(`/etc/cron.d/aegis-pg-backup`,mode 644):

```cron
# 每日 03:30 UTC
30 3 * * * root /opt/aegis/scripts/backup-pg.sh
```

### 5.2 Xray config 快照(weekly)

```bash
# 周一 04:00 UTC
0 4 * * 1 root tar -czf /opt/aegis/backups/xray-$(date -u +%Y%m%d).tar.gz \
  /opt/aegis/data/marznode/xray/config.json
```

### 5.3 `.env` + cert 离线备份(每次改完手动)

```bash
sudo tar -czf "/opt/aegis/backups/secrets-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" \
  /opt/aegis/.env /opt/aegis/certs/
sudo chmod 600 /opt/aegis/backups/secrets-*.tar.gz
# 用 gpg 加密后异地存放,离线介质优先
gpg -c --cipher-algo AES256 /opt/aegis/backups/secrets-*.tar.gz
shred -u /opt/aegis/backups/secrets-*.tar.gz   # 留下 .gpg
```

### 5.4 频率建议

| 数据 | 频率 | 保留 | 异地副本 |
|---|---|---|---|
| PostgreSQL `pg_dump` | daily 03:30 UTC | 本地 14 份 | S3/R2,30 天 |
| Xray config snapshot | weekly Mon 04:00 | 本地 8 份 | 同 PG |
| `.env` + certs(gpg 加密) | 每次变更 | 永久(版本化) | 离线介质 + 异地 |
| 升级前 pg_dump | 每次升级前(自动) | 10 份 | 自动同步 |

---

## 6. Restore — 还原与凭据恢复

### 6.1 从 `pg_dump` 还原

```bash
# Step 1: 停 panel(保留 pg)
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml stop panel marznode

# Step 2: drop + recreate DB
docker compose ... exec postgres psql -U aegis -d postgres -c \
  "DROP DATABASE aegis; CREATE DATABASE aegis OWNER aegis;"

# Step 3: 灌备份
gunzip -c /opt/aegis/backups/pg-20260428T033000Z.sql.gz | \
  docker compose ... exec -T postgres psql -U aegis -d aegis

# Step 4: 拉 panel(它会跑 alembic upgrade head 校验 schema 完整)
docker compose ... up -d
```

**验证**:`curl /api/system/info` 200 + dashboard 登录 + 抽查一个 user 流量数据存在。

### 6.2 admin 密码重置

> 适用:管理员忘密码 / 离职管理员 token 需作废 / 首次密码遗失。

```bash
# 进入 panel 容器(同一镜像即可,不依赖运行态)
docker compose ... exec panel \
  marzneshin admin update --username admin \
    --new-password "$(openssl rand -base64 18)"
```

输出新密码,记到 `INSTALL-SUMMARY.txt` 备份处。

### 6.3 JWT secret 丢失(从 `.env` 备份恢复)

`JWT_SECRET_KEY` 丢了不等于灾难,但所有现有 token 立即失效。

```bash
# 路径 A: 有 .env 备份
gpg -d /opt/aegis/backups/secrets-LATEST.tar.gz.gpg | tar -xzC /tmp/restored
sudo cp /tmp/restored/opt/aegis/.env /opt/aegis/.env
sudo shred -u -r /tmp/restored
docker compose ... restart panel

# 路径 B: 无备份 → 重生成 + 强制所有 admin 重登
NEW_JWT=$(openssl rand -base64 64)
sudo sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${NEW_JWT}|" /opt/aegis/.env
docker compose ... restart panel
# 通告:所有 admin/user 需重新登录 / 重新拉订阅
```

注意:用户订阅 URL 不依赖 JWT,**用户侧无感**;只 admin token 失效。

---

## 7. Common incidents — 应急场景十连

> 以严重度排序。每个场景四段式:**检测 / 判定 / 处置 / 验证**。

### 7.1 Panel 起不来(decision tree)

**检测命令**:
```bash
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml ps
docker compose ... logs --tail 200 panel | tail -50
curl -fsSL http://127.0.0.1:8443/api/system/info
```

**判定条件**:`docker compose ps` 中 panel `Exit 1`/`Restarting`,或 curl 返回非 200。

**处置步骤**:
1. **看日志关键词分诊**:
   - `alembic.exc.*` → schema 出错 → 跑 §6.1 还原最近备份
   - `psycopg.*OperationalError` → DB 连不上 → §7.5 + 检查 `POSTGRES_PASSWORD` 在 `.env` 与 compose 一致
   - `Address already in use` → §7.x 端口冲突 → `ss -ltnp | grep 8443`,kill 占用进程
   - `Permission denied: '/opt/aegis/data/...'` → ownership 错 → `sudo chown -R aegis:aegis /opt/aegis/data`
   - 没有上述特征 → 走 step 2
2. `docker compose ... restart panel` 一次,再看 logs。
3. 仍不通:`docker compose ... down && docker compose ... up -d`,等 120s。
4. 仍不通:进 §6.1 还原模式。

**验证命令**:
```bash
curl -fsSL http://127.0.0.1:8443/api/system/info | jq .version
```

### 7.2 Marznode 节点 disconnected

**检测命令**:
```bash
# 控制面侧
curl -fsSL http://127.0.0.1:8443/api/nodes \
  -H "Authorization: Bearer $TOKEN" | jq '[.[] | select(.status != "connected")]'

# 节点侧
sudo journalctl -u aegis-marznode.service -n 100 --no-pager
sudo grpc_health_probe -addr=:62051
```

**判定条件**:节点 status ≠ `connected` 持续 > 60s。

**处置步骤**(四种根因排查):
1. **gRPC cert 过期/不匹配**:`openssl x509 -in /opt/aegis/certs/marznode.crt -noout -dates`,
   过期 → §10.3 cert rotation。
2. **网络层不通**:控制面 `nc -vz <node-ip> 62051`。不通:节点 ufw `sudo ufw status`,确认 62051
   对控制面 IP open;云防火墙 / security group 同样放行。
3. **节点容器未跑**:`ssh node "docker compose ps"`,挂掉 → `docker compose up -d`。
4. **控制面 DB 锁死**:见 §7.5;锁死时控制面 gRPC handler 阻塞,所有节点同时掉。

**验证命令**:
```bash
curl ... /api/nodes | jq '.[] | {name, status}'
# 全部 status="connected"
```

### 7.3 易支付 webhook 不到达

**检测命令**:
```bash
# 1. webhook URL 公网可达?
curl -fsSI ${BILLING_PUBLIC_BASE_URL}/billing/epay/webhook
# 2. 最近 24h 是否有任何 webhook 入账?
docker compose ... exec panel \
  marzneshin billing webhook-log --hours 24
# 3. 码商后台 webhook 重试日志(供应商面板,见 OPS-epay-vendor-guide.md §故障台账)
```

**判定条件**:用户支付后 5 min 内 panel 无 `payment.received` 事件,且码商后台显示 webhook 多次 4xx/5xx。

**处置步骤**:
1. **`BILLING_PUBLIC_BASE_URL` 不可达**:CF Tunnel down(§7.10) / DNS 错 / nginx 拦截 webhook
   路径 → 修通后码商会重试。
2. **码商 IP 不在 allowlist**:看 nginx access.log 看到 4xx 的源 IP → 加进 `nginx.conf` 的
   `geo $epay_allowed { ... }` block → `nginx -s reload`。完整列表见
   [OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md)。
3. **签名验证失败**(panel 日志 `webhook signature mismatch`):
   `EPAY_SECRET_KEY` 在 `.env` 与码商后台不一致 → 同步后 restart panel。
4. **数据库写入冲突**:`docker compose ... logs panel | grep -i deadlock` → §7.5。

**验证命令**:
```bash
# 用码商后台的 "重发 webhook" 功能,然后:
docker compose ... exec panel \
  marzneshin billing webhook-log --hours 1 | tail -5
# 期待最新一条 status=accepted
```

### 7.4 TRC20 polling 卡住

**检测命令**:
```bash
docker compose ... logs panel --tail 200 | grep -i tronscan
docker compose ... exec panel \
  marzneshin billing trc20-status      # 自定义命令,见 OPS-trc20-runbook.md §6
```

**判定条件**:Tronscan 最近 30s 内无 success request,或 receive 地址 24h 无新交易但用户报已转账。

**处置步骤**:
1. **Tronscan 限流**(`429 Too Many Requests`):
   ```bash
   # 临时拉长 poll 间隔
   sudo sed -i 's|^TRC20_POLL_INTERVAL=.*|TRC20_POLL_INTERVAL=60|' /opt/aegis/.env
   docker compose ... restart panel
   ```
   长期:申请 Tronscan API key 提配额(见 [OPS-trc20-runbook.md §限流](./OPS-trc20-runbook.md))。
2. **接收地址错** / 不一致:
   ```bash
   # 对比 .env 与 dashboard "PaymentChannel" 配置
   grep TRC20_RECEIVE_ADDRESS /opt/aegis/.env
   curl ... /api/billing/payment-channels | jq '.[] | select(.kind=="trc20")'
   ```
   不一致 → 以 `.env` 为准,改 dashboard。
3. **Tron 节点端故障**:换备用 endpoint:`TRC20_API_BASE=https://api.trongrid.io`(免费 tier)。

**验证命令**:
```bash
docker compose ... logs panel --tail 50 | grep "trc20.*polled"
# 最新一条 < 60s 前
```

### 7.5 高 DB CPU(> 80% sustained)

**检测命令**:
```bash
docker compose ... exec postgres psql -U aegis -d aegis -c \
  "SELECT pid, now()-query_start AS dur, state, query
     FROM pg_stat_activity
    WHERE state != 'idle'
    ORDER BY dur DESC
    LIMIT 10;"
docker stats --no-stream aegis-postgres
```

**判定条件**:postgres 容器 CPU > 80% 持续 > 5 min,或 `pg_stat_activity` 出现单查询 `dur > 30s`。

**处置步骤**:
1. **找 long-running query**(上面 SQL 输出 → 抓 pid):
   ```sql
   SELECT pg_cancel_backend(<pid>);    -- 优雅取消
   -- 不掉就升级
   SELECT pg_terminate_backend(<pid>);
   ```
2. **用户大表 N+1**(对齐 SPEC §">200 用户铺垫"):
   - 抓最频 query:`SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10`
   - 缺索引时跑 `EXPLAIN ANALYZE` 确认 → 加索引(走正常 alembic migration,**不在线 DDL**)
3. **vacuum 滞后**(`n_dead_tup` 大):`VACUUM (ANALYZE, VERBOSE) <table>` 手动一次,
   后续打开 autovacuum tuning。
4. **彻底失控**:`docker compose ... restart postgres`(影响:期间 panel 502 ~30s)。

**验证命令**:
```bash
docker stats --no-stream aegis-postgres
# CPU < 30% sustained
```

### 7.6 磁盘满

**检测命令**:
```bash
df -h /
df -h /opt/aegis/data
du -sh /opt/aegis/data/* | sort -h
docker system df
```

**判定条件**:任一 fs `Use% > 90%`。

**处置步骤**(按风险从低到高):
1. **docker logs 占空间**:
   ```bash
   docker system prune -f --volumes=false      # 不动 volume!
   ```
2. **旧 PG 备份**:
   ```bash
   ls -1t /opt/aegis/backups/pg-*.sql.gz | tail -n +15 | xargs -r sudo rm -f
   ```
3. **xray access.log 老 partition**(若已轮转):
   ```bash
   sudo find /opt/aegis/data/marznode/xray/logs -name 'access.log.*.gz' -mtime +14 -delete
   ```
4. **expand volume**(provider 特定 — 通常 cloud control panel 在线扩容 + `resize2fs`)。
5. ⚠️ **绝不**直接 `rm /opt/aegis/data/pg/*` —— DB 立即损坏。

**验证命令**:`df -h /opt/aegis/data` 显示 `Use% < 70%`。

### 7.7 SSL 证书过期

**检测命令**:
```bash
echo | openssl s_client -servername panel.example.com -connect panel.example.com:443 2>/dev/null \
  | openssl x509 -noout -dates
```

**判定条件**:`notAfter` 距今 < 7 天,或 panel 访问浏览器报 `NET::ERR_CERT_DATE_INVALID`。

**处置步骤**:
- **CF Tunnel 模式**:CF 自动管证书,过期是 CF 侧 incident 而不是你 → 看 CF status page,
  可临时切 §7.10 备用入口。
- **certbot 模式**:
  ```bash
  sudo certbot renew --quiet
  sudo systemctl reload nginx
  ```
  自动 renew 的 cron(`/etc/cron.d/certbot`)若被禁就再开。
- **手动证书**(自带 cert):用新签发证书替换 `/etc/letsencrypt/live/panel.example.com/`,
  reload nginx。

**验证命令**:重跑检测命令,`notAfter` 远在未来。

### 7.8 用户大批量被禁(emergency stop)

**场景**:错配 IP limiter(参 [OPS-iplimit-runbook.md](./OPS-iplimit-runbook.md))/
误操作 / 检测到 abuse pattern 但需先暂停。

**检测命令**:
```bash
docker compose ... exec panel marzneshin user list --status disabled | wc -l
```

**判定条件**:disabled 数量 > 业务历史 baseline 5×。

**处置步骤**:
1. **第一时间冻结**:
   ```bash
   sudo sed -i 's|^IPLIMIT_VIOLATION_ACTION=.*|IPLIMIT_VIOLATION_ACTION=warn|' /opt/aegis/.env
   docker compose ... restart panel
   ```
   把 `disable` 退回 `warn`,新增违规不再封号。
2. **批量解封**(确认是误判):
   ```bash
   docker compose ... exec panel \
     marzneshin user bulk-enable --since "2026-04-28 00:00 UTC" --dry-run
   # 看清单,确认无误后去掉 --dry-run
   ```
3. 通告用户 + 在 §11 渠道发声。
4. 复盘:看 [OPS-iplimit-runbook.md](./OPS-iplimit-runbook.md) 是否时区错配
   等已知坑。

**验证命令**:
```bash
docker compose ... exec panel marzneshin user list --status active | wc -l
# 接近正常水位
```

### 7.9 JWT secret 泄露

**场景**:`.env` 误 push 到 git / 备份介质丢失 / 协作者离职。

**检测命令**:
```bash
git log --all -p | grep -E 'JWT_SECRET_KEY=[A-Za-z0-9+/=]{32,}'
```

**判定条件**:命中 secret 字面值,或第三方扫描器报告。

**处置步骤**(SLA ≤ 30 min):
1. **生成新 secret**:
   ```bash
   NEW=$(openssl rand -base64 64)
   sudo sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${NEW}|" /opt/aegis/.env
   ```
2. **restart panel**:`docker compose ... restart panel` —— **所有现有 admin token 立即失效**。
3. **强制所有管理员重登**:dashboard 自然要求再次输入 admin 密码。
4. **审计日志看异常**:
   ```bash
   docker compose ... exec panel \
     marzneshin audit grep --since "1 hour ago" --pattern 'admin\.'
   ```
   出现陌生 IP 的 admin action → 走 §7.8 + 改密码。
5. **git 历史清理**(已 push):
   - 私库:`git filter-repo --path .env --invert-paths` + force push,通知协作者重 clone。
   - 公开库:**视作 secret 已泄露,只能轮换,不要回头删** —— 已经被抓走。
6. **AGPL §13 自检**:跑 §8,确认 `.env` 不在 commit 列表(`agpl-selfcheck.sh` 含此项)。

**验证命令**:
```bash
# 旧 token 应该 401
curl -fsSL http://127.0.0.1:8443/api/admins/me \
  -H "Authorization: Bearer ${OLD_TOKEN}"   # 期待 401
```

### 7.10 CF Tunnel down(CF 侧故障 / 配置出错)

**检测命令**:
```bash
curl -fsSI https://panel.example.com           # 期待 200,实际 5xx 或 timeout
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -n 100 --no-pager
# CF 全网状态:https://www.cloudflarestatus.com
```

**判定条件**:`curl` 失败 + cloudflared 服务 active 但日志报 `connection refused`/`tunnel error`,
或 CF status page 确认 region incident。

**处置步骤**:
1. **首选:切备用入口**(临时直暴露原机,IP allowlist):
   ```bash
   sudo ufw allow from <admin-vpn-ip> to any port 443 proto tcp comment 'temp panel direct'
   sudo ufw allow from <admin-vpn-ip> to any port 8443 proto tcp comment 'temp panel direct'
   sudo systemctl stop cloudflared           # 释放绑定
   sudo nginx -s reload                      # 走 nginx 81/443 直走
   # 通告 admin 走 IP + 端口直访,跳过 panel.example.com
   ```
2. **次选:整体 uninstall + 临时 SSH tunnel**:
   ```bash
   # 节点机
   sudo bash deploy/cloudflare/uninstall-tunnel.sh --domain panel.example.com
   # 操作机
   ssh -L 8443:127.0.0.1:8443 root@<vps-ip>
   # 浏览器开 http://localhost:8443
   ```
3. **CF 恢复后回切**:
   ```bash
   sudo bash deploy/cloudflare/install-tunnel.sh --domain panel.example.com
   sudo bash deploy/cloudflare/setup-access.sh --domain panel.example.com \
     --emails admin@example.com
   sudo ufw delete allow from <admin-vpn-ip> to any port 443 proto tcp
   ```

**验证命令**:
```bash
curl -fsSI https://panel.example.com    # 200
dig +short panel.example.com            # 仅 CF Anycast IP,无源站 IP
```

---

## 8. AGPL §13 compliance verification

差异化 #4(SPEC §"合规一键自检")。AGPL-3.0 §13 要求:**通过网络对用户提供服务时
必须能让用户获取源码**。Aegis Panel 把这一项做成可一键验证。

### 8.1 何时跑

| 场景 | 频率 |
|---|---|
| 首装后(§1.3) | 必跑 |
| 每次升级后 | 必跑 |
| 月度运维例行 | 推荐 |
| 任何依赖 license 警告 | 必跑 |

### 8.2 怎么跑

```bash
bash /opt/aegis/src/deploy/compliance/agpl-selfcheck.sh \
  --url https://panel.example.com
```

退出码语义(对齐 [`agpl-selfcheck.sh`](../../deploy/compliance/agpl-selfcheck.sh) header):

| Exit | 含义 | 处置 |
|---|---|---|
| 0 | 全 PASS | 归档 report 即可 |
| 1 | 源码披露入口缺失 | 检查 dashboard footer + `/api/system/info` 的 `source_code_url` 字段 |
| 2 | NOTICE.md 缺失 / 上游版权头被删 | `git diff origin/main -- NOTICE.md`,恢复缺失部分 |
| 3 | `app/**` 源码版权头被删 | 看 git blame,恢复或重写 |
| 4 | panel 不可达 | 先解决 §7.1 / §7.10 |

### 8.3 月度归档

```bash
mkdir -p /opt/aegis/compliance-archive
out=$(bash /opt/aegis/src/deploy/compliance/agpl-selfcheck.sh \
  --url https://panel.example.com 2>&1)
echo "${out}" > "/opt/aegis/compliance-archive/$(date -u +%Y%m).log"
```

异地归档:同步到 `r2:aegis-compliance/` 留 5 年备查(对齐 AGPL 长尾)。

---

## 9. Capacity planning — 何时扩容

| 用户规模 | 节点 | DB | 必做 | 建议 |
|---|---|---|---|---|
| ≤ 50 | 1(同机) | SQLite | — | 升 PG 早一步 |
| 51 – 200 | 1(同机) | PostgreSQL | 关 SQLite 切 PG;PG 备份 cron;CF Tunnel | 监控 panel CPU,>50% 持续 1h 加节点 |
| 201 – 500 | 2 节点 | PostgreSQL | 控制面 + 数据面分机;Redis 启用;ip limiter 启用 | PG 资源 cap 改 1 CPU / 1 GiB |
| 501 – 1000 | 3-5 节点 | PostgreSQL | 起 read replica 计划;按区域分节点 | 考虑 nginx → CF Worker 卸载订阅请求 |
| > 1000 | 5+ 节点 | PostgreSQL + read replica | DB 升级到独立 VPS 4 vCPU / 16 GiB;监控 grafana | 准备 v0.3 Reality 仪表盘(S-R 落地) |

**信号触发器**(达到任一即按上表跳级):
- panel CPU > 60% sustained > 1h
- DB CPU > 70% sustained > 30 min
- 单节点 xray TCP `connections_active` > 800
- 订阅 endpoint p99 > 800ms
- nginx 429 比例 > 1%

---

## 10. Quarterly tasks — 季度作业

四件套,每季度第一周跑一遍并写在 SESSIONS.md 季度回顾。

### 10.1 Tranco top-1k 刷新(Reality SNI 候选)

```bash
# 拉最新 Tranco 列表,喂给 SNI 选型器(由 S-R session 维护)
curl -fsSL https://tranco-list.eu/top-1m.csv.zip -o /tmp/tranco.zip
unzip -p /tmp/tranco.zip | head -1000 > /opt/aegis/data/sni/tranco-top1k.csv

# 重跑 SNI 审计,刷新候选库
docker compose ... exec panel marzneshin sni audit --refresh
```

候选维护规范见 [OPS-sni-runbook.md](./OPS-sni-runbook.md);本节只触发刷新,不做候选挑选。

### 10.2 JWT secret 轮换(预防性)

```bash
# 走 §7.9 路径 B(无备份重生成),期间 admin 重登一次
NEW=$(openssl rand -base64 64)
sudo sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${NEW}|" /opt/aegis/.env
docker compose ... restart panel
```

### 10.3 Marznode gRPC cert 轮换

依赖 D.3 的 `cert-rotate.yml` Ansible playbook(SPEC §"Risks" §证书轮换):

```bash
cd /opt/aegis/src/deploy/ansible
ansible-playbook -i inventory.yml cert-rotate.yml --ask-vault-pass
```

Playbook 顺序:下发新 CA → 控制面切新 cert → 24h grace period → 清旧 CA。
**不要绕过 grace period**,否则节点掉线。

### 10.4 sentinel 重置 + sudo 密码轮换

```bash
# 完整重装测试(在 staging 跑,不要直接打生产)
sudo rm -f /opt/aegis/.install-step-*.done
sudo ./deploy/install/install.sh --upgrade

# admin 密码轮换(沿用 §6.2)
docker compose ... exec panel \
  marzneshin admin update --username admin \
    --new-password "$(openssl rand -base64 18)"
```

---

## 11. 联络与通告

| 渠道 | 用途 | 模板位置 |
|---|---|---|
| Telegram 群(admin only) | 应急同步 | 私域,不入仓库 |
| 用户公告 channel | 维护窗口预告 / 故障跟进 | `docs/ai-cto/private/announcement-templates.md` |
| 运营邮件列表 | 月度 newsletter / 重大变更 | 同上 |

事故分级与响应时限:

| Sev | 定义 | 响应时限 | 通告 |
|---|---|---|---|
| 1 | 全量不可用 / secret 泄露 | ≤ 15 min | 群 + 用户公告 |
| 2 | 单通道(如 EPay)不可用 | ≤ 60 min | 群 |
| 3 | 性能下降但功能完好 | ≤ 4h | 群 |

---

## 12. 附录:命令速查

`install.sh` flag 全集见 [`deploy/README.md`](../../deploy/README.md) §"Flags"。

```bash
# Ansible
ansible-playbook -i inventory.yml site.yml --ask-vault-pass --check        # 干跑
ansible-playbook -i inventory.yml site.yml --limit data_plane              # 只动节点
ansible-playbook -i inventory.yml site.yml --tags marznode                 # 只跑 marznode role

# Compose
docker compose -f /opt/aegis/src/deploy/compose/docker-compose.prod.yml ps
docker compose ... logs --tail 200 -f panel
docker compose ... exec panel bash

# Alembic
docker compose ... exec panel alembic current
docker compose ... exec panel alembic upgrade head
docker compose ... exec panel alembic downgrade <rev>

# CF API(curl,token 走 env)
curl -fsSL -H "Authorization: Bearer $CF_API_TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify | jq

# AGPL self-check
bash /opt/aegis/src/deploy/compliance/agpl-selfcheck.sh --url https://panel.example.com
```

---

## 13. 已知遗留 / 后续 OPS runbook 迭代

以下场景在本次 D.5 fleshed 中**未给出完整 remediation**,需后续 OPS runbook 迭代补:

- **§2 / §3.2 / §10.3 依赖 D.2 + D.3 PR**:`deploy/marznode/install-node.sh`、
  `deploy/ansible/`、`cert-rotate.yml` 在 D.5 push 时尚未合并;路径与命令以 SPEC §"Ansible 职责"
  为准,具体 flag 名等 D.2/D.3 落地后再校对。
- **§5.1 备份脚本**:示例脚本 `backup-pg.sh` 未提交到仓库(本 PR 仅 docs + 1 workflow),
  下一轮 OPS 迭代落到 `deploy/install/lib/backup-pg.sh` 并入 install.sh `--backup-only` 旗。
- **§7.3 / §7.4 marzneshin CLI 子命令**(`billing webhook-log`, `billing trc20-status`,
  `user bulk-enable` 等)是 forward-looking,部分尚未实现 → 待后续 PR 补 CLI 后再链接到此处。
- **§11 通告模板**目录 `docs/ai-cto/private/announcement-templates.md` 是私域(gitignore),
  此 runbook 只声明位置,模板内容在 private/ 维护。
- **§7.5 监控指标**(panel CPU、DB CPU、p99 等阈值)在 v0.3 Reality 仪表盘(S-R)落地后
  自动化告警;本 runbook 暂只列阈值,采集靠 `docker stats` 手动。

---

## 变更日志

- **2026-04-23** — 骨架建立(docs-only,S-D session 开);每节仅占位,D.5 待 flesh out。
- **2026-04-28** — D.5 flesh-out:0–12 章覆盖前置 / 首装 / 多节点 / 加节点 / 升级回滚 /
  备份还原 / 10 类应急场景 / AGPL 合规 / 容量规划 / 季度作业 / 联络通告 / 命令速查;
  四段式应急条目(检测 / 判定 / 处置 / 验证)落地;依赖 D.2/D.3 的章节明确标记
  forward-looking;同 PR 落地 `.github/workflows/deploy-smoke.yml` CI 冒烟。
