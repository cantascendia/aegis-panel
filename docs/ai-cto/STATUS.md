# 项目状态(STATUS)

> 最后更新:2026-04-30 late-7 wave-4 (post-issue-102-closure)(issue #102 R.4 follow-up 4 component tests ✅;skills 缺口闭环 PR #111;harness v3.6 同步 PR #115 + drift 收口 #116/#117/#118/#120/#122;Harness 维度 94→97)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 3 mid late-7 wave-4 —— issue #102 收口 + harness v3.6 同步 + drift cleanup(Harness 94→97)**

> 本 wave 仍无新业务功能 ship,**主线是 governance / harness 第三轮收口**。商业化 / 差异化 #3 / 差异化 #4 状态承袭 wave-3 不变(全 5/5 闭环)。本 wave 主要 ship:PR #111 同步 3 个 skill 到 `.claude/skills/`(关闭 Harness ROI 缺口 #1);PR #113 R.4 module 4 component tests(关闭 issue #102,差异化 #3 测试覆盖到 dashboard);PR #114 wave-3 batch refresh;PR #115 sync playbook v3.6(§44 replay + §45 canary + §48 cross-review);PR #116 skills-sync drift checker + SubagentStop 修;PR #117 L-027 → `.agents/rules/sub-agent-worktree.md` + 2 regression evals;PR #118 codex-bridge business path SSOT(`scripts/business-paths.txt`);PR #120 reality-dashboard 空审计 UX 修;PR #122 harness drift cleanup 残留收口。

状态:🟢 v0.2 实质完工,商业化(A.x)5/5 端到端跑通;**差异化 #3 Reality 配置审计 5/5 全闭环**(R.1-R.3 后端 + R.5 OPS-runbook + R.4 dashboard PR #99);差异化 #4(一体化部署)5/5 全 ship;v0.3 audit-log + RBAC SPEC 双骨架已 ship(PR #101),等用户拍 7 个 TBD(issue #103 #104)。各 session 跑独立 worktree(L-018 / 铁规则 #7):

| Session | PR | 状态 |
|---|---|---|
| **S-B 商业化后端**(Claude Code × `aegis-B` worktree) | #46 A.2.1 ✅;#65 A.2.2 ✅;#77 A.5 scheduler ✅;#79 A.3 TRC20 ✅ | **completed**(后端 5/5 全工)|
| **S-F 商业化前端 + Reality 审计前端**(Claude Code) | A.4: #41 skeleton + #49 money-critical 测试 + #86 BRIEF + #87 A.4 flip-on + #89 rename;R.4: **#99 dashboard reality module ship** | **completed**(A.4 admin checkout + R.4 reality dashboard 双交付,差异化 #3 前端闭环;**S-F-2 命名实质合并到 S-F**,同 session 同时承担 admin checkout + reality dashboard 实操证明拆分非必要)|
| **S-D 部署一体化**(Claude Code × `aegis-D` worktree) | #58 OPS-deploy-runbook + #64 D.0 SPEC + #88 agpl-selfcheck.sh + #94 D.4 CF Tunnel + #95 D.1 install.sh + #96 D.5 OPS-deploy-runbook + deploy-smoke CI + #97 D.2 marznode standalone + #98 D.3 Ansible playbook ✅ 全 merged | ✅ **completed**(差异化 #4 一体化部署 5/5 全 ship)|
| **S-R Reality 配置审计**(Claude Code × `aegis-R` worktree) | R.1-R.3 后端 ✅ #74/#75/#76 + R.5 OPS-runbook #82 + **R.4 frontend #99 ship** | ✅ **completed**(差异化 #3 全链路闭环 5/5,R.1-R.3 后端 + R.5 runbook + R.4 frontend) |
| **S-X 前端测试基建**(Claude Code × `aegis-X` worktree) | #57/#59/#63 ✅ merged | **暂停**(基础齐了,X.3+ 增量低优先级) |
| **S-I iplimit 生产化**(Codex × `Marzban-iplimit-production` worktree) | #40/#42/#43/#44/#45 全 ✅ merged | 已完工(归档)|
| **S-O 文档守护**(Claude Code × `aegis-O` worktree,part-time) | 累计 #48/#52/#56/#60/#61/#67/#78/#80/#84/#85/#91/#100/#106/#110 + **本批次 wave-3 batch refresh** | **本次触发**(late-7 wave-3 post-harness-audit batch)|

**Pre-kickoff(待用户决策驱动后启动)**:
- **S-AL** audit-log session: SPEC ✅ ship (PR #101);等 issue #103 4 TBDs 拍板 + CONSTITUTION SEALED 双先决条件
- **S-RB** RBAC session: SPEC ✅ ship (PR #101);等 issue #104 3 TBDs + S-AL 完工双先决条件
- ~~**S-X-2** R.4 follow-up tests~~ ✅ **closed PR #113**(issue #102 4 component tests for reality module 落地,差异化 #3 测试覆盖延伸到 dashboard)
- **S-CI** CI eval-gate workflow: 等 SPEC + 双签(forbidden 路径 `.github/workflows/**`,§32 强制双签);issue 待建

多会话协作索引见 `docs/ai-cto/SESSIONS.md`(本轮新增)。

**差异化 #2 (IP 限制 = Hiddify `shared_limit` 等价物) 已落地**:
- ✅ **IP limiter MVP**(PR #24,`7b12085`)—— `hardening/iplimit/` 数据面 + policy 表 + REST + dashboard UI,按 BRIEF-codex-ip-limiter.md 执行
- ✅ **Review blockers 修复**(PR #26,`b07e18c`)—— C-1(buffer replay → 日志时间戳)+ C-2(unconditional re-enable → 归属表 + data/expire gate)+ M-1 批量 policy resolve + M-2 gRPC 异常记录 + M-3 `SET NX` 原子 dedupe + 覆盖 5 个关键测试
- ✅ **Migration safety-net + Alembic CI 门禁**(PR #31,`3b8cfe4` + `1c652d2`)—— PR #26 mutate 了已 merge 的 `4f7b7c8e9d10` 造成"已部署环境卡死"风险,safety-net 幂等恢复 + `test-alembic-stepped` CI job 防回归

**商业化 MVP (Billing A.x) 数据面 + Admin UI 已落地**:
- ✅ **SPEC billing MVP**(PR #25)—— 5 表骨架 + 状态机 + EPay 对接定义
- ✅ **Billing data models (A.1.1)**(PR #28)—— `ops/billing/db.py` 5 张 `aegis_billing_*` 表 + Alembic
- ✅ **Billing pricing + states (A.1.2)**(PR #29)—— 状态机 + webhook 去重 + 时区感知时间
- ✅ **Billing admin REST (A.1.3)**(PR #30)—— sudo-admin CRUD 接口
- ✅ **Billing admin dashboard (A.1.4.a)**(PR #32)—— 管理员入口
- ✅ **Billing admin channels (A.1.4.b)**(PR #33)—— 码商(EPay)凭据管理页
- ✅ **Billing admin invoices (A.1.4.c)**(PR #35,`a4e0c15`)—— 订单列表(state / user_id 过滤)+ 详情 dialog(summary grid + TRC20 相关字段 + lines + 审计事件)+ apply_manual / cancel 动作面板(note 门控,终态隐藏);新教训:注释内不得写出匹配 `t("...")` 正则的字面 —— drift-gate 会把它抽成 source key

**基础设施沉淀 (Round 3 opener 债)**:
- ✅ **`app/db/extra_models.py` aggregator + 硬规则**(PR #34,`f31db67`)—— 自研 SQLAlchemy model 单点注册,env.py 缩回 1 行 upstream 冲突面;`.agents/rules/python.md` 吸收 L-014(aggregator 强制)+ L-015(Alembic revision 不可 mutate)两条硬规则
- ✅ **Round 2 tail CI 清债**(PR #20/#22/#23 批 1-3)—— UVICORN_HOST 默认 127.0.0.1 / TrustedProxyMiddleware / Chromatic token 处理等
- ✅ **Translations drift gate 换成 diff-based**(PR #27)—— 不再因历史 drift 卡新 PR,只卡"新 PR 增加 drift"(解 L-012)

## 项目画像(一句话)

Marzneshin 硬 fork,面向商业化机场 >200 付费用户 + 多节点,**Round 3 opener 双线同步:差异化 #2 IP 限制 MVP 用户可见闭环 + 商业化 MVP 数据面/Admin UI A.1 全 5 个子 PR 落地**,下一件 A.2 EPay 网关对接 + A.3 TRC20 poller + 真实节点 iplimit E2E 验证。Alembic 不变性 + 自研 model aggregator 两条硬规则沉淀是 Round 3 最高价值 infra 动作。

## 产品完成度

- 上游功能 6/6 保留(面板 / 多节点 / Reality / 订阅 / Telegram / 多语言)
- 自研核心功能 **7/8** 落地(admin 速率限制,SNI 智能选型器,**IP 限制 MVP**,**商业化 5/5 端到端 = 数据面 + Admin UI + EPay 后端 + TRC20 后端 + A.4 admin checkout UI(BRIEF option A 完结)**,**差异化 #3 Reality 配置审计 全链路闭环 = R.1-R.3 后端 + R.5 OPS runbook + R.4 dashboard frontend(PR #99)+ 健康端点 backend + frontend** 算一项产品级核心,**差异化 #4 一体化部署 D.1-D.5 当天 5 PR 并行 ship** 计第 6 件 = `agpl-selfcheck.sh`(#88) + install.sh(#95) + marznode standalone(#97) + Ansible playbook(#98) + CF Tunnel(#94) + OPS-deploy-runbook + deploy-smoke CI(#96)),**+ R.4 Reality dashboard frontend(PR #99)** 计第 7 件,差异化 #3 用户可见闭环最后一公里完工)
- **AGPL-3.0 合规自检工具**(2026-04-28 late-7,PR #88 + #90):`deploy/agpl-selfcheck.sh`(302 LOC bash,**差异化 #4 第一件工具**)+ `NOTICE.md` 声明 fork source URL。AGPL §13 长悬 audit gap 关闭。**差异化 #4(一体化部署 / 运营加固)D.1-D.5 当天 5 PR 并行 ship**:#94 D.4 CF Tunnel + Access scripts(`b00a9cf`)、#95 D.1 install.sh + compose + .env.example + README(`9787bd4`)、#96 D.5 OPS-deploy-runbook + deploy-smoke CI(`3a969a7`)、#97 D.2 marznode standalone node installer(`cfc3b9a`)、#98 D.3 Ansible multi-node playbook(`5f0ca98`),全部 06:03-06:41 UTC 区间 merged。D-017 原序列约束实操证伪 → 修订承认 deploy 工具可独立 ship 不必前后依赖(详见 DECISIONS.md D-017 2026-04-28 修订段)
- **`dashboard/src/modules/billing/admin-checkout/`** 是 A.4 改名后规范路径(PR #89,原 `modules/billing/user/`,改名清理 BRIEF option A 命名一致性)
- **健康度全栈**(2026-04-26 PR #83 backend + 2026-04-28 PR #93 frontend admin page):`/api/aegis/health` public + `/health/extended` sudo(6 子系统并发探针)+ admin dashboard 健康页直接消费 extended endpoint。LB / k8s / Prometheus 接入直接可用
- 自研基础设施 **全部就绪**:
  - ✅ 安全基线(JWT 外置 / CORS 白名单 / bcrypt 固化 / JWT 时效 60min)
  - ✅ Auth 依赖升级(pyjwt 2.12 / pynacl 1.6.2 / cryptography 46.0.7)
  - ✅ 非 auth 依赖升级(aiohttp / starlette / jinja2 / requests / protobuf / python-multipart)
  - ✅ Redis 客户端(可选,默认禁用,fail-loud 模式)
  - ✅ PostgreSQL 16 compose profile(可选,零破坏)
  - ✅ 速率限制(slowapi + Redis 令牌桶,默认禁用)
  - ✅ 测试基础设施(pytest + ruff + pip-audit CI,**171 个通过测试** + 1 个 SQLite skip):
    - Round 1: smoke / P0 security / cache redis / rate limit / compose profiles / migrations(22)
    - Round 2: sni_asn(6) + sni_checks(16) + sni_loaders(10) + sni_selector(9) + crypto(5) + sni_endpoint(10)
    - Round 3 opener: iplimit(~27,含 buffer-replay / 非归属 disable / data gate / 并发 dedupe / clear endpoint)+ billing_states / billing_invoices_admin / billing_channels_admin
    - Dashboard 单测仍为 2 个(`features/support-us/*.test.*`);`SniSuggestDialog` + billing admin 单测留待专项前端 test infra PR
  - ✅ **Alembic CI 门禁两道**:fresh-DB PG16 matrix(PR #4)+ `test-alembic-stepped`(PR #31,阻塞 mutated revision 类 bug)
  - ✅ **自研 model 注册 aggregator**(PR #34):`app/db/extra_models.py` 是唯一注册点,env.py 对 upstream 同步区保持 1 行 diff
  - ✅ 目录骨架(`hardening/` + `deploy/` + `ops/` 各自 README)
  - ✅ **`hardening/sni/`**(Round 2)—— candidate / asn / checks / scoring / loaders / selector + seeds + blacklist + endpoint
  - ✅ **`hardening/iplimit/`**(Round 3)—— policy 表(config / override / disabled_state)+ Xray access 日志 parser(时间戳感知)+ Redis 滚动窗口 + detector + REST + Telegram 告警 + clear-disable endpoint
  - ✅ **`ops/billing/`**(Round 3)—— 5 张 `aegis_billing_*` 表(plans / channels / invoices / invoice_lines / payment_events)+ 状态机 + webhook 去重 + 管理员 REST
  - ✅ **`dashboard/src/modules/nodes/dialogs/sni-suggest/`**(Round 2)+ **`dashboard/src/modules/users/dialogs/iplimit/`**(Round 3)+ **`dashboard/src/modules/billing/`**(Round 3 in-progress)
  - ✅ **`evals/golden-trajectories/` 5 P0**(PR #109,wave-3)— 铁律 #12 可执行,首套 trajectory yaml 落地
  - ✅ **`.claude/agents/`**(PR #108,wave-3)— eval-runner / harness-auditor / vibe-checker 三 Agent 模式起点
  - ✅ **`.claude/skills/` 同步**(PR #108,wave-3)— playbook bulk sync 落本仓库;3 个项目自研 skill(agpl-compliance / reality-config-audit / sni-selector)pending in-flight chore PR
  - ✅ **`.claude/output-styles/` + `.claude/statusline.sh`**(PR #108,wave-3)
  - ✅ **`.claude/commands/` 9 个 cto-* 命令** + 4 个新命令(cto-constitution / cto-eval / cto-harness-audit / cto-vibe-check,PR #107,wave-3)

**项目治理**(wave-3 新增):

- ✅ **`docs/ai-cto/CONSTITUTION.md`**(PR #110,DRAFT 状态)— 5 大领域(架构 / 安全 / 测试 / 部署 / 治理)第一份 draft,等用户 + senior 双签后转 SEALED
- ✅ **`docs/ai-cto/HARNESS-CHANGELOG.md`**(PR #110,倒序记录)— 自 2026-04-28 起所有 harness 改动(`.claude/*` / `.agents/*` / `docs/ai-cto/{CONSTITUTION,STATUS,LESSONS,DECISIONS,SESSIONS,ROADMAP}.md`)必须在此追一行
- ✅ **`/cto-harness-audit` 第二跑验证**:78 → **94**(+16),三大缺口闭环
- 关键缺口(Round 3+):**install.sh + Ansible playbook**(S-D D.1+,部署一体化下一块)/ **Reality CLI + endpoint 端到端 hookup**(S-R R.2-R.3 包装入用户工作流;后端 R.1-R.3 已 ship,缺 deploy / cron 化合入)/ **真实端到端 real-money round-trip**(operator 任务,非 session 任务:¥0.01 EPay + USDT 测试网均需对接外部环境)/ Reality 审计 dashboard 页(R.4,S-F-2)/ IP 限制真实节点 E2E / CF Tunnel 集成 / 审计日志(panel-wide,需 SPEC)/ RBAC(需 SPEC);小债已清零:**SNI rate-limit 回填**(L-010 documented,Linux 复现 ROI 负,先放着)/ ✅ **iplimit 白名单**(`hardening/iplimit/allowlist.py` + db schema + endpoint + task 已用)/ ✅ **iplimit Redis SCAN**(`store.py` 用 `scan_iter`,非 KEYS)/ ✅ **TZ 对齐文档**(OPS-iplimit-runbook §"Timezone validation" 已文档化)/ ✅ **A.4 用户购买 UI**(完结于 PR #87 走 BRIEF option A admin checkout 路径,改名清理在 #89)

## 当前代码质量评分

**7.85 / 10**(R0 5.0 → R1 6.8 → R2 前半 7.1 → R2 v0.2 7.3 → R3 opener 7.6 → R3 mid late-7 7.8 → R3 mid late-7 wave-2 post-merge 7.85 → R3 mid late-7 wave-3 post-harness-audit 7.85 → **R3 mid late-7 wave-4 post-issue-102-closure 7.85**)

**wave-4 维度变化**:产品总分维持 **7.85**(R.4 component tests 是测试覆盖深化,不计新功能);**Harness 维度** 94 → **97**(+3,skills 缺口闭环 + v3.6 同步 + drift 收口);测试维度 7 → **7.5** 信号驱动(R.4 module 4 component tests ship 关闭差异化 #3 dashboard 测试缺口)。

**Harness 维度** 升分 +3 的 concrete delta:
1. ✅ `.claude/skills/` 缺 3 个项目自研 skill 同步(PR #111)→ +2(关闭 wave-3 ROI 缺口 #1)
2. ✅ playbook v3.6 整体同步(PR #115:§44 replay + §45 canary + §48 cross-review;PR #116 skills-sync drift checker;PR #117 L-027 → rule;PR #118 codex-bridge SSOT)→ +1
3. ⚠️ `.github/workflows/eval-gate.yml` 仍缺 → -1(wave-4 残余 ROI Top-1)
4. ⚠️ CONSTITUTION DRAFT → SEALED 仍待双签 → -1(wave-4 残余 ROI Top-2)

**wave-3 历史 delta(承袭)**:
1. ✅ `evals/` 5 P0 trajectory 落地(PR #109)→ +10(铁律 #12 可执行)
2. ✅ `HARNESS-CHANGELOG.md` 创建(PR #110)→ +5
3. ✅ `CONSTITUTION.md` 创建(PR #110,DRAFT)→ +5

**回顾 wave-2 post-merge 升分 +0.05 的 concrete delta(承袭)**:
1. **R.4 Reality dashboard frontend ship**(PR #99) —— 差异化 #3 用户可见闭环最后一公里完工,R.1-R.5 全链路 5/5 闭环
2. **v0.3 audit-log + RBAC SPEC 双骨架 ship**(PR #101) —— v0.3 scope 明确化,issue #103 #104 跟踪 7 个 TBD,等用户决策驱动后启动 S-AL / S-RB session

UX 维度 7 → **8** 信号驱动(wave-2 已计提,wave-3 维持):R.4 dashboard 是差异化 #3 的"用户可见性闭环最后一公里",从此 reality audit 是管理员日常 dashboard 体验的一等公民,不再是 CLI / endpoint hidden capability。

| 维度 | R0 | R1 | R2 v0.2 | R3 opener | R3 mid late-7 | R3 mid late-7 wave-2 | **R3 mid late-7 wave-3** | 变化驱动 |
|---|---|---|---|---|---|---|---|---|
| 架构 | 7 | 7 | 7 | 8 | 8 | 8 | **8** | 保持(aggregator + Alembic 不变性规则保稳)|
| 代码质量 | 6 | 6 | 7 | 7 | 7 | 7 | **7** | 保持(billing / Reality / health 模块均符合 rules)|
| 性能 | 5 | 6 | 6 | 6 | 6 | 6 | **6** | 保持(无性能改动)|
| 安全 | 3 ⚠️ | 8 | 8 | 8 | 8 | 8 | **8** | 保持 |
| 测试 | 1 ⚠️ | 5 | 6 | 7 | 7 | 7 | **7.5** | wave-4 +0.5:R.4 module 4 component tests ship(PR #113),差异化 #3 dashboard 测试覆盖闭环 |
| DX | 6 | 8 | 8 | 8 | 8 | 8 | **8** | 保持 |
| 功能完整性 | 4 | 4 | 5 | 5 | 6 | 7 | **7** | 保持(wave-4 无新功能 ship)|
| UX | 7 | 7 | 7 | 7 | 8 | 8 | **8** | 保持(reality dashboard UX 修 #120 是细化,不升档)|
| **产品总分** | **5.0** | **6.8** | **7.3** | **7.6** | **7.8** | **7.85** | **7.85** | wave-4 测试 +0.5 但产品总分计算方式无新功能未升档;governance 升级算 Harness 维度独立计 |
| 🆕 Harness(独立) | - | - | - | - | - | 78 | **97** | **+3**(wave-3 78→94 + wave-4 94→97):skills 缺口闭环 + v3.6 同步 + drift 收口 |

## 关键决策记录

见 `docs/ai-cto/DECISIONS.md`。Round 1 新增 D-005~D-009,Round 2 尚未新增决策(SPEC-sni-selector 已提 PR #10 合入,走 SPEC-driven 流程无独立决策需要)。

## PR 汇总(累计)

**Round 1**(7 个 PR,全绿):

| PR | 内容 | 状态 | SHA |
|---|---|---|---|
| #1 | 脚手架 + 测试 infra + .gitattributes | ✅ 合并 | `e9b543c` |
| #2 | P0 安全(JWT/CORS/bcrypt/auth 依赖升级) | ✅ 合并 | `8969e58` |
| #3 | 非 auth 依赖升级 | ✅ 合并 | `a3d932c` |
| #4 | PostgreSQL 16 + Redis 7 可选集成 | ✅ 合并 | `2097542` |
| #5 | STATUS 依赖安全基线中间刷新 | ✅ 合并 | `67a8c3a` |
| #6 | 修复 `_testcapi.INT_MAX` | ✅ 合并 | `f5188f2` |
| #7 | Admin 登录速率限制 | ✅ 合并 | `482d2cc` |

**Round 1 tail + Round 2**(11 个 PR):

| PR | 内容 | 状态 | SHA |
|---|---|---|---|
| #8 | R1 记忆刷新(STATUS / DECISIONS / LESSONS) | ✅ 合并 | `940622a` |
| #9 | R1 tail(LESSONS → rules + [tool.black] 清理) | ✅ 合并 | `246500e` |
| #10 | SPEC-sni-selector.md(R2 v0.2 opener) | ✅ 合并 | `ef620aa` |
| #11 | cryptography 46 迁移 | ✅ 合并 | `6e589ba` |
| #12 | L-009 教训(API read vs write-side trap) | ✅ 合并 | `94b5baf` |
| #13 | **SNI 选型器 core + docs**(差异化 #1 MVP) | ✅ 合并 | `6ade9bf` |
| #14 | `app/utils/crypto.py` 128 行单测 | ✅ 合并 | `efcfd9e` |
| #15 | Round 2 mid-point STATUS refresh | ✅ 合并 | `bd81a54` |
| #16 | **SNI dashboard 端点**(差异化 #1 REST 层) | ✅ 合并 | `c75359e` |
| #17 | R2 endpoint wrap STATUS + L-010 / L-011 | ✅ 合并 | `672e67d` |
| #18 | **SNI dashboard 前端集成**(差异化 #1 UI 层,闭环完成) | ✅ 合并 | `efabf43` |

**Round 2 tail + Round 3 opener**(16 个 PR):

| PR | 内容 | 状态 | SHA |
|---|---|---|---|
| #19 | R2 SNI loop closed STATUS refresh | ✅ 合并 | `4763743` |
| #20 | CI 清债 batch 1(UVICORN_HOST / Chromatic token) | ✅ 合并 | `ddd1ea7` |
| #21 | BRIEF-codex-ip-limiter.md(差异化 #2 委派骨架) | ✅ 合并 | `bc6935a` |
| #22 | CI 清债 batch 2 | ✅ 合并 | `bf6e562` |
| #23 | CI 清债 batch 3 | ✅ 合并 | `0208b4f` |
| #24 | **IP limiter MVP**(差异化 #2) | ✅ 合并 | `7b12085` |
| #25 | SPEC-billing.md(商业化 MVP opener) | ✅ 合并 | `8e305b4` |
| #26 | **iplimit review blockers 修复**(C-1/2 + M-1/2/3/6) | ✅ 合并 | `b07e18c` |
| #27 | Translations drift gate → diff-based(解 L-012) | ✅ 合并 | `67a8c3a` |
| #28 | **Billing data models (A.1.1)** | ✅ 合并 | `b3cd98d` |
| #29 | **Billing pricing + states (A.1.2)** | ✅ 合并 | `7a23ac0` |
| #30 | **Billing admin REST (A.1.3)** | ✅ 合并 | `5b9170a` |
| #31 | **iplimit safety-net migration + alembic CI 门禁** | ✅ 合并 | `3b8cfe4` / `1c652d2` |
| #32 | **Billing admin dashboard (A.1.4.a)** | ✅ 合并 | `6b8149d` |
| #33 | **Billing admin channels (A.1.4.b)** | ✅ 合并 | `a808e11` |
| #34 | **extra_models.py aggregator + 硬规则 L-014/15** | ✅ 合并 | `f31db67` |
| #35 | **Billing admin invoices (A.1.4.c)**(订单列表 + 详情 dialog + 动作面板) | ✅ 合并 | `a4e0c15` |

**Round 3 mid(多会话并行期)**:

| PR | 内容 | 状态 | Session | SHA |
|---|---|---|---|---|
| #37 | STATUS 底半部刷新 | (open) | - | - |
| #38 | SPEC-billing-a2-a3.md(A.2/A.3 详细 spec) | ✅ 合并 | S-B kickoff | `0a4aa78` |
| #39 | BRIEF-codex-iplimit-production.md(Codex 委派) | ✅ 合并 | S-I kickoff | `2fba986` |
| #40-#45 | iplimit 生产化 6 条(runbook / 日志样本 / CIDR allowlist / 时区 / scan 重构 / owned-disable banner) | ✅ 全合 | **S-I** Codex 全套完工 | - |
| #41 | **A.4 用户购买 UI skeleton**(flag-gated OFF;fixtures + hooks + 7 组件 + 2 routes + i18n)| ✅ 合并 | **S-F** | `a397914` |
| #46 | **Billing A.2.1 provider abstraction + EPay adapter** | ✅ 合并 | **S-B** | `46b0296` |
| #48 | **协作 kit**(SESSIONS.md + SPEC-{deploy,reality-audit,dashboard-tests} 骨架 + i18n-extractor rule + WIP-billing-split)| ✅ 合并 | **S-O**(S-F 切出)| `4b46e50` |
| #49 | **A.4 money-critical 组件单测**(CartSummary + PlanCard)| ✅ 合并 | **S-F** | `0c5beb3` |
| #52 | **worktree 隔离铁规则 + L-018**(SESSIONS.md 铁规则 #7)| ✅ 合并 | **S-F/S-O** | `56e1b06` |
| #54 | **tools/setup-session-worktrees.sh**(一键建 aegis-{B,D,R,X} worktree;SESSIONS.md 铁规则 #7 改成指向脚本)| ✅ 合并 | **session 0** | `747d5a4` |
| #56 | **S-O round-3-mid-late2 refresh**(第一次正式 S-O 触发:STATUS/SESSIONS/DECISIONS/LESSONS/ROADMAP + python.md slowapi async 硬规则 + D-011)| ✅ 合并 | **S-O** | `a9c9ccb` |
| #57 | **S-X X.1**(dashboard unit-test watch-mode 修复 + pnpm 统一)| ✅ 合并 | **S-X** | `722d29c` |
| #58 | **S-D OPS-deploy-runbook 骨架**(第一次 S-D 正式交付)| ✅ 合并 | **S-D** | `8a72301` |
| #59 | **S-X X.2**(test-utils/render helpers + date-range-picker / usePolling 单测)| ✅ 合并 | **S-X** | `a0692bf` |
| #60 | **AUDIT.md 进度 overlay**(fork-time 基线 + Round 3 mid 状态桥梁;不动原 🔴/🟠 finding)| ✅ 合并 | **S-O** | `009e757` |
| #61 | STATUS late-3 micro-refresh | ✅ 合并 | **S-O** | `149e0e2` |
| #62 | tools/setup-session-worktrees 扩到 S-O + S-F | ✅ 合并 | session 0 | `9195737` |
| #63 | **S-X X.3** dashboard coverage 非阻塞 + test-utils README | ✅ 合并 | **S-X** | `91547df` |
| #64 | **S-D D.0** SPEC-deploy.md flesh-out(compass 默认值矩阵 / 生产 compose 9 维表 / CF Tunnel 最小权限)| ✅ 合并 | **S-D** | `6c33641` |
| #65 | **S-B A.2.2** billing cart checkout + EPay webhook + session 0 cross-review 修(X-Forwarded-For 欺骗 / `datetime.utcnow()` × 3 / disabled-channel 410)| ✅ 合并 | **S-B + session 0** | `84ec4e0` |
| #66 | **OPS-sni-runbook** 落地(SPEC-sni-selector follow-up #3 完成,差异化 #1 SNI 闭环最后一块)| ✅ 合并 | session 0 | `b03ccc0` |
| #67 | round-3 mid late-4 micro-refresh(STATUS / LESSONS L-019/20/21 / DECISIONS D-012 — 反代信任 per-feature CIDR 设计模式锁定)| ✅ 合并 | **S-O** | `30670df` |
| #68 | `datetime.utcnow()` 自有目录 sweep(`ops/billing/{db,states}.py` 6 处 → 共享 `_now_utc_naive` helper)| ✅ 合并 | session 0 | `42eb68f` |
| #69 | `v2share` beta 评估结案(D-013 + `RESEARCH-v2share-evaluation.md`;keep + vendor hedge plan,2026-10-26 复评)| ✅ 合并 | session 0 | `c831150` |
| #70 | `datetime.utcnow()` upstream `app/` sweep(26 callsites 跨 10 文件 + 1 `utcfromtimestamp` → `app/utils/_aegis_clocks.now_utc_naive`)| ✅ 合并 | session 0 | `f4e73cd` |

**Round 3 mid late-6 wave-1 + wave-2 + late-7 wave**(13 个 PR):

| PR | 内容 | 状态 | Session | SHA |
|---|---|---|---|---|
| #74 | R.1 Reality 配置审计 core(差异化 #3) | ✅ 合并 | session 0 | - |
| #75 | R.2 Reality CLI + loader + golden fixtures | ✅ 合并 | session 0 | - |
| #76 | R.3 Reality REST endpoint(`POST /api/reality/audit`) | ✅ 合并 | session 0 | - |
| #77 | A.5 计费 scheduler(reap_expired + apply_paid + lifespan) | ✅ 合并 | session 0 | - |
| #79 | **A.3 TRC20 直收支付通道**(5 模块 + memo+exact-amount 匹配 + Tronscan poll)| ✅ 合并 | session 0 | - |
| #81 | OPS-trc20-runbook(521 行,closes A.3 五段流程) | ✅ 合并 | session 0 | - |
| #82 | OPS-reality-runbook(383 行,closes 差异化 #3 五段流程) | ✅ 合并 | session 0 | - |
| #83 | 健康端点 backend(`/api/aegis/health` public + `/health/extended` sudo)| ✅ 合并 | session 0 | `189f892` |
| **#86** | **docs(ai-cto): BRIEF — A.4 用户购买流程被缺失 user web auth 阻塞**(决策文档:走 admin checkout 路径) | ✅ 合并 | **S-F** | `f7b58c3` |
| **#87** | **feat(dashboard): A.4 flip-on as admin checkout**(BRIEF option A — A.4 商业化前端完结) | ✅ 合并 | **S-F** | `34681f2` |
| **#88** | **feat(deploy): agpl-selfcheck.sh**(AGPL §13 合规自检,302 LOC bash,**差异化 #4 第一件工具**) | ✅ 合并 | **S-D** | `9d0ff76` |
| **#89** | **chore(dashboard): rename modules/billing/user → admin-checkout**(BRIEF option A 命名清理) | ✅ 合并 | **S-F** | `27529e2` |
| **#90** | **docs(notice): aegis-panel fork source URL 声明**(closes #88 surfaced 的 AGPL §13 audit gap) | ✅ 合并 | **S-D** | `a1fb7f6` |
| **#91** | docs(ai-cto): STATUS late-7 wave drive-by refresh(单文件 STATUS,留给 batch S-O 整合) | ✅ 合并 | **S-O drive-by** | `a548751` |
| **#93** | **feat(dashboard): admin health dashboard page**(消费 `/api/aegis/health/extended`,健康全栈闭环) | ✅ 合并 | session 0 / 健康全栈 | `8ac2ff7` |
| **#94** | **feat(deploy): D.4 — Cloudflare Tunnel + Access scripts**(差异化 #4 工具 #2)| ✅ 合并 | **S-D** | `b00a9cf` |
| **#95** | **feat(deploy): D.1 — install.sh + compose + .env.example + README**(差异化 #4 工具 #3,单节点一键)| ✅ 合并 | **S-D** | `9787bd4` |
| **#96** | **feat(deploy): D.5 — OPS-deploy-runbook + deploy-smoke CI**(差异化 #4 工具 #6,五段流程闭环)| ✅ 合并 | **S-D** | `3a969a7` |
| **#97** | **feat(deploy): D.2 — marznode standalone node installer**(差异化 #4 工具 #4)| ✅ 合并 | **S-D** | `cfc3b9a` |
| **#98** | **feat(deploy): D.3 — Ansible multi-node playbook**(差异化 #4 工具 #5,多节点部署)| ✅ 合并 | **S-D** | `5f0ca98` |
| **#100** | **docs(ai-cto): late-7 wave batch S-O refresh — STATUS 结构压缩 + LESSONS L-025 + DECISIONS D-016/D-017 + ROADMAP/SESSIONS 全口径同步**(上次 batch S-O)| ✅ 合并 | **S-O batch** | `e1dcfb7` |

**Round 3 mid late-7 wave-2 post-merge**(3 个 PR + 3 issue):

| PR | 内容 | 状态 | Session | SHA |
|---|---|---|---|---|
| **#99** | **feat(dashboard): R.4 — Reality audit page**(差异化 #3 用户可见闭环最后一公里;消费 R.3 endpoint,管理员 dashboard reality module)| ✅ 合并 | **S-F**(实质合并 S-F-2 命名) | `5adddfe` |
| **#101** | **docs(ai-cto): SPEC-audit-log + SPEC-rbac skeletons**(v0.3 scope SPEC 双骨架;7 个 TBD 留 issue #103 #104 跟踪)| ✅ 合并 | session 0 | `349db93` |
| **#106** | **docs(ai-cto): late-7 wave-2 post-merge batch — R.4 + SPEC #101 + tracking issues**(上一个 batch S-O)| ✅ 合并 | **S-O batch** | `c168520` |

**Round 3 mid late-7 wave-3 post-harness-audit**(5 个 PR + 本 batch):

| PR | 内容 | 状态 | Session | SHA |
|---|---|---|---|---|
| **#105** | **chore(docs): fix handbook path in CLAUDE.md (ai-guidebook → ai-playbook)**(单字符修复,跨机器手册路径) | ✅ 合并 | session 0 | `bc427c9` |
| **#107** | **chore(commands): sync cto-* commands from playbook**(§33/§34/§35/§37 同步 + cto-spec 三段式升级)| ✅ 合并 | session 0 | `2782642` |
| **#108** | **chore(harness): bulk sync from playbook**(`.claude/agents/` + `.claude/skills/` + `.claude/output-styles/` + `.claude/statusline.sh` + cto-image / cto-link 命令)| ✅ 合并 | session 0 | `fb4e1a2` |
| **#109** | **chore(evals): init evals/ + 5 P0 trajectories**(铁律 #12 可执行,首套 trajectory yaml)| ✅ 合并 | session 0 | `06db847` |
| **#110** | **docs(ai-cto): init CONSTITUTION + HARNESS-CHANGELOG**(§37 + §34 audit follow-up,DRAFT 状态)| ✅ 合并 | session 0 | `5e718d8` |
| **#114** | **docs(ai-cto): late-7 wave-3 S-O batch — capture harness 78→94 + 9 PR + 3 issue closure** | ✅ 合并 | **S-O batch** | `c5d16c1` |

**Round 3 mid late-7 wave-4 post-issue-102-closure**(8 个 PR + 本 PR):

| PR | 内容 | 状态 | Session | SHA |
|---|---|---|---|---|
| **#111** | **chore(skills): sync agpl-compliance + reality-config-audit + sni-selector to .claude/skills/**(关闭 Harness wave-3 ROI 缺口 #1)| ✅ 合并 | session 0 | `f39fd59` |
| **#113** | **test(dashboard): R.4 follow-up — 4 component tests for reality module**(关闭 issue #102,差异化 #3 dashboard 测试闭环)| ✅ 合并 | **S-X-2 临时 worktree** | `0cce4ba` |
| **#115** | **chore(harness): sync playbook v3.6**(§44 replay + §45 canary + §48 cross-review)| ✅ 合并 | session 0 | `9bf3e1b` |
| **#116** | **chore(harness): add skills-sync drift checker + fix SubagentStop STATUS write** | ✅ 合并 | session 0 | `e572ba3` |
| **#117** | **docs(governance): L-027 → .agents/rules/sub-agent-worktree.md + 2 regression evals**(D-018 候选升级为硬规则)| ✅ 合并 | session 0 | `3fa8faf` |
| **#118** | **chore(codex-bridge): fix business path filter — use SSOT scripts/business-paths.txt**(v3.6.1 教训:hardcoded 业务路径在 dashboard/src/ silent skip)| ✅ 合并 | session 0 | `8909101` |
| **#120** | **fix(reality-dashboard): empty audit shows dash, not worst_score=100**(UX 细化)| ✅ 合并 | session 0 | `31508b8` |
| **#122** | **chore(harness): drift cleanup post v3.6 sync**(.agents/skills/ 双源清理 + cto-relink-all 补全 + cto-audit §1-§28→§1-§42 + scheduled_tasks.lock gitignore)| (open) | session 0 | - |
| **本 PR(late-7 wave-4 batch)** | docs(ai-cto): late-7 wave-4 S-O batch — STATUS 与 8 PR + issue #102 closure + Harness 94→97 对齐 | (本 PR) | **S-O batch** | - |

**Tracking issues**(待用户/CTO 决策驱动):
- ~~**issue #102**~~ ✅ **closed by PR #113**(R.4 follow-up 4 component tests)
- **issue #103** `spec(audit-log): finalize 4 TBDs before opening S-AL session` — 等用户拍 4 TBDs
- **issue #104** `spec(rbac): finalize 3 TBDs before opening S-RB session (depends on audit-log)` — 等用户拍 3 TBDs + 等 #103 ship

## 已部署配置文件

Round 0 列表的全部 + Round 1 新增:
- ✅ `.gitattributes`(LF 规范化)
- ✅ `pyproject.toml` 增加 `[tool.ruff]` + `[tool.pytest.ini_options]` + `[tool.coverage]`
- ✅ `requirements-dev.txt`(ruff / pytest / pytest-alembic / pip-audit)
- ✅ `.github/workflows/api-ci.yml`(lint + test + security 三 job)
- ✅ `docs/ai-cto/SPEC-postgres-redis.md`(Round 1 唯一 spec,模板参考)
- ✅ `tests/conftest.py`(fixture 契约骨架)+ 6 个测试文件
- ✅ `hardening/panel/{__init__,middleware,rate_limit}.py`(PR #7 落地)
- ✅ `docs/ai-cto/LESSONS.md`(Round 1 CI / 工具链经验沉淀)

## 未解决问题 / Round 2 后半待做

- **差异化核心**:
  - ✅ SNI 智能选型器 MVP(差异化 #1 CLI 层,PR #13)
  - ✅ SNI dashboard REST 端点(差异化 #1 API 层,PR #16)
  - ✅ SNI dashboard 前端集成(差异化 #1 UI 层,PR #18)→ **用户可见闭环完成**
  - ⏳ SNI rate-limit 回填(slowapi async-def 兼容方案,LESSONS.md L-010)
  - ✅ SNI runbook(`docs/ai-cto/OPS-sni-runbook.md`,PR #66) → 差异化 #1 全链路闭环
  - ✅ **Reality 配置审计 全链路闭环**(差异化 #3): R.1-R.3 后端(PR #74-#76)+ R.5 OPS-runbook(PR #82)+ **R.4 dashboard frontend(PR #99)** → **用户可见闭环完成 5/5**
  - ⏳ R.5+ Reality 实时监测(差异化 #3 v0.3 后段,Prometheus + Grafana 长期趋势)
  - ⏳ R.4 follow-up tests(issue #102 跟踪,4 个 component test)
- **商业化基础**:
  - ✅ 计费系统 MVP A.1-A.5 全 5/5(数据面 + Admin UI + EPay + TRC20 + scheduler + admin checkout)
  - ✅ **审计日志 SPEC 骨架**(PR #101) — 4 TBDs 待用户拍板(issue #103);S-AL session 等决策 + CONSTITUTION SEALED 双先决
  - ⏳ 告警系统(超额 / 临期 / 异常登录)
  - ✅ **RBAC SPEC 骨架**(PR #101,v0.3)— 3 TBDs 待用户拍板(issue #104);S-RB session 等决策 + S-AL 完工先决
- **Harness / 治理**(wave-3 新增):
  - ⏳ **CONSTITUTION DRAFT → SEALED**(PR #110 落 DRAFT,等用户 + senior 双签)
  - ⏳ **`.github/workflows/eval-gate.yml` CI 自动调度**(forbidden 路径 `.github/workflows/**`,§32 强制 SPEC + 双签)— 待开 SPEC + 双签
  - ⏳ **R.4 4 组件单测**(issue #102 open,**in-flight 临时 worktree test PR 并行中**)
  - ⏳ **`.claude/skills/` 缺 3 个项目自研 skill**(agpl-compliance / reality-config-audit / sni-selector)— in-flight chore PR
- **部署**:
  - ✅ `deploy/install.sh` 一键单节点(PR #95)
  - ✅ `deploy/cloudflare/` CF Tunnel 自动化(PR #94)
  - ✅ Ansible 多节点 playbook(PR #98)
- **Round 1 遗留小事**:
  - `UVICORN_HOST` 默认 `0.0.0.0` → `127.0.0.1`(CLAUDE.md 铁律要求,需带 deprecation)
  - ~~`pyproject.toml` 的 `[tool.black]` 块清理~~ ✅ 已合 PR #9
  - ~~CI 加 PostgreSQL matrix~~ ✅ 已合(`test-postgres` + `test-alembic-stepped` 两 job)
  - ~~TrustedProxyMiddleware (panel-wide)~~ ❌ 撤销:由 D-012 改为 per-feature `*_TRUSTED_PROXIES` env;billing webhook 已用此模式(PR #65)
  - ~~cryptography 46 的 x509 `not_valid_before_utc` 迁移~~ ✅ 已合 PR #11(read-side 用 `_utc`,builder setter 不变,L-009)
  - ~~`v2share==0.1.0b31` beta 替代评估~~ ✅ 已结案 D-013 + `RESEARCH-v2share-evaluation.md`(保留 + vendor 备胎规划,2026-10-26 日历复评)
  - ~~`datetime.utcnow()` 全 app 迁移~~ ✅ **完工**:PR #65(billing webhook 3 处)+ PR #68(`ops/billing/{db,states}.py` 6 处)+ PR #70(upstream `app/*` 26 处 + 1 `utcfromtimestamp`)。统一收口到 `app/utils/_aegis_clocks.now_utc_naive`(fork-local helper,upstream 适配后即删)

## 下一步推进(wave-3 后)

- **operator 任务**(非 session 任务,需用户外部操作):real-money round-trip(¥0.01 EPay + USDT 测试网均需对接外部环境)
- **决策驱动**(等用户拍 TBD,session 才能 kickoff):
  - issue #102 — R.4 follow-up tests 已派遣并行 in-flight test PR
  - issue #103 — audit-log 4 TBDs(等用户)
  - issue #104 — RBAC 3 TBDs(等用户)
- **SPEC 待开**:
  - panel-wide 审计日志(issue #103 4 TBDs 拍板后)
  - RBAC(issue #104 3 TBDs 拍板 + S-AL ship 后)
  - XHTTP / Hysteria2 备用通道(差异化扩展,scope TBD)
  - `.github/workflows/eval-gate.yml` CI eval-runner 自动调度(forbidden 路径,§32 强制双签)
- **Harness 残余 ROI Top-2**(97 → 99+):
  1. ~~`.claude/skills/` 缺 3 个~~ ✅ **closed PR #111**(2026-04-30)
  2. `.github/workflows/eval-gate.yml` CI 自动调度缺 → 待 SPEC + 双签
  3. CONSTITUTION DRAFT → SEALED 等用户决策
- **aegis-O worktree 严重过期**(停留在 PR #61 / `149e0e2`,落后 main 50+ commits + 大量脏文件):下次 S-O session 启动前需重建 worktree(`git worktree remove` + 重新 add)

## 竞品关键发现

不变 —— 见 `docs/ai-cto/COMPETITORS.md`。Round 1 未做竞品跟踪刷新,下次 STATUS 更新(Round 2 末)做。

## Upstream sync 状态(quarterly)

最新报告:[`UPSTREAM-SYNC-REPORT-2026-04-26.md`](./UPSTREAM-SYNC-REPORT-2026-04-26.md)。**核心结论**:Marzneshin upstream 自 fork 后 6 个月只 2 个 commit,实质 dormant;sync 风险 ≈ 0,我们已是事实独立项目。下次 sync 抓取:**2026-07-26**(每季度)。

## 🔀 分支状态

- `main` — PR #1~#14 全部合入(SHA `94b5baf`)
- **Stale 远端分支**(待授权删):
  - `origin/fix/marznode-testcapi-import` — 内容已作为 PR #6 合入,base 旧于 PR #7 rate-limit,merge 会删除速率限制配置
  - `origin/chore/deps-audit-2026-04` — 3 个 deps 升级已与 main 一致(cryptography 46 / fastapi 0.121 / starlette 0.49),merge 会删除 main 上 800+ 行自研代码
  - 建议:用户运行 `git push origin --delete fix/marznode-testcapi-import chore/deps-audit-2026-04` 或在 GitHub UI 删
- 下一个建议分支:取决于用户下一步选择(Round 2 后半 scope:计费 MVP / SNI rate-limit 回填 / CI infra 清债)

## 📅 最后同步确认

**Round 3 mid late-7 wave-4 post-issue-102-closure batch S-O refresh**(2026-04-30,本 PR):

- **本批次触发**:上一个 batch (PR #114, commit `c5d16c1`) 后又 ship 8 PR(#111/#113/#115/#116/#117/#118/#120)+ 1 PR open(#122 harness drift cleanup)+ issue #102 closed(PR #113)+ Harness 94→97(skills 缺口闭环 + v3.6 同步 + drift 收口),STATUS 不能 lag → S-O 立即批刷
- **本批次更新动作**:metadata 时间戳 → 2026-04-30 late-7 wave-4 (post-issue-102-closure);Session table → S-X-2 标 closed by PR #113;tracking issues → #102 closed;PR 累计表新增 wave-4 段(#111/#113/#115/#116/#117/#118/#120/#122 + 本 PR);Harness 维度 94 → **97**(+3,skills #111 + v3.6 同步);测试维度 7 → **7.5**(R.4 dashboard 测试覆盖);"下一步推进" Harness ROI Top-3 → Top-2(skills 已闭环);记录 aegis-O worktree 严重过期问题
- **本批次零代码改动 + 零 SPEC 改动 + 不动 .claude/* / .agents/* / DECISIONS / ROADMAP**

---

**Round 3 mid late-7 wave-3 post-harness-audit batch S-O refresh**(2026-04-29,PR #114,保留以示阶段切换):

- **本批次触发**:上一个 batch (PR #106, commit `c168520`) 后又 ship 5 PR(#105/#107/#108/#109/#110)+ 3 issue(#102/#103/#104)+ harness audit 第二跑验证 78→94,STATUS / SESSIONS / LESSONS / HARNESS-CHANGELOG 不能 lag → S-O 立即批刷
- **本批次更新动作**:metadata 时间戳 → 2026-04-29 late-7 wave-3 (post-harness-audit);Session table → **S-O 累计 PR 表 +#106/#110;pre-kickoff 行 S-AL/S-RB 加 CONSTITUTION SEALED 先决条件 + S-X-2 标 in-flight + 新增 S-CI**;产品总分维持 **7.85**(无新功能 ship);新增 **Harness 维度** 78 → **94**(+16);PR 累计表新增 wave-3 段(#105/#107/#108/#109/#110 + 本 PR);"项目治理" 新段(CONSTITUTION + HARNESS-CHANGELOG + harness audit 78→94);"下一步推进" 段补充 operator / 决策驱动 / SPEC 待开 / Harness 残余 ROI Top-3
- **本批次新增 LESSONS L-027**(sub-agent 临时 worktree 并行模式经 7 波验证稳定,从 L-026 候选升级为硬规则)
- **HARNESS-CHANGELOG 新加 entry**(2026-04-29 re-audit 78→94,顶部倒序)
- **DECISIONS 不动**(本 batch 无新决策;D-018 sub-agent worktree 硬规则候选可能在下次 batch 立)
- **ROADMAP 不动**(本 batch 无重大里程碑;v0.2 已在 PR #106 标完成)
- 本批次只动 docs(STATUS / SESSIONS / LESSONS / HARNESS-CHANGELOG),零代码改动 + 零 SPEC 改动 + 不动 .claude/* / .agents/* / DECISIONS / ROADMAP

---

**Round 3 mid late-7 wave-2 post-merge batch S-O refresh**(2026-04-28,上一个 batch PR #106,保留以示阶段切换):

- **本批次触发**:上一个 batch (PR #100, commit `e1dcfb7`) 后又 ship 了 PR #99 R.4 + PR #101 SPEC 双骨架,STATUS 不能 lag → S-O 立即批刷
- **本批次更新动作**:metadata 时间戳 → 2026-04-28 late-7 wave-2 (post-merge);Session table → **S-F R.4 双交付完结 + S-F-2 实质合并到 S-F 备注 + S-R completed(R.1-R.5 全闭环)+ pre-kickoff 行 S-AL/S-RB/S-X-2**;自研核心 6/8 → **7/8**(R.4 dashboard frontend 计第 7 件);代码质量 7.8 → **7.85**(+0.05,2 项 delta:R.4 ship + SPEC 双骨架 ship);PR 累计表新增 wave-2 段(#99 / #101 / 本 PR)+ tracking issues 段(#102/#103/#104)
- **本批次新增 LESSONS L-026**(sub-agent 并行 + 临时 worktree 让 1 session 触发 6 PR + 3 issue 自动收口)
- **DECISIONS 不动**(D-016 / D-017 在上一个 batch PR #100 已加,本 batch 无新决策)
- 本批次只动 docs(STATUS / LESSONS / ROADMAP / SESSIONS),零代码改动 + 零 SPEC 改动,L-022 三条件全不满足 = 不动 upstream 文件

---

**Round 3 mid late-7 batch S-O refresh + cross-review 修补**(2026-04-28,上一个 PR #100 的批次,保留以示阶段切换):

- **STATUS 结构压缩**:从 7 个 nested late-N wave block 收口到本节单段历史索引(下方),+ 顶部 wave-7 batch 摘要
- 本批次更新动作:metadata 时间戳 → 2026-04-28;Session table → S-F completed / S-D ✅ completed(差异化 #4 5/5)/ S-R in-progress(R.4 sibling)/ S-X 暂停;自研核心 5/8 → 6/8;代码质量 7.6 → 7.8(+0.2);新 LESSONS L-025;新 DECISIONS D-016 / D-017(D-017 含 2026-04-28 修订段)
- **当天并行 ship 实绩(2026-04-28 06:03-06:41 UTC)**:#94 D.4 CF Tunnel `b00a9cf` / #95 D.1 install.sh `9787bd4` / #96 D.5 OPS-deploy-runbook + deploy-smoke CI `3a969a7` / #97 D.2 marznode standalone `cfc3b9a` / #98 D.3 Ansible `5f0ca98`

---

### 历史 wave 索引(压缩)

| wave | 日期 | 主线 | 关键 PR / 决策 |
|---|---|---|---|
| Round 2 v0.2 close | 2026-04-22 | 差异化 #1 SNI 用户可见闭环 | #1-#18 累计;L-010/L-011/L-012/L-013 |
| Round 3 mid late-2 | 2026-04-23 | S-O 第一次正式触发 + 多会话 kit | #41 A.4 skeleton / #46 A.2.1 / #48 SESSIONS.md / #49 / #52 worktree 隔离铁规则 + L-018 / #54 setup script |
| Round 3 mid late-3 | 2026-04-23 | S-X / S-D / 测试基建 | #57 X.1 / #58 OPS-deploy-runbook 骨架 / #59 X.2 test-utils |
| Round 3 mid late-4 | 2026-04-26 | A.2.2 webhook + 反代信任设计模式 | #64 D.0 SPEC-deploy / #65 A.2.2 + 反代信任修(L-019/20/21 + D-012) / #66 OPS-sni-runbook(差异化 #1 五段流程 close)|
| Round 3 mid late-5 | 2026-04-26 | Round 1 leftover 全清零 + 上游 app/ datetime sweep | #67 / #68 billing datetime / #69 v2share D-013 / #70 upstream app/ sweep + L-022 |
| Round 3 mid late-6 wave-1 | 2026-04-26 | 差异化 #3 Reality 后端闭环 + A.x 后端补完 | #72/#73 季度 upstream/COMPETITORS / #74 R.1 / #75 R.2 / #76 R.3 / #77 A.5 scheduler / #79 A.3 TRC20(L-023/L-024 + D-014/D-015)|
| Round 3 mid late-6 wave-2 | 2026-04-26 | Round 3 mid 后端实质收口 | #81 OPS-trc20-runbook(A.3 五段 close) / #82 OPS-reality-runbook(差异化 #3 五段 close) / #83 健康端点 backend |
| Round 3 mid late-6 wave-3 | 2026-04-26 | 小账盘点(无新 PR) | iplimit 白名单 / Redis SCAN / TZ 文档**全部已完工**;唯一余债 = SNI rate-limit Linux 复现(L-010 documented)|
| Round 3 mid late-7 wave | 2026-04-28 | A.4 完结 + AGPL §13 合规自检 + 改名清理 + **差异化 #4 一体化部署 D.1-D.5 当天 5 PR 并行 ship** | #86 BRIEF / #87 A.4 flip-on / #88 agpl-selfcheck.sh(差异化 #4 #1) / #89 rename / #90 NOTICE / #91 STATUS drive-by / #93 admin health dashboard 页 / **#94 D.4 CF Tunnel / #95 D.1 install.sh / #96 D.5 OPS-deploy-runbook + deploy-smoke CI / #97 D.2 marznode standalone / #98 D.3 Ansible playbook** |
| Round 3 mid late-7 batch | 2026-04-28 | **S-O 正式 batch refresh** | PR #100 全 docs 同步 + L-025 + D-016/D-017 |
| Round 3 mid late-7 wave-2 post-merge | 2026-04-28 | R.4 + SPEC 双骨架 + tracking issues 收口 | #99 R.4 dashboard reality module(差异化 #3 全链路闭环)+ #101 SPEC-audit-log + SPEC-rbac skeletons + tracking issues #102/#103/#104 + PR #106 (S-O batch wave-2) |
| Round 3 mid late-7 wave-3 post-harness-audit | 2026-04-29 | **Harness 健康分 78→94 + 项目治理 3 大文件就位** | #105 handbook 路径修复 + #107 cto-* commands sync + #108 bulk harness sync + #109 evals/ 5 P0 init + #110 CONSTITUTION + HARNESS-CHANGELOG init + #114 (S-O batch wave-3 + L-027) |
| **Round 3 mid late-7 wave-4 post-issue-102-closure**(本 PR) | 2026-04-30 | **issue #102 收口 + harness v3.6 同步 + drift cleanup(Harness 94→97)** | **#111 skills sync(关闭 ROI #1)** + **#113 R.4 4 component tests(关闭 issue #102)** + **#115 playbook v3.6 sync** + **#116 skills-sync drift checker** + **#117 L-027 → rule** + **#118 codex-bridge SSOT** + **#120 reality-dashboard 空审计 UX** + **#122 harness drift cleanup** + 本 PR (S-O batch wave-4) |

详细历史信息保留在 git log + 各 PR description + LESSONS/DECISIONS 条目中,STATUS 不再展开。

---

**Round 2 v0.2 差异化 #1 用户可见闭环**(2026-04-22 历史 milestone,保留以示阶段切换):
- **18 个 PR 合入**(#1~#18 全绿或核心三门禁全绿)
- **78 个后端通过测试** + 1 skip;dashboard 2 个(未扩)
- SNI 三层全通:CLI(PR #13)→ REST(PR #16)→ UI(PR #18)
- `apply_panel_hardening()` 扩展为 middleware + limiter + **自研 routers** 三位一体入口,`app/marzneshin.py` 仍只有一行 diff
- `dashboard/src/modules/nodes/dialogs/sni-suggest/` 新增,对 upstream `dashboard/src/` 其它路径零修改(同样的"冲突面 = 一行"哲学现在也适用前端)

## 💭 最新想法(给未来的 CTO)

**Round 1 教训(仍有效)**:
- **"附加看似小的 infra PR" 是 Round 1 最大价值**:PG/Redis compose profile + 速率限制一次到位,让 Round 2 SNI 选型器直接吃到 PR 门禁与测试 infra 的红利
- **PR 粒度稳定模式**:1 PR = 1 SPEC + 1-3 个关联 commit + 测试 + 文档。Round 2 PR #13 (SNI core 1795 行 + 41 测试)仍然一次过 CI,验证该模式能 scale 到中等复杂度特性
- **"upstream 冲突面 = 一行"原则有效**:SNI 模块全部落在 `hardening/sni/`,对 `app/` 和 `dashboard/` 零修改。下一个 follow-up PR(dashboard 端点)才会触碰 upstream,但通过 `app/routes/node.py` 的新路由而非修改现有路由

**Round 2 前半反思**:
- **SNI 选型器的实现选择**(Team Cymru WHOIS / Python 3.13+ vs 3.12 fallback / 指标复用同一 TLS 握手)全部在 SPEC 中预先做过权衡,实现阶段几乎无返工。SPEC-Driven 模式在此大规模验证成功
- **测试覆盖曲线**:Round 1 新增 22 测试,Round 2 前半又 +46 测试,到 63 个。关键是 `hardening/sni/` 的 4 个测试文件全部完全 mock 网络,CI 离线可跑。这是正确的测试哲学,要坚持
- **文档交叉引用习惯**:每个新模块都在 DEVELOPMENT.md + 同层 README + 上级 README 三处互链。这条没写进 rule,但成了事实标准,下轮考虑沉淀

**Round 2 后半反思 + 决策**:

- **差异化 #1 的三层闭环验证了"upstream 冲突面 = 一行"不仅适用后端**:前端 SNI 集成也落在新独立目录 `dashboard/src/modules/nodes/dialogs/sni-suggest/`,对 upstream 其它代码零修改。这个哲学从后端扩到前端后,upstream-sync 的风险面进一步收窄
- **CI 基础设施的隐性 debt 比想象中多**:Round 2 PR #18 第一次触碰 locale JSON 就引爆了 `tools/check_translations.sh` 全局 drift(每 locale >100 key),同时发现 Chromatic 没有 project token。这些都是 main 上躺了很久的 debt,只是之前没 PR 去碰它们。CTO 决策:不把清 debt 捆在 feature PR 里(那样 PR 永远合不上),独立一轮 "CI infra cleanup" 清一次
- **新教训落入 rule 的节奏再评估**:LESSONS 现有 13 条(L-001 到 L-013),其中 8 条已沉淀为 `.agents/rules/*.md`。剩下 5 条都是"单次事件 + 判断题"型,暂不转 rule。下轮开始前再扫一遍,看是否有趋势性重复

**Round 2 后半的三条路径**:

| 路径 | 选 | 预计 | 推进哪个商业目标 |
|---|---|---|---|
| A | **计费 MVP**(Subscription/Payment/Invoice 模型 + 管理员手动激活订阅) | 5-7 天 | 能变现 |
| B | **SNI rate-limit 回填 + CI infra 清债**(locale drift / Chromatic token / UVICORN_HOST 默认值)| 1-2 天 | 稳定性 + 工具链 |
| C | **IP 限制(防账号共享)自研**(Hiddify `shared_limit` 算法 port 到 Marzneshin API) | 3-5 天 | 差异化 #2 |

**CTO 建议**:B → A 串行。B 一两天清掉 CI 债让未来每一个 PR 更爽;然后 A 专注商业化 MVP。C 可以委派 Codex worktree 并行做(IP 限制有明确算法参考,适合 Agent 隔离执行)。但最终选哪个应由用户的**运营 deadline** 决定,而不是技术偏好。下轮开工前 CTO 主动问一次
