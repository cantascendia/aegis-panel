# 项目状态(STATUS)

> 最后更新:2026-04-23 late-2(Round 3 mid — A.4 skeleton + 协作 kit + worktree 规则合入,S-D/S-X 分支就位)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 3 mid —— 多会话并行,差异化 #2 生产化 + 商业化后端 A.2 推进 + 商业化前端 A.4 skeleton 合入 + 协作 kit 合入 + worktree 隔离铁规则**

状态:🔄 进行中。活跃 + 待启 session 已在 SESSIONS.md 登记,L-018/铁规则 #7 要求各 session 跑独立 worktree:

| Session | PR | 状态 |
|---|---|---|
| **S-B 商业化后端**(Claude Code × `aegis-B` worktree) | #46 A.2.1 ✅ merged;A.2.2 待开 | 进行中 |
| **S-F 商业化前端**(Claude Code) | #41 A.4 skeleton ✅ merged(flag-gated OFF);#49 money-critical 测试 ✅ merged | A.5 接力待开 |
| **S-D 部署一体化**(Claude Code × `aegis-D` worktree) | `feat/spec-deploy` 分支已建(SPEC 骨架随 #48 合入);D.0 flesh-out PR 未开 | 待启 |
| **S-X 前端测试基建**(Claude Code × `aegis-X` worktree) | `feat/dashboard-tests-x0` 分支已建 | 待启 |
| **S-I iplimit 生产化**(Codex × `Marzban-iplimit-production` worktree) | #40/#42/#43/#44/#45 全 ✅ merged | 已完工(归档)|
| **S-O 文档守护**(Claude Code × `aegis-O` worktree,part-time) | #48 协作 kit + #52 worktree 规则 ✅ merged;本分支 `docs/ai-cto/round-3-mid-late2-refresh` 刷 STATUS/DECISIONS/LESSONS/ROADMAP/rules | 触发中 |

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
- 自研核心功能 **4/8** 落地(admin 速率限制,SNI 智能选型器,**IP 限制 MVP**,**计费数据面 + Admin UI**)
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
- 关键缺口(Round 3+):EPay 网关对接实现(A.2)/ TRC20 poller(A.3)/ 用户购买 UI(A.4)/ APScheduler 自动化(A.5)/ IP 限制真实节点 E2E / CF Tunnel 集成 / 审计日志 / 健康度仪表盘 / 备用通道 / RBAC;小债:SNI rate-limit 回填 / `hardening/iplimit` 白名单 + Redis SCAN / TZ 对齐文档

## 当前代码质量评分

**7.6 / 10**(R0 5.0 → R1 6.8 → R2 前半 7.1 → R2 v0.2 7.3 → **R3 opener 7.6**)

| 维度 | R0 | R1 | R2 v0.2 | **R3 opener** | 变化驱动 |
|---|---|---|---|---|---|
| 架构 | 7 | 7 | 7 | **8** | aggregator + Alembic 不变性规则让 upstream 冲突面从"每次多一行"降到"1 行封顶",架构抽象升了一档 |
| 代码质量 | 6 | 6 | 7 | **7** | iplimit / billing 模块基本符合 `.agents/rules/python.md`,但 iplimit 有白名单 / SCAN / TZ 等小 🟡 遗留 |
| 性能 | 5 | 6 | 6 | **6** | iplimit N+1 已在 M-1 修掉;billing 查询未到性能瓶颈;未变化 |
| 安全 | 3 ⚠️ | 8 | 8 | **8** | 保持 |
| 测试 | 1 ⚠️ | 5 | 6 | **7** | 171 passed(R2 末 94 → R3 opener +77,主要来自 iplimit 5 个场景覆盖 + billing states/admin 覆盖) |
| DX | 6 | 8 | 8 | **8** | LESSONS +L-014/15/16,rules +两条硬规则,CI +stepped-upgrade 门禁,DX 深化 |
| 功能完整性 | 4 | 4 | 5 | **6** | 自研核心 4/8(+IP 限制 MVP +计费数据面/Admin) |
| UX | 7 | 7 | 7 | **7** | 用户页加 IP limiter tab + billing admin 三页全通(plans / channels / invoices),invoices 详情 dialog 含 TRC20 字段与审计 audit log;用户侧购买 UI 未建,暂不升分 |

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
  - ⏳ SNI runbook(`deploy/README.md` "全部候选不合格" 排查手册)
  - Reality 配置审计器(Skill 已定义,代码未起)
  - Reality 健康度仪表盘(差异化 #3,v0.3)
- **商业化基础**:
  - 计费系统 MVP(`Subscription` / `Payment` / `Invoice` 模型)
  - 审计日志(`AuditLog` 表 + 中间件)
  - 告警系统(超额 / 临期 / 异常登录)
  - RBAC(v0.3)
- **部署**:
  - `deploy/install.sh` 一键单节点
  - `deploy/cloudflare/` CF Tunnel 自动化
  - Ansible 多节点 playbook
- **Round 1 遗留小事**:
  - `UVICORN_HOST` 默认 `0.0.0.0` → `127.0.0.1`(CLAUDE.md 铁律要求,需带 deprecation)
  - `pyproject.toml` 的 `[tool.black]` 块清理(已被 ruff format 替代)
  - `v2share==0.1.0b31` beta 替代评估
  - CI 加 PostgreSQL matrix(捕获 Round 2 新迁移的 PG 兼容)
  - TrustedProxyMiddleware(反代场景下的 X-Forwarded-For 支持,速率限制真实落地依赖这个)
  - `datetime.utcnow()` 迁移到 timezone-aware(PyJWT 2.10+ 触发 DeprecationWarning)
  - cryptography 46 的 x509 `not_valid_before_utc` / `not_valid_after_utc` 迁移

## 竞品关键发现

不变 —— 见 `docs/ai-cto/COMPETITORS.md`。Round 1 未做竞品跟踪刷新,下次 STATUS 更新(Round 2 末)做。

## 🔀 分支状态

- `main` — PR #1~#14 全部合入(SHA `94b5baf`)
- **Stale 远端分支**(待授权删):
  - `origin/fix/marznode-testcapi-import` — 内容已作为 PR #6 合入,base 旧于 PR #7 rate-limit,merge 会删除速率限制配置
  - `origin/chore/deps-audit-2026-04` — 3 个 deps 升级已与 main 一致(cryptography 46 / fastapi 0.121 / starlette 0.49),merge 会删除 main 上 800+ 行自研代码
  - 建议:用户运行 `git push origin --delete fix/marznode-testcapi-import chore/deps-audit-2026-04` 或在 GitHub UI 删
- 下一个建议分支:取决于用户下一步选择(Round 2 后半 scope:计费 MVP / SNI rate-limit 回填 / CI infra 清债)

## 📅 最后同步确认

**Round 3 mid late-2 —— S-O 第一次正式触发刷新**(2026-04-23 late-2,按铁律 #6 每 3 轮 / 每重大 merge 1 条):

本次 5 条合入摘要(按时间序):
- **#41 A.4 用户购买 UI skeleton**(S-F):`dashboard/src/modules/billing/user/` 新建 7 组件 + 2 lazy route + types/hooks/fixtures + i18n 子树;`VITE_FEATURE_BILLING_USER` flag 默认 OFF;sidebar Account 组 append-only;upstream `dashboard/src/` 其它路径零修改
- **#46 A.2.1 provider abstraction + EPay adapter**(S-B):money-critical interface + EPay payload/verify 落地,未接调度器
- **#48 协作 kit**(S-O 从 S-F 切出):`docs/ai-cto/SESSIONS.md` 确立多会话裁判台 charter + 冲突地带表 + append-only 铁规则 6 条;补 SPEC 骨架三份(deploy / reality-audit / dashboard-tests)给 S-D/S-R/S-X kickoff contract;`.agents/rules/i18n-extractor.md` 固化 L-012/L-017 两条 drift-gate 硬规则
- **#49 A.4 money-critical 组件单测**(S-F):CartSummary 小计 / PlanCard 价格显示的 safety net
- **#52 worktree 隔离铁规则**(S-F/S-O 联合):SESSIONS.md +铁规则 #7;LESSONS.md +L-018(同一 working tree 并发跑多 session → branch/stash/PR 撞车全套);`tools/setup-session-worktrees.sh` 一键建 4 个 aegis-{B,D,R,X} worktree

**下一步触发**:A.2.2 webhook endpoint(S-B)→ A.5 scheduler(S-B 后续)/ S-D 首日 SPEC flesh-out PR(`feat/spec-deploy` 分支已开待干)/ S-X 首日 test-infra PR(`feat/dashboard-tests-x0` 分支已开待干)

**本次 S-O 自身的教训**:首次 S-O 触发在 S-D 分支上混改 docs 被反复回滚(同工作树多 session 竞争),最终按 L-018/铁规则 #7 建 `aegis-O` worktree 隔离后才稳定完成刷新 —— 证明 worktree 规则本身是对的,S-O 不可豁免

---

**Round 2 v0.2 差异化 #1 用户可见闭环完成**(2026-04-22):
- **18 个 PR 合入**(#1~#18 全绿或核心三门禁全绿)
- **78 个后端通过测试** + 1 skip;dashboard 2 个(未扩)
- SNI 三层全通:CLI(PR #13)→ REST(PR #16)→ UI(PR #18)
- `apply_panel_hardening()` 扩展为 middleware + limiter + **自研 routers** 三位一体入口,`app/marzneshin.py` 仍只有一行 diff
- `dashboard/src/modules/nodes/dialogs/sni-suggest/` 新增,对 upstream `dashboard/src/` 其它路径零修改(同样的"冲突面 = 一行"哲学现在也适用前端)
- 四条新教训入库:L-010(slowapi async 兼容)/ L-011(ruff 版本漂移)/ L-012(locale drift CI 陷阱)/ L-013(Chromatic token 缺失)

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
