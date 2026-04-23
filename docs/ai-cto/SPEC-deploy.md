# SPEC — 部署一体化(S-D session)

> **状态**:骨架,待 S-D session 首日 flesh out。
>
> 本文件是 S-D session 的交付契约。S-D session 读完这份 spec 的
> 当前骨架后,第一件事是把每个章节的 TBD 补齐并以 PR 形式提交
> **仅这份 spec 的扩充**(不含任何 `deploy/**` 代码)。SPEC 合并后,
> 后续 PR 按本 spec 落地 `deploy/**`。
>
> 参考:CTO handbook §7 Spec-Driven。

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

## What(目标)

**一键部署**:商业化机场运营者在首次拿到 VPS 到 panel 可用
之间 ≤ 15 分钟,覆盖以下场景:

- 单节点(控制面 + marznode 同机,SQLite)—— MVP 个人运营
- 单节点 + 外置 PG(控制面 + marznode 同机,PostgreSQL)—— 成长期
- 多节点(控制面 + N 个独立 VPS 跑 marznode,PG)—— 商业运营
- Cloudflare Tunnel 前置(第 4 件加固套件)—— 隐藏真实 IP

操作人门槛:懂得 SSH、用过 `ufw`。不假设会 Ansible / K8s。

## Why

引自 `AUDIT.md` 的未解决 🔴:**部署长链路手动** —— 每新增一个节点
要 SSH + docker-compose + 证书 + gRPC 握手 + 订阅路由,2 小时起;
**>200 用户商业场景下 N 节点累加,CF Tunnel 手动配更容易出错,
是 differentiation #4/#5 落地瓶颈。**

## 核心非目标(明确写出来避免 scope creep)

- ❌ 不支持 K8s(太重;商业机场 >200 用户 99% 单到 3 节点够用)
- ❌ 不自动申请证书(让操作者自己跑 certbot,我们提供 hook)
- ❌ 不触碰 Marzban/Marzneshin 上游目录结构
- ❌ 不加新依赖到 Python 侧

---

## How(实施大纲 —— S-D 补 TBD)

### 目录结构

```
deploy/
├── README.md               # 操作者第一眼看的入口
├── install.sh              # 单节点 / 控制面一键
├── .env.example            # 环境变量模板(运行时复制成 .env)
├── docker-compose.yml      # 本 repo 根已有一份;本目录下是扩展版
├── marznode/
│   └── docker-compose.yml  # marznode 独立 VPS 场景
├── ansible/
│   ├── inventory.example.yml
│   ├── site.yml            # 控制面 + N 节点
│   └── roles/
│       ├── marzneshin/     # 控制面
│       └── marznode/       # 数据面
├── cloudflare/
│   ├── cloudflared.config.yml.template
│   └── install-tunnel.sh   # 自动建 tunnel + 配 DNS 记录
└── pg/
    └── init.sql            # PG 16 初始化(schema 由 alembic 管,此处只 CREATE DATABASE)
```

### install.sh 职责

1. 检查依赖:`docker`, `docker-compose`, `curl`, `openssl`(足够就行,不强装)
2. 交互式或 flags 驱动:
   - DB 选择(SQLite / PG)
   - marznode 部署模式(同机 / skip)
   - 域名(用于 subscription URL / CF Tunnel)
   - JWT secret(自动生成)
3. 渲染 `.env`
4. 起 `docker-compose up -d`
5. 等 panel 健康(`GET /api/system/info` 200)
6. 显示首次管理员 credentials(随机生成)
7. 输出 "下一步" checklist

### Ansible 职责(多节点)

**控制面 role(`marzneshin`)**:
- 装 Docker + compose plugin
- `git clone` 本 repo 的 tag
- 运行 `deploy/install.sh` 的非交互变体
- 启 systemd 单元(`marzneshin-panel.service`,wrap docker-compose)

**数据面 role(`marznode`)**:
- 装 Docker
- 拉 marznode 镜像
- 接收控制面的 gRPC cert(从 inventory 或 Ansible Vault)
- 启 `marznode-node.service`

### CF Tunnel 自动化(`deploy/cloudflare/install-tunnel.sh`)

- 假设运维已拿到 CF API token(单独 scope:Tunnel + DNS)
- 用 `cloudflared tunnel create aegis-<instance>` 建 tunnel
- 写 `cloudflared.config.yml`(公网 hostname → `localhost:<panel_port>`)
- 写 CF DNS CNAME 指 tunnel
- 启 `cloudflared.service`

### 回滚 / 升级路径

- 升级:`git pull && docker-compose pull && docker-compose up -d`
- 回滚:`git checkout <old-tag> && docker-compose up -d`
- DB 迁移:`alembic downgrade -1`(但 Alembic 不变性规则 L-015 警告:
  已 merge 的 migration 不可 mutate;回滚语义是回到 spec 的 `down`)

---

## Acceptance criteria(待 S-D 补测试细节)

**Install.sh 单节点**:
- [ ] Fresh Ubuntu 24.04 VPS → `curl ... | bash` → panel 可 HTTPS 登录 ≤ 15 min
- [ ] SQLite + PG 两种 DB 选项都工作
- [ ] 生成的 .env 能 override 常见字段(DB URL、域名、port)
- [ ] 脚本 idempotent:重跑不破坏已有状态,问 "是否覆盖"

**Ansible 多节点**:
- [ ] 2-marznode inventory 从零到全绿 ≤ 30 min
- [ ] 控制面重启 → 节点自动重连(gRPC cert 持久)
- [ ] 加第 3 个节点只需改 inventory + `ansible-playbook`

**CF Tunnel**:
- [ ] 不暴露 panel 真实 IP(`dig` 只返回 CF 的 IP)
- [ ] 撤销 tunnel 的 script 存在

**运维**:
- [ ] `deploy/OPS-deploy-runbook.md` 覆盖:节点迁移、DB 备份、证书轮换、CF token 泄露应急

## Risks(待 S-D 补对策)

| 风险 | 对策(待 S-D 补) |
|---|---|
| install.sh 在非 Ubuntu 24.04 发行版崩 | TBD |
| Ansible idempotency 和 install.sh 冲突 | TBD |
| CF API rate limit | TBD |
| marznode gRPC cert 分发方式 | TBD(Vault? manual scp? bootstrap endpoint?) |
| 用户自己改了 docker-compose.yml 导致升级冲突 | TBD |

---

## PR sequencing(S-D 落地节奏)

1. **D.0**:本 spec 补全,docs-only PR
2. **D.1**:`deploy/install.sh` + `.env.example` + `deploy/README.md` 单节点 MVP
3. **D.2**:`deploy/marznode/docker-compose.yml` + install.sh 支持独立节点模式
4. **D.3**:Ansible inventory + 2 roles,2 节点场景能跑
5. **D.4**:`deploy/cloudflare/` 脚本
6. **D.5**:`OPS-deploy-runbook.md` 完整版

每个 PR ≤ 500 LOC,审查负担可控。
