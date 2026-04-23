# SPEC — 部署一体化(S-D session)

> **状态**:`D.0` 定稿中 —— S-D session 首轮 flesh-out。
>
> 本文件是 S-D session 的交付契约。SPEC 合并后,后续 PR 按本 spec
> 落地 `deploy/**`。任何 `deploy/**` 代码改动必须能引用到本 SPEC
> 的某条 Acceptance criterion,否则 scope creep。
>
> 参考:CTO handbook §7 Spec-Driven。
> 对接:`compass_artifact_wf-5103cc40-*.md`(Reality 2026 五件套)、
> `docs/ai-cto/VISION.md` §创新机会 #3/#4、`docs/ai-cto/ROADMAP.md` v0.2、
> `deploy/README.md`。

## Kickoff prompt(粘贴到新 Claude Code 会话第一条消息)

```
/cto-resume

你是 Aegis Panel 项目 S-D session(部署一体化,ROADMAP 差异化 #4/#5)。

读这三份文件作为上下文:
- docs/ai-cto/SESSIONS.md(§S-D Charter)
- docs/ai-cto/VISION.md
- compass_artifact_*.md 五件套(冷门 SNI / 同 ASN / 非标准端口 /
  CF Tunnel / Vision+短 connIdle),尤其是 CF Tunnel 那份

你的地盘独占: deploy/** + docs/ai-cto/SPEC-deploy.md +
docs/ai-cto/OPS-deploy-runbook.md
禁动: app/**, ops/**, hardening/**, dashboard/**
共享冲突点: .github/workflows/ 只能新增文件不能改现有

第一步: 把本 SPEC 骨架的每个 TBD 段落补完整(Scope / How /
Acceptance criteria / Risks),开 docs-only PR。SPEC 通过后再动
任何 deploy/** 代码。严格 Spec-Driven。
```

---

## Scope

### 交付物(S-D session 最终产出)

