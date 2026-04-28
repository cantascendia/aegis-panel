# 路线图(ROADMAP)

> 最后更新:2026-04-28 late-7 wave-2 post-merge(Round 3 mid late-7 wave-2 — **v0.2 实质完工**:商业化 5/5 + 差异化 #1 SNI + 差异化 #3 Reality 全链路闭环 + 差异化 #4 一体化部署 5/5;v0.3 SPEC 双骨架就位等决策驱动)
> 每阶段末尾或重大优先级变化时更新
>
> **当前位置**:v0.1 已完成,**v0.2 实质完工**(SNI ✅ / **计费 MVP 5/5 完结** ✅ / **一键部署引擎 5/5 全 ship** ✅ / **差异化 #3 Reality 配置审计 全链路闭环** ✅:R.1-R.3 后端 #74-#76 + R.5 OPS-runbook #82 + R.4 dashboard frontend #99),建议进入 v0.3(audit-log + RBAC + XHTTP/Hysteria2 备用通道 + 自动化 upstream 同步);v0.3 audit-log + RBAC SPEC 双骨架已 ship(PR #101),等用户拍 7 个 TBD(issue #103 #104)

---

## 总体思路

**先加固基底,再建差异化,再上商业化**。任何阶段未达标,不进入下一阶段。

时间基于"每周 20-30 小时开发投入 + CTO 并行规划"的节奏估算,实际可能浮动 30%。

---

## 优先级队列(2026-04-28 late-7 wave-2 post-merge 视角)

按"现在该推什么"排序,**v0.2 实质完工** → 进入 v0.3 队列;现阶段无 in-flight session,等用户决策驱动:

1. ✅ **S-R R.4 Reality 审计 dashboard 页**(PR #99 `5adddfe` merged) — 差异化 #3 用户可见闭环最后一公里完工
2. ✅ **v0.3 audit-log + RBAC SPEC 双骨架**(PR #101 `349db93` merged) — v0.3 scope SPEC 就位
3. ⏳ **A.x 真实 round-trip**(operator 外部任务,需用户行动) — ¥0.01 EPay + USDT 测试网各跑一遍;不在自动 queue
4. ⏳ **issue #103 audit-log 4 TBDs 拍板** — 用户决策后启动 S-AL session
5. ⏳ **issue #104 RBAC 3 TBDs 拍板**(+ 等 #103 ship 双先决条件)— 用户决策后启动 S-RB session
6. ⏳ **issue #102 R.4 follow-up tests**(4 个 component test for reality module)— S-X-2 session pre-kickoff,charter 等用户/CTO 派遣
7. ⏳ **R.5+ Reality 实时监测**(差异化 #3 v0.3 后段) — Prometheus + Grafana 长期趋势
8. ⏳ **XHTTP / Hysteria2 备用通道**(v0.3 抗封进化) — 未启
9. ⏳ **自动化 Upstream 同步**(v0.3 运维成熟) — 未启

---

## v0.1 — 基底加固 + P0 安全(4-6 周)

**目标**: 把刚 fork 的 Marzneshin 变成"可上线但还不商业化"的加固版。

### 必做(依赖顺序)

1. **P0 安全修复**(1-2 周)
   - JWT Secret 外置到 `.env`(禁止库存储)
   - Admin 登录速率限制(slowapi + Redis)
   - CORS 收紧(whitelist 具体域名)
   - JWT 时效收紧到 ≤60 分钟
   - CI 集成 `safety check` + `pip list --outdated`
   - 依赖更新:`v2share` beta → 稳定替代评估

2. **数据库切 PostgreSQL 16 + Redis 7**(1 周)
   - Alembic 迁移脚本兼容多 DB
   - Redis 作为限流令牌桶 + 用户查询缓存
   - `docker-compose.yml` 加 postgres + redis 服务

3. **测试基础设施**(1-2 周)
   - pytest fixture(DB / redis / mock marznode / mock aiohttp)
   - 关键路由端点测试(admin login / user CRUD / subscription gen)
   - GitHub Actions CI:`pytest + vitest + biome + ruff + safety`
   - Dashboard:至少 login / user-list / node-list 的组件快照测试
   - 目标覆盖率:backend ≥40%,dashboard ≥30%

4. **目录骨架 + README**(0.5 周)
   - `hardening/` + `deploy/` + `ops/` 目录 + 各自 README + LICENSE 声明
   - 根目录 `DEVELOPMENT.md`(本地启动步骤 + 常见故障排查)
   - Makefile 补全 `test / lint / format / db-reset` 目标

### 验收(**v0.1 达成,2026-04-22 确认**)

- [x] AUDIT.md 安全维度从 3/10 提升到 ≥7/10(**达到 8/10**,见 STATUS 评分表)
- [x] 测试维度从 1/10 提升到 ≥5/10(**达到 7/10**,171 passed)
- [x] CI 全绿,任何 push 自动跑完 backend + frontend 测试(lint/test/pip-audit 三门禁 + Alembic stepped-upgrade + PG16 matrix)
- [x] `/api/source` 或 dashboard footer 源码链接就位(AGPL 合规)

---

## v0.2 — 差异化落地 + 一键部署(6-8 周) — ✅ **实质完工**(2026-04-28 late-7 wave-2 post-merge)

**目标**: 让项目有**能卖的理由**。SNI 选型器 + 一键部署 + 计费 MVP + 差异化 #3 Reality 配置审计。

**完工度**: 验收 checklist 全部 ✅ 或 stretch goal(real-money round-trip 是 operator 外部环境,不阻塞 v0.3);建议正式进入 v0.3 (audit + RBAC + XHTTP + 备用通道)。

### 必做

1. **SNI 智能选型器 MVP** ✅(2026-04-22 达成,差异化 #1 用户可见闭环)
   - ✅ `hardening/sni/selector.py` CLI + 6 硬指标(PR #13)
   - ✅ `POST /api/nodes/sni-suggest` REST 端点,`apply_panel_hardening()` 注册(PR #16)
   - ✅ Dashboard 新建节点对话框 "Suggest SNI" 按钮 + 独立对话框(PR #18)
   - ✅ 41 + 10 单测 mock 网络,CI 离线可跑
   - ⏳ 遗留:SNI rate-limit(slowapi async-def 兼容,LESSONS L-010)/ runbook / 前端单测

2. **一键部署引擎 v1 + 差异化 #4 工具系列**(2-3 周)✅ **已完工 (D.1-D.5 全 ship)** —— D-017 原序列约束实操证伪(2026-04-28 修订),5 PR 当天并行 merged
   - [x] **D.0 SPEC-deploy.md flesh-out** —— PR #64
   - [x] **agpl-selfcheck.sh**(差异化 #4 第一件工具,AGPL §13 自检) —— PR #88
   - [x] **NOTICE.md fork source URL declaration** —— PR #90(closes AGPL §13 audit gap)
   - [x] **D.1 install.sh + compose + .env.example + README**(单节点一键) —— PR #95 `9787bd4`
   - [x] **D.2 marznode standalone node installer** —— PR #97 `cfc3b9a`
   - [x] **D.3 Ansible multi-node playbook** —— PR #98 `5f0ca98`
   - [x] **D.4 Cloudflare Tunnel + Access scripts** —— PR #94 `b00a9cf`
   - [x] **D.5 OPS-deploy-runbook + deploy-smoke CI**(五段流程闭环) —— PR #96 `3a969a7`
   - [x] `deploy/compose/` 生产 compose 已在 #95 落地
   - [x] OPS-deploy-runbook 完整化(骨架 #58 → 完整 #96)

3. **计费系统 MVP**(2-3 周)✅ **完结 — 5/5 端到端跑通**(2026-04-28 late-7)
   - [x] A.1 数据模型 + 状态机 + Admin REST + Admin UI 三页(plans/channels/invoices)—— PR #28-#35
   - [x] A.2.1 provider 抽象 + EPay adapter —— PR #46
   - [x] A.2.2 cart checkout + EPay webhook —— PR #65
   - [x] A.3 TRC20 直收支付通道 5 模块 —— PR #79
   - [x] A.5 APScheduler reap_expired + apply_paid grants —— PR #77
   - [x] **A.4 admin-on-behalf-of-user checkout UI**(BRIEF option A,见 D-016)—— PR #87 + #89(rename)
   - [x] OPS-trc20-runbook —— PR #81
   - **剩余 = 外部环境**:¥0.01 EPay round-trip(operator 接一家码商 stage)+ USDT 测试网 round-trip(operator 接 Tronscan stage)
   - **不做**(D-016):用户公开 web auth / 用户自助 SPA portal,除非客户真实数据点 ≥ 3 触发推翻条件

4. **差异化 #3 Reality 配置审计**(2-3 周)✅ **全链路闭环 5/5 完工**
   - [x] R.1 core(checks / scoring / report / seeds)—— PR #74
   - [x] R.2 CLI + loader + golden fixtures —— PR #75
   - [x] R.3 REST endpoint(`POST /api/reality/audit`) —— PR #76
   - [x] R.5 OPS-reality-runbook —— PR #82
   - [x] **R.4 dashboard reality module**(消费 R.3 endpoint,管理员 dashboard 审计页)—— PR #99 `5adddfe`
   - ⏳ R.4 follow-up: 4 个 component test(issue #102 跟踪,S-X-2 session pre-kickoff)

5. **审计日志系统**(1 周,可与 #3/#4 合并)—— ✅ **SPEC ship,等决策驱动启动 S-AL session**
   - [x] **SPEC-audit-log skeleton ship**(PR #101) — `AuditLog` 表骨架 + 中间件设计 + dashboard 审计页方向
   - ⏳ 4 TBDs 拍板(issue #103 跟踪): model schema 细节 / 写入策略 / 保留期限 / dashboard 筛选维度
   - 备注:billing invoices 的 `payment_events` 表已是一种窄域审计,通用 AuditLog 在 SPEC 中已定位为合并设计

### 验收

- [x] 新节点创建流程中 SNI 候选自动预填,用户 80% 场景不用手填(PR #18 达成)
- [x] 从空 VPS 到面板可访问用时 ≤15 分钟(install.sh 跑完,PR #95 达成)
- [x] 管理员能为用户 "激活订阅" + 查看到期提醒 + 查看订阅历史(激活 ✅;A.5 自动 grant ✅;admin checkout #87 ✅)
- [x] 差异化 #3 Reality 配置审计 用户可见闭环(R.4 dashboard PR #99 ship)
- [ ] 所有关键操作有审计记录(billing 窄域 ✅;通用 AuditLog SPEC ✅,实施待 S-AL session)
- [x] AGPL §13 合规可一键自检(`bash deploy/agpl-selfcheck.sh`) —— PR #88 + #90

---

## v0.3 — 运维成熟 + 抗封进化(8-12 周) — **入口就位**(2026-04-28 late-7 wave-2 post-merge)

**目标**: 从"能卖"走到"可长期运营"。健康度仪表盘 + 原生 IP 限制 + 备用通道 + RBAC + 审计日志。

**当前状态**: v0.2 实质完工(差异化 #3 Reality 全链路闭环已前置完成);v0.3 audit-log + RBAC SPEC 双骨架已 ship(PR #101),等用户拍 7 个 TBD(issue #103 #104)后启动 S-AL / S-RB session。

### 必做

1. **Reality 配置审计 + 健康度仪表盘**(2-3 周,差异化 #3)✅ **全链路闭环 5/5 完工(已前置到 v0.2)**
   - [x] R.1 配置审计 core(SNI 冷门度 / ASN 同质性 / 端口非标 / shortId 合规 / connIdle)—— PR #74
   - [x] R.2 CLI + loader + golden fixtures —— PR #75
   - [x] R.3 REST endpoint(`POST /api/reality/audit`,sudo-admin 门控)—— PR #76
   - [x] R.5 OPS-reality-runbook —— PR #82
   - [x] **R.4 dashboard reality module**(管理员审计页消费 R.3 endpoint)—— PR #99 `5adddfe`
   - ⏳ R.4 follow-up: 4 个 component test(issue #102)
   - ⏳ R.5+ 实时监测每节点 SNI 可达性 / 握手成功率 / 历史趋势图(Prometheus + Grafana,留 v0.3 后段)

2. **原生 IP 限制模块**(2 周)✅ **已前置落地**(v0.3 item 提前到 Round 3 opener 完成,差异化 #2 用户可见闭环 + 生产化全套)
   - [x] `hardening/iplimit/` MVP —— PR #24(policy 表 / Xray access 日志 parser / Redis 滚动窗口 / detector / REST / Telegram 告警 / clear-disable endpoint)
   - [x] Review blockers C-1/C-2/M-1/M-2/M-3 修复 —— PR #26
   - [x] Migration safety-net + Alembic stepped-upgrade CI 门禁 —— PR #31
   - [x] 生产化(S-I Codex 完工):runbook + xray 日志样本 + CIDR allowlist + 时区修正 + owned-disable 可见性 —— PR #40/#42/#43/#44/#45
   - ⏳ 真实节点 E2E 验证(留待 S-D 一键部署就位后双向测)
   - ⏳ 小债:Redis SCAN 替代 KEYS / 白名单 UI

3. **备用通道(XHTTP / Hysteria2)**(2-3 周)— **未启**
   - `hardening/fallback/` 支持多协议回切
   - 订阅链接同时下发 Reality + 备用协议
   - 客户端指南 + dashboard 客户端状态面板

4. **审计日志系统**(1 周)— ✅ **SPEC ship,等决策驱动启动**
   - [x] **SPEC-audit-log skeleton ship**(PR #101)
   - ⏳ 等 issue #103 4 TBDs 拍板后启动 S-AL session
   - 备注: 实施先于 RBAC,因为 RBAC 的"细化审计 who+action+target"依赖 audit_log 表 schema(SPEC-rbac 已注明先决)

5. **RBAC + 管理员分层**(2 周)— ✅ **SPEC ship,等决策 + S-AL 完工双先决**
   - [x] **SPEC-rbac skeleton ship**(PR #101)
   - ⏳ 等 issue #104 3 TBDs 拍板 + S-AL 完工后启动 S-RB session
   - `Role` + `Permission` 表
   - 默认角色:sudo / ops / finance / support
   - UI 管理角色 + 权限矩阵
   - 细化审计:记录 "who + action + target"(消费 audit_log 表)

6. **自动化 Upstream 同步**(1 周)— **未启**
   - Codex Automation:每周 `git fetch marzneshin-upstream`,diff changelog,生成报告
   - 冲突预警 + 人工审核后合并

### 验收

- [ ] 健康度仪表盘能在 SNI 被封后 10 分钟内推送告警并推荐替代
- [ ] IP 限制能在用户 3 设备并发时自动断连一个并推送 Telegram 提醒
- [ ] 用户在 Reality 被封的国家自动切到 Hysteria2
- [ ] 管理员可为"财务审计员"角色配置"只读 + 只看付款数据"权限

---

## v1.0 — 发布候选(基于 v0.3 稳定 2 个月后)

**目标**: 产品正式 1.0,开始对外分发。

### 准备工作

- 文档站(MkDocs 或 Docusaurus)
- 多语言用户指南
- 部署场景白皮书(单节点、3 节点、10 节点)
- 性能基准测试(1000 用户压测 + 报告)
- 安全审计(外部团队)
- 升级/迁移脚本(从上游 Marzneshin 迁入我们分支)

---

## 长期方向(2026 下半年 +)

- **向上游贡献 PR**:IP 限制、审计日志、RBAC 等若通用,提回 Marzneshin 上游
- **Kubernetes 支持**:超大规模部署
- **API 生态**:开放 OAuth2 + Webhook,允许第三方 dashboard/客户端
- **企业 SaaS**:向"面板即服务"方向演进(我们托管,客户只填域名和上游)

---

## 路线图调整原则

- 每轮末尾评估当前阶段达成度,未达成就不进下一阶段
- DPI 黑名单变化 / 新漏洞爆发 → 安全任务永远可插队到最高优先级
- 商业 deadline 可驱动某项优先级提升(如营销计划要求 v0.2 提前 2 周)
- 新竞品出现重大创新 → 每 3 轮评估一次是否需要跟进(参考 COMPETITORS.md "追踪坐标")

---