| 分类 | 产物 | PR 归属 |
|---|---|---|
| 脚本 | `deploy/install/install.sh`(单节点)+ 非交互变体 | D.1 |
| 脚本 | `deploy/marznode/install-node.sh`(独立数据面) | D.2 |
| 配置 | `deploy/compose/docker-compose.prod.yml`(含 pg + redis + panel + marznode + nginx) | D.1 |
| 配置 | `deploy/.env.example`(含 compass 五件套强化默认值) | D.1 |
| IaC | `deploy/ansible/`(inventory template + 2 roles) | D.3 |
| IaC | `deploy/cloudflare/`(Tunnel create / DNS / Access policy) | D.4 |
| 工具 | `deploy/compliance/agpl-selfcheck.sh`(差异化 #4) | D.4 |
| 文档 | `deploy/README.md`(运维者第一入口) | D.1 |
| 文档 | `docs/ai-cto/OPS-deploy-runbook.md`(事件应急 + 日常运维) | D.5 |
| CI | `.github/workflows/deploy-smoke.yml`(不改现有 workflows) | D.1 |

### 场景矩阵(覆盖面)

| 场景 | 控制面 DB | 节点数 | CF Tunnel | 对应 PR |
|---|---|---|---|---|
| S1 — 个人 MVP | SQLite | 1(同机 marznode) | 可选 | D.1 |
| S2 — 成长期 | PostgreSQL | 1(同机 marznode) | 推荐 | D.1 + D.2 |
| S3 — 商业运营 | PostgreSQL | 1 控制面 + 2-10 节点 | 必须 | D.3 + D.4 |
| S4 — 异地灾备(out) | — | — | — | 不在 v0.2 范围 |

### 用户画像(操作门槛基线)

- 会用 SSH,用过 `ufw` 或 `iptables` 基础命令
- 读得懂简单 `.env`
- **不假设**会:Ansible、K8s、Terraform、编写 Jinja2 模板
- 目标:运营 >200 付费用户、3-10 VPS 的独立机场主(对齐 VISION §目标用户)

### Out-of-scope(明确划出去)

- ❌ K8s(太重;>10 节点才值得,当前商业机场 <1% 到这个规模)
- ❌ 证书自动签发(提供 certbot hook 调用,不重写 ACME 客户端)
- ❌ 多云 provider abstraction(目前只测 Hetzner / RackNerd / Oracle Cloud)
- ❌ 不触碰 `app/**`、`hardening/**`、`ops/**`、`dashboard/**` 现有代码
- ❌ 不新增 Python 运行时依赖;Ansible / cloudflared / docker 等是**部署工具**,
  操作者宿主机装,panel 进程不 import
- ❌ 不自研 monitoring;Grafana/Prometheus stack 留给 v0.3 Reality 仪表盘(S-R)

---

## Why

引自 `AUDIT.md` 未解决 🔴 和 VISION.md 差异化 #3/#4:

1. **部署长链路手动** —— 每新增节点 SSH + docker-compose + 证书 + gRPC
   握手 + 订阅路由,2 小时起;>200 用户商业场景下 N 节点累加,CF Tunnel
   手动配更容易出错,是 differentiation bottleneck。
2. **合规风险** —— AGPL-3.0 要求网络对用户提供服务时可获取源码;手动部署
   易漏源码披露入口。`deploy/compliance/agpl-selfcheck.sh` 是差异化 #4。
3. **加固套件应用门槛** —— compass_artifact 五件套(冷门 SNI / 同 ASN /
   非标准端口 / CF Tunnel / Vision+短 connIdle)每件手动配都要翻文档。
   部署引擎要作为**默认安全基线**把五件套打进 `.env.example` 与 compose,
   降低用户误配面。

---

## How(实施大纲)

### 目录结构

```
deploy/
├── README.md                        # 运维者第一入口(已存在,D.1 补全)
├── install/
│   ├── install.sh                   # 单节点主入口
│   ├── lib/                         # bash 辅助函数(os 检测 / 渲染 / 等健康)
│   │   ├── detect.sh
│   │   ├── render.sh
│   │   └── health.sh
│   └── templates/
│       ├── env.tmpl                 # .env 模板(含 compass 五件套注释)
│       └── nginx.conf.tmpl
├── .env.example                     # 同步自 install/templates/env.tmpl 的导出
├── compose/
│   ├── docker-compose.prod.yml      # pg + redis + panel + marznode + nginx
│   └── docker-compose.sqlite.yml    # S1 轻量(无 pg / redis)
├── marznode/
│   ├── install-node.sh              # 独立 VPS 数据面
│   └── docker-compose.yml
├── ansible/
│   ├── inventory.example.yml
│   ├── site.yml                     # playbook 入口
│   └── roles/
│       ├── common/                  # docker / ufw / fail2ban
│       ├── marzneshin/              # 控制面 role
│       └── marznode/                # 数据面 role
├── cloudflare/
│   ├── install-tunnel.sh            # tunnel create + DNS CNAME
│   ├── setup-access.sh              # Access policy(邮箱 OTP / SSO)
│   └── cloudflared.config.yml.template
├── compliance/
│   └── agpl-selfcheck.sh            # 版权头 / 源码披露入口 / license 扫描
└── pg/
    └── init.sql                     # CREATE DATABASE / ROLE;schema 归 alembic
```

### install.sh 职责(D.1)

1. **依赖检测**(不强装,给出安装命令):`docker (≥24)`, `docker compose (v2 插件)`,
   `curl`, `openssl`, `jq`。缺失时打印具体 `apt-get install ...` 命令,exit 1。
2. **OS 识别**:优先支持 Ubuntu 22.04 / 24.04 LTS、Debian 12。其他发行版
   给 warning + `--force` 继续。Detection 走 `/etc/os-release` 的 `ID` + `VERSION_ID`。
3. **交互式 vs 非交互**:
   - 默认交互(`read -p`),
   - `--non-interactive` 从 flags / 环境变量取值(供 Ansible 调用),
   - `--from-env FILE` 从现有 `.env` 继承值,跳问。
4. **关键参数收集**:
   - `--db {sqlite|postgres}`(默认 postgres,S1 用户显式选 sqlite)
   - `--marznode {same-host|skip}`(默认 same-host)
   - `--domain <fqdn>`(必填;用于 subscription URL / CF Tunnel / nginx)
   - `--admin-username` / `--admin-password`(空则自动生成 24 字符随机)
   - `--jwt-secret`(空则自动生成 64 字节 base64)
   - `--cf-tunnel {yes|no|skip}`(默认 skip,yes 链式调用 `cloudflare/install-tunnel.sh`)
5. **渲染 `.env`**:从 `templates/env.tmpl` 填坑,写 `/opt/aegis/.env`,600 权限。
   内置 compass 五件套默认值(见 `.env.example 强化项` 段)。
6. **启动**:`docker compose -f compose/docker-compose.prod.yml up -d`。
7. **等待健康**:轮询 `GET http://127.0.0.1:$PANEL_PORT/api/system/info`
   直到 200(最长 120s,超时抛 `docker compose logs` 尾 50 行后 exit 1)。
8. **首次 admin 凭据输出**:打印到 stdout 且同时写 `/opt/aegis/INSTALL-SUMMARY.txt`(600)。
9. **下一步 checklist**:打印 `ufw allow` / 证书安装 / CF Tunnel(如未 bundled)/
   订阅 URL 测试 / AGPL 自检脚本 等后续命令清单。

**幂等实现**:脚本入口检查 `/opt/aegis/.env` 是否存在,存在则进入 "已安装"
分支 —— 读 `.env.version` 与当前 repo tag 比对,版本相同则只 `compose up -d`
(相当于 restart);版本不同问 "是否升级",升级走 `git pull && compose pull && compose up -d`。
每一步关键动作用 sentinel 文件(如 `/opt/aegis/.install-step-{1..9}.done`)标记,
中断重跑从下一步继续。

**非交互模式下的输出契约**:
- stdout:机器可读 KV(`admin_username=...\nadmin_password=...\ndashboard_url=...`)
- stderr:人类可读进度
- exit code:0 成功 / 1 依赖缺失 / 2 配置非法 / 3 健康检查超时 / 4 端口占用

### .env.example 强化项(compass 五件套应用)

默认值来自 compass_artifact "管理面板加固" + "SNI 选择" 节:

```bash
# === 核心安全 ===
UVICORN_HOST=127.0.0.1                   # 不开 SSL 强制 localhost,对外走 CF Tunnel / nginx
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=45        # compass 推荐 ≤60,取保守值
DASHBOARD_PATH=/__RANDOMIZE_ON_INSTALL__  # install.sh 渲染为随机 8 字符
XRAY_SUBSCRIPTION_PATH=/__RANDOMIZE_ON_INSTALL__  # 同上
ADMIN_LOGIN_RATE_LIMIT=5/minute           # 依赖 slowapi(v0.1 已引入)

# === Xray 策略(策略值由 panel 生成的 config 消费,这里只记运维侧默认) ===
XRAY_POLICY_CONN_IDLE=120
XRAY_POLICY_HANDSHAKE=2

# === 默认非标端口(对齐 compass "非标准端口") ===
PANEL_PORT=8443
MARZNODE_GRPC_PORT=62051

# === CF Tunnel 开关(install.sh --cf-tunnel yes 时自动置 true) ===
CF_TUNNEL_ENABLED=false
CF_ACCESS_REQUIRED_FOR_ADMIN=true         # 启 tunnel 时强制 Access policy
```

### Ansible 职责(D.3,多节点)

**`roles/common/`**:
- 装 Docker CE + compose v2 插件(apt repo 方式,不用 snap)
- 配 `ufw`:allow 22, 443, `PANEL_PORT`(仅控制面),`MARZNODE_GRPC_PORT`(仅节点,source 限制为控制面 IP)
- 装 `fail2ban` 默认规则(ssh + nginx-badbots)
- 创建 `aegis` 系统用户 + `/opt/aegis` 目录

**`roles/marzneshin/`**(控制面):
- `git clone` 本 repo 到 `/opt/aegis/src`,checkout 指定 tag
- 调用 `deploy/install/install.sh --non-interactive --from-env` 读 Ansible 渲染的 env
- 部署 systemd unit `aegis-panel.service`(wrap `docker compose -f compose/docker-compose.prod.yml`)
- 生成 / 获取 marznode gRPC 客户端证书,放 `/opt/aegis/certs/marznode-client.{crt,key}`
- Alembic `upgrade head` 在 compose up 前跑(同一 compose 中的 init 容器)

**`roles/marznode/`**(数据面):
- 装 Docker
- 拉 `marzneshin/marznode:<tag>` 镜像
- **证书分发**:两种模式
  - `cert_mode: vault` —— Ansible Vault 加密 CA + 下发给节点(生产推荐)
  - `cert_mode: bootstrap` —— 节点首次启动向控制面 `/api/nodes/{id}/bootstrap` 发 one-time token 交换证书(离线场景)
- 部署 systemd unit `aegis-marznode.service`
- 配 healthcheck(`grpc_health_probe -addr=:62051`)

**Inventory 示例**(`inventory.example.yml` 片段):

```yaml
all:
  vars:
    aegis_version: v0.2.0
    aegis_domain: panel.example.com
    cert_mode: vault
  children:
    control_plane:
      hosts:
        panel.example.com:
          ansible_host: 1.2.3.4
    data_plane:
      hosts:
        node-tokyo:
          ansible_host: 5.6.7.8
          marznode_id: 1
        node-singapore:
          ansible_host: 9.10.11.12
          marznode_id: 2
```

### CF Tunnel 自动化(D.4,`deploy/cloudflare/`)

**前置**:操作者持有 CF API token,scope 限定:`Zone.DNS:Edit` + `Account.Cloudflare Tunnel:Edit` + `Account.Access:Edit`(不给全局 token)。

**`install-tunnel.sh`**:
1. `cloudflared tunnel create aegis-$(hostname -s)`,抓 tunnel UUID
2. 渲染 `cloudflared.config.yml`:ingress `$PANEL_DOMAIN` → `http://localhost:$PANEL_PORT`
3. 调 CF API 建 CNAME:`$PANEL_DOMAIN` → `<tunnel-uuid>.cfargotunnel.com`
4. 装 `cloudflared.service`(systemd)并 `systemctl enable --now`
5. 验证:`curl -sI https://$PANEL_DOMAIN` 200

**`setup-access.sh`**:
1. CF API 建 Access App,host = `$PANEL_DOMAIN`,path = `$DASHBOARD_PATH`
2. 附 Access Policy:`include.emails = $ADMIN_EMAILS`(从 .env 取)
3. Session duration ≤ 24h,require MFA
4. 验证:未登录访问应 302 到 CF Access 登录页

**撤销脚本 `uninstall-tunnel.sh`**:删 Access App → 删 DNS → 删 tunnel → 清 local config。

### 合规一键自检(D.4,差异化 #4)

**`deploy/compliance/agpl-selfcheck.sh`**:

| 检查项 | 判定 |
|---|---|
| 上游版权头保留 | grep `Marzneshin` 在 `LICENSE` / `NOTICE.md`,缺失 FAIL |
| 源码披露入口 | `curl -sI https://$PANEL_DOMAIN/api/source` 200 或 dashboard footer 含 GitHub 链接,两者皆缺 FAIL |
| Python 依赖 license 扫描 | `pip-licenses --format=json` → 过滤 GPL incompatible(AGPL/GPL/LGPL 混入第三方 = PASS;纯 MIT/Apache = PASS;proprietary = FAIL) |
| dashboard 依赖 license | `pnpm licenses ls` → 同上逻辑 |
| `.env` 未提交 | `git ls-files | grep '^\.env$'` 空 = PASS |
| JWT secret 不是示例值 | `.env` 中 JWT_SECRET ≠ `change-me-*` = PASS |

输出:`deploy/compliance/report-$(date +%Y%m%d).txt`,PASS/FAIL 清单 + 修复建议。

### 回滚 / 升级路径

- **升级(minor)**:`cd /opt/aegis/src && git fetch --tags && git checkout <new-tag> && ./deploy/install/install.sh --upgrade`
- **回滚(紧急)**:`git checkout <prev-tag> && docker compose -f compose/docker-compose.prod.yml up -d`
  - ⚠️ DB migration 回滚受 LESSONS **L-015 Alembic 不变性** 约束:
    - 已 merge 的 revision 不可删除 / 改 `down_revision`
    - 回滚走 `alembic downgrade <prev-rev>`;若 downgrade 语义不干净,此次升级不可回滚,只能滚前
    - install.sh `--upgrade` 先跑 `alembic current` 记录当前 rev,失败时提示 `alembic downgrade <that-rev>`
- **数据备份前置**(升级必走):`pg_dump` → `/opt/aegis/backups/pre-upgrade-$(date +%s).sql.gz`,保留最近 10 份。

---

## Acceptance criteria

### D.1 — 单节点 install.sh

- [ ] **AC-D.1.1** Fresh Ubuntu 24.04 VPS(2 vCPU / 4GB RAM),`curl ... | bash` → panel HTTPS 可登录,耗时 ≤ 15 min(不含证书签发等待)
- [ ] **AC-D.1.2** `--db sqlite` 与 `--db postgres` 两模式均能跑到 panel 健康,subscription URL 能拉到订阅
- [ ] **AC-D.1.3** 生成的 `.env` 中 `DASHBOARD_PATH` 与 `XRAY_SUBSCRIPTION_PATH` 均为 8+ 字符随机串,非默认值
- [ ] **AC-D.1.4** 脚本 idempotent:同一 VPS 重跑 3 次,第 2/3 次结束状态与第 1 次完全一致(`diff /opt/aegis/.env` 空)
- [ ] **AC-D.1.5** 中断重跑:kill 进程在第 5 步后,重跑从第 6 步继续(sentinel 文件生效)
- [ ] **AC-D.1.6** 非交互模式的 stdout KV 输出被 Ansible `register` 正确解析(单测用 `bash -c` + 正则 assert)
- [ ] **AC-D.1.7** Debian 12 上全流程能跑(warning 后用户显式继续)
- [ ] **AC-D.1.8** CentOS/Alma 系显式拒绝安装并给出切换发行版建议(不崩溃)
- [ ] **AC-D.1.9** 端口占用时 exit code = 4,报错含占用进程 PID

### D.2 — 独立 marznode

- [ ] **AC-D.2.1** 控制面 VPS 已运行,新 VPS 跑 `marznode/install-node.sh --control-plane=... --node-id=2`,30s 内控制面 dashboard 显示新节点 online
- [ ] **AC-D.2.2** 控制面重启,节点 60s 内自动重连(gRPC cert 持久 + retry backoff)
- [ ] **AC-D.2.3** 节点 VPS 的 `ufw status` 只开 22 + 62051(62051 source 限控制面 IP)

### D.3 — Ansible 多节点

- [ ] **AC-D.3.1** 2 marznode inventory 从零 `ansible-playbook site.yml` 到全绿 ≤ 30 min
- [ ] **AC-D.3.2** 加第 3 节点只改 inventory 再跑 `site.yml --limit data_plane`,不触控制面
- [ ] **AC-D.3.3** `ansible-playbook site.yml --check` 在已部署环境输出 0 change(幂等性)
- [ ] **AC-D.3.4** `cert_mode: vault` 和 `cert_mode: bootstrap` 两种证书分发路径均有 smoke test

### D.4 — CF Tunnel + 合规

- [ ] **AC-D.4.1** `install-tunnel.sh` 跑完,`dig $PANEL_DOMAIN` 只返回 CF Anycast IP,不含源站 IP
- [ ] **AC-D.4.2** 未在 Access 白名单的邮箱访问 dashboard 302 到 CF 登录页
- [ ] **AC-D.4.3** `uninstall-tunnel.sh` 撤销后,CF 控制台无残留 tunnel / Access app / DNS 记录
- [ ] **AC-D.4.4** `agpl-selfcheck.sh` 在干净安装上全 PASS;故意改 `NOTICE.md` 删版权头后对应项 FAIL

### D.5 — 运维文档

- [ ] **AC-D.5.1** `OPS-deploy-runbook.md` 覆盖:节点迁移、PG 备份/还原、cert 轮换、CF token 泄露应急、升级失败回滚、DASHBOARD_PATH 被扫描应对
- [ ] **AC-D.5.2** Runbook 的每个应急场景含:检测命令 / 判定条件 / 处置步骤 / 验证命令
- [ ] **AC-D.5.3** Runbook 经至少 1 次真实 dry-run(CTO 在测试 VPS 跑一遍记录)

### CI 契约

- [ ] **AC-CI.1** `.github/workflows/deploy-smoke.yml` 在 PR 触发,跑:shellcheck `install.sh` + ansible-lint + `bash -n` 语法检查
- [ ] **AC-CI.2** 新 workflow 文件,不修改现有 `.github/workflows/*.yml`(对齐 SESSIONS §冲突地带)

---

## Risks

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| `install.sh` 在非 Ubuntu 24.04 发行版崩(CentOS/Alma、老 Debian) | 中 | 中 | **分层支持**:Ubuntu 22/24 + Debian 12 = tier-1(CI 测);其他发行版 pre-flight 检测不通过时**显式拒绝并给 tier-1 升级建议**,不做 "尽力而为"(会留下半装状态更难排错) |
| Ansible idempotency 与 install.sh 重跑语义冲突(两边都想管 sentinel) | 中 | 高 | `install.sh --from-env /opt/aegis/.env --non-interactive` 是 Ansible 唯一调用入口;Ansible 不直接写 `.env`,只写 `group_vars`;sentinel 文件权威方是 `install.sh` |
| CF API rate limit(1200 req/5min per token)在 Ansible 批量建 N 节点时触顶 | 低 | 中 | `install-tunnel.sh` 串行执行 + `sleep 0.5`;Ansible role 对 CF 相关任务加 `throttle: 1` |
| marznode gRPC cert 分发方式选错导致泄露 | 低 | **极高** | 默认 `cert_mode: vault`(强制 Ansible Vault 加密);`bootstrap` 模式明确标注 "生产不推荐",one-time token 5 分钟失效,用过即弃 |
| 用户自己改了 `compose/docker-compose.prod.yml` 导致 `git pull` 升级冲突 | 高 | 中 | `install.sh` 生成 `compose/overrides/local.yml` 供用户改(git-ignore),主 compose 文件 **`chattr +i` 可选**(README 说明);升级时 `git stash` 检测到 override 以外的改动则中止,要求人工介入 |
| JWT secret 随机但 `.env` 备份泄露 | 中 | **极高** | `.env` 600 权限 + `/opt/aegis` 目录 700 + ownership `aegis:aegis`;runbook 写 "JWT 轮换" 流程(改 `.env` → restart → 旧 token 立即失效) |
| CF Tunnel 服务中断(CF 侧故障),panel 不可达 | 低 | 高 | 保留 **备用入口**:nginx 监听非标端口(默认 8443)+ IP allowlist(源站直连 fallback);runbook 写切换流程 |
| 证书轮换时控制面与节点 cert 不一致,节点掉线 | 中 | 高 | `ansible-playbook cert-rotate.yml`(D.3 role 内置):先下发新 CA 到所有节点 → 控制面切新 cert → 旧 CA grace period 24h → 清旧 CA |
| 脚本在低内存 VPS(1GB)上 OOM(pg + redis + panel + marznode 同机) | 中 | 中 | `install.sh` pre-flight 检查 `/proc/meminfo`:< 2GB 时拒绝装 pg,强制 `--db sqlite` 或 `--marznode skip`;README 明确 S1 最低配置 |
| 幂等性回归(新 PR 意外破坏 idempotency) | 中 | 高 | CI `deploy-smoke.yml` 跑 `install.sh` 两次,diff `/opt/aegis/.env` 必须空;作为 D.1 合并卡点 |
| AGPL 自检误报(合法的 LGPL 依赖被判 FAIL) | 中 | 低 | 维护 `deploy/compliance/license-allowlist.txt`,PR review 时人工新增条目;自检 script 对 allowlist 内的 license 降级为 WARNING |
| CF token 误提 commit | 低 | **极高** | pre-commit hook(`.agents/rules/` 声明)+ `agpl-selfcheck.sh` 增一条 `grep CF_API_TOKEN in git log -p`;若命中立即告警 "rotate token NOW" |

---

## PR sequencing(S-D 落地节奏)

1. **D.0** — 本 SPEC flesh-out,docs-only PR(本 PR)
2. **D.1** — `deploy/install/install.sh` + `.env.example` + `compose/docker-compose.prod.yml` + `compose/docker-compose.sqlite.yml` + `deploy/README.md` 更新 + `deploy-smoke.yml` CI;验收 S1/S2 场景 AC-D.1.*
3. **D.2** — `deploy/marznode/install-node.sh` + `marznode/docker-compose.yml`;验收 AC-D.2.*
4. **D.3** — `deploy/ansible/`(common + marzneshin + marznode 3 roles + inventory template);验收 AC-D.3.*
5. **D.4** — `deploy/cloudflare/`(tunnel + access + uninstall)+ `deploy/compliance/agpl-selfcheck.sh`;验收 AC-D.4.*
6. **D.5** — `docs/ai-cto/OPS-deploy-runbook.md` 完整版 + CTO dry-run 记录;验收 AC-D.5.*

每个 PR ≤ 500 LOC(bash + yaml + markdown 合计);超限拆子 PR。每个 PR body 必须:
- 引用本 SPEC 的 AC-D.x.y 编号列为验收勾选
- "I touch:" / "I don't touch:"(对齐 SESSIONS §铁规则 #4)
- 链接 `docs/ai-cto/SESSIONS.md`

---

## 变更日志

- **2026-04-23** — S-D session 首轮 flesh-out(Scope 显式化 + How 填坑 + Acceptance criteria 细化到 AC-D.x.y 编号 + Risks 表全部填对策 + 引入 compass 五件套默认值 + 差异化 #4 合规自检)。docs-only PR。
