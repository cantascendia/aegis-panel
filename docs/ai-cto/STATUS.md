# 项目状态(STATUS)

> 最后更新:2026-04-26 late-6(Round 3 mid — 差异化 #3 Reality audit R.1+R.2+R.3 + 商业化 A.5 scheduler + A.3 TRC20 全部 session 0 自动落地,商业化双支付通道闭环 + 差异化 #3 后端闭环就绪)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 3 mid —— 多会话并行,差异化 #2 生产化 + 商业化后端 A.2 推进 + 商业化前端 A.4 skeleton + 协作 kit + worktree 规则合入 + S-D/S-X 正式启动**

状态:🔄 进行中。活跃 + 待启 session 已在 SESSIONS.md 登记,L-018/铁规则 #7 要求各 session 跑独立 worktree:

| Session | PR | 状态 |
|---|---|---|
| **S-B 商业化后端**(Claude Code × `aegis-B` worktree) | #46 A.2.1 ✅ merged;A.2.2 待开 | 进行中 |
| **S-F 商业化前端**(Claude Code) | #41 A.4 skeleton ✅ merged;#49 money-critical 测试 ✅ merged | A.5 接力待开 |
| **S-D 部署一体化**(Claude Code × `aegis-D` worktree) | #58 OPS-deploy-runbook skeleton ✅ merged;D.0 SPEC flesh-out 待开 | 进行中 |
| **S-X 前端测试基建**(Claude Code × `aegis-X` worktree) | #57 X.1 watch-mode + pnpm unify ✅ merged;#59 X.2 test-utils/render + picker/poll tests ✅ merged | 进行中 |
| **S-I iplimit 生产化**(Codex × `Marzban-iplimit-production` worktree) | #40/#42/#43/#44/#45 全 ✅ merged | 已完工(归档)|
| **S-O 文档守护**(Claude Code × `aegis-O` worktree,part-time) | #48 协作 kit + #52 worktree 规则 + #56 第一次刷新 + #60 AUDIT overlay ✅ merged;本分支 `docs/ai-cto/round-3-mid-late3-refresh` 微刷 STATUS | 触发中 |

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
- 自研核心功能 **5/8** 落地(admin 速率限制,SNI 智能选型器,**IP 限制 MVP**,**计费完整后端 = 数据面 + Admin UI + A.5 scheduler + A.3 TRC20 双支付通道**,**Reality 配置审计 R.1+R.2+R.3**)
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
- 关键缺口(Round 3+):用户购买 UI(A.4 完结,S-F)/ Reality 审计 dashboard 页(R.4,S-F-2)/ 真实 ¥0.01 round-trip(需用户对接码商)/ 真实 USDT 测试网 round-trip(A.3 已 ship,需 ops 接 Tronscan stage 验证)/ IP 限制真实节点 E2E / CF Tunnel 集成 / 审计日志 / 健康度仪表盘 / 备用通道 / RBAC;小债:SNI rate-limit 回填 / `hardening/iplimit` 白名单 + Redis SCAN / TZ 对齐文档

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
  - ~~`pyproject.toml` 的 `[tool.black]` 块清理~~ ✅ 已合 PR #9
  - ~~CI 加 PostgreSQL matrix~~ ✅ 已合(`test-postgres` + `test-alembic-stepped` 两 job)
  - ~~TrustedProxyMiddleware (panel-wide)~~ ❌ 撤销:由 D-012 改为 per-feature `*_TRUSTED_PROXIES` env;billing webhook 已用此模式(PR #65)
  - ~~cryptography 46 的 x509 `not_valid_before_utc` 迁移~~ ✅ 已合 PR #11(read-side 用 `_utc`,builder setter 不变,L-009)
  - ~~`v2share==0.1.0b31` beta 替代评估~~ ✅ 已结案 D-013 + `RESEARCH-v2share-evaluation.md`(保留 + vendor 备胎规划,2026-10-26 日历复评)
  - ~~`datetime.utcnow()` 全 app 迁移~~ ✅ **完工**:PR #65(billing webhook 3 处)+ PR #68(`ops/billing/{db,states}.py` 6 处)+ PR #70(upstream `app/*` 26 处 + 1 `utcfromtimestamp`)。统一收口到 `app/utils/_aegis_clocks.now_utc_naive`(fork-local helper,upstream 适配后即删)

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

**Round 3 mid late-2 —— S-O 第一次正式触发刷新**(2026-04-23 late-2,按铁律 #6 每 3 轮 / 每重大 merge 1 条):

本次 5 条合入摘要(按时间序):
- **#41 A.4 用户购买 UI skeleton**(S-F):`dashboard/src/modules/billing/user/` 新建 7 组件 + 2 lazy route + types/hooks/fixtures + i18n 子树;`VITE_FEATURE_BILLING_USER` flag 默认 OFF;sidebar Account 组 append-only;upstream `dashboard/src/` 其它路径零修改
- **#46 A.2.1 provider abstraction + EPay adapter**(S-B):money-critical interface + EPay payload/verify 落地,未接调度器
- **#48 协作 kit**(S-O 从 S-F 切出):`docs/ai-cto/SESSIONS.md` 确立多会话裁判台 charter + 冲突地带表 + append-only 铁规则 6 条;补 SPEC 骨架三份(deploy / reality-audit / dashboard-tests)给 S-D/S-R/S-X kickoff contract;`.agents/rules/i18n-extractor.md` 固化 L-012/L-017 两条 drift-gate 硬规则
- **#49 A.4 money-critical 组件单测**(S-F):CartSummary 小计 / PlanCard 价格显示的 safety net
- **#52 worktree 隔离铁规则**(S-F/S-O 联合):SESSIONS.md +铁规则 #7;LESSONS.md +L-018(同一 working tree 并发跑多 session → branch/stash/PR 撞车全套);`tools/setup-session-worktrees.sh` 一键建 4 个 aegis-{B,D,R,X} worktree

**下一步触发**:A.2.2 webhook endpoint(S-B)→ A.5 scheduler(S-B 后续)/ S-D D.0 SPEC-deploy.md flesh-out PR(OPS-runbook 骨架已在 #58)/ S-X X.3+ 继续覆盖更多 dashboard 组件单测(test-utils 基建已在 #59)

---

**late-3 追加同步**(2026-04-23 late-3,承接 late-2 后的 3 个并行 merge):

- **#57 S-X X.1**:pnpm-lock 漂移修复 + Vitest watch-mode 在 Windows 正确退出;S-X 从"分支就位"升到"进行中"
- **#58 S-D OPS-deploy-runbook 骨架**:第一次 S-D 正式交付(单 docs 文件),给运维侧留下"节点迁移 / DB 备份 / CF token 泄露应急"四条 runbook 占位;S-D 从"分支就位"升到"进行中"
- **#59 S-X X.2**:`dashboard/src/test-utils/render.tsx` 加 i18next + tanstack-query + theme 三件套 provider;补 date-range-picker / usePolling 两个单测,证明 test-utils 好用

S-O 本轮两次触发消化了 #41/#46/#48/#49/#52/#54/#56/#57/#58/#59/#60 共 11 个 PR,STATUS/SESSIONS/DECISIONS/LESSONS/ROADMAP/AUDIT 全部对齐到现状。

**本次 S-O 自身的教训**:首次 S-O 触发在 S-D 分支上混改 docs 被反复回滚(同工作树多 session 竞争),最终按 L-018/铁规则 #7 建 `aegis-O` worktree 隔离后才稳定完成刷新 —— 证明 worktree 规则本身是对的,S-O 不可豁免

---

**late-6 追加同步**(2026-04-26 late-6,**差异化 #3 Reality audit 后端闭环 + 商业化 A.5 scheduler 落地**,session 0 自动连击 5 个 PR — #72/#73/#74/#75/#76/#77;实际本轮 2 个新差异化里程碑):

- **#72 / #73 季度研究**:Marzneshin upstream 6 个月 dormant 报告 + COMPETITORS.md 加入 "Aegis (我们)" 列(quarterly refresh framework 第一次跑通)
- **#74 R.1 Reality 配置审计 core**:`hardening/reality/{checks,scoring,report,seeds}` —— 五件套指标(SNI 冷门度 / ASN 同质性 / 端口非标准 / shortId 合规 / connIdle 短设)+ 评分 + Markdown/JSON 渲染。44 测试。compass_artifact_*.md 五件套现在第一次有可执行体现
- **#75 R.2 CLI + loader + 黄金 fixture**:`hardening/reality/cli.py` argparse 双模式(`--config` 文件 / `--from-db`)+ `from_db_rows` / `from_xray_config` loader + golden fixtures(perfect.json 应 ≥90 green / broken.json 应 <60 red)。CLI 退出码契约 `0/1/2` 锁定。20 测试
- **#76 R.3 Reality REST endpoint**:`POST /api/reality/audit` (sudo-admin 门控 / 60s wait_for / 504 on WHOIS hang) + `apply_panel_hardening` include_router 一行。`asyncio.to_thread(check_asn_match)` 解决 sync `asyncio.run()` 与 FastAPI 运行 loop 冲突的问题(L-023 候选)。10 测试,**reality 全套 74 测试**
- **#77 A.5 计费 scheduler**:`ops/billing/{scheduler,grants}.py` 两条 APScheduler 任务 —— `reap_expired_invoices`(每 60s,`awaiting_payment` 过 `expires_at` → `expired`)+ `apply_paid_invoices`(每 30s,`paid` → `applied` + 用户 `data_limit` / `expire_date` 加 grant)+ `install_billing_scheduler` lifespan 包装(同 iplimit 模式)。25 测试,billing 套 137 测试
- **#79 A.3 TRC20 直收支付通道**(关键里程碑):**计费第二条支付通道全后端就位**。`ops/billing/{providers/trc20,trc20_config,trc20_matcher,trc20_client,trc20_poller}.py` 5 个新模块。**与 EPay 反向**:无第三方 webhook,我们 30s 轮询 Tronscan 公开 API。两层匹配 = 优先 memo(HMAC-SHA256 8 字符,salt 防爆破)+ 退回精确金额 + window(cents-dither 解并发)。无模糊匹配 / 无超付欠付补偿 = 审计干净。`MIN_CONFIRMATIONS` 默认 1(Tron 3 秒块时,paranoid 可调 19)。state-machine 守卫保 idempotency:同一 transfer 重新喂入不会双付。60 测试,**billing 全套 197 测试**(137 → 197)

**差异化 #3 (Reality 配置审计) 后端闭环完成**:SPEC(#10 之前)→ R.1 core(#74)→ R.2 CLI+loader(#75)→ R.3 REST(#76)。R.4 dashboard UI 待 S-F-2 session 启动(前端地盘),后端闭环已 production-ready。

**商业化推进里程碑**:
- A.5 scheduler 让"用户付钱后自动延长"链路从 webhook 到 User row 全自动,不再需要 admin manual_apply 手动触发
- A.3 TRC20 + EPay 双支付通道全部后端就位 —— 用户结账时可选 EPay(支付宝/微信中介)或 TRC20(USDT 直收无中介手续费)。**A.x 计费**剩余真实开发动作 = A.4 用户购买 UI 收尾(前端,S-F)+ 真接 ¥0.01 round-trip(用户外部动作 = 接一家码商 stage 测试)+ 真接 USDT 测试网 round-trip(用户外部动作 = ops 接 Tronscan stage 验证一遍)

**新增 LESSONS / DECISIONS**:
- **L-023 候选** `asyncio.run()` 不能从 FastAPI 已运行的 loop 内调用 —— 用 `asyncio.to_thread` 包装可重用现有 sync 实现而不必改写为 async
- **L-024 候选** 链上支付 vs. 第三方网关 = 拉模型 vs. 推模型,trust boundary 不一样;TRC20 选 poll 而不是想着搞个 webhook 是因为 Tron 本身不推,只能读
- **D-014 候选** 计费 grant 应用 = pricing.py(预付,无 DB)/ grants.py(后付,改 User)分离;expire_strategy 政策:`NEVER` / `START_ON_FIRST_USE` 首次 duration grant → `FIXED_DATE` anchored 到 now;`FIXED_DATE` 已 lapsed → 从 `max(now, expire_date)` 延长
- **D-015 候选** 链上支付匹配策略 = "memo > exact-amount + window";拒绝模糊匹配(under-pay / over-pay 都不补偿);cents-dither (`invoice_id % 1000` millis) 解并发;rate 操作员锁定不自动 fetch ticker(避免双 API 依赖 + 市场波动期匹配歧义)

**Auto-merge 节奏继续稳态**:本轮 6 个 PR(#73/#74/#75/#76/#77/#79)全部 session 0 单跑(+ #78 docs 间隔同步),Monitor + auto-merge 链路 6/6 成功,**用户 0 手动操作**。

**SESSIONS.md 状态**:Round 3 mid 接近收口 —— 差异化 #1 ✅ / 差异化 #2 ✅(MVP)/ 差异化 #3 ✅(后端);A.3 / A.5 ✅。剩余真功能开发块 = R.4 dashboard(S-F-2)+ A.4 用户购买 UI(S-F-延续)+ 真接 ¥0.01 round-trip(用户外部动作)+ 真接 USDT round-trip(用户外部动作)。

---

**late-5 追加同步**(2026-04-26 late-5,**Round 1 leftover 全清零里程碑**:session 0 自动连击 4 个 PR — #67/#68/#69/#70):

- **#67 late-4 micro-refresh**:STATUS 口径同步 + L-019/L-020/L-021 + D-012(反代信任 = per-feature CIDR env,反对 panel-wide middleware,模板代码在 `ops/billing/config.py`)
- **#68 billing datetime sweep**:`ops/billing/{db,states}.py` 6 处 `datetime.utcnow()` → 共享 `_now_utc_naive` helper。1 个 helper 函数,3 行 docstring,4+2 callsite 替换。CI 一次过
- **#69 v2share 评估结案**:研究文件 `docs/ai-cto/RESEARCH-v2share-evaluation.md` ~110 行 + D-013 lock 决策。结论:keep + vendor hedge,2026-10-26 复评
- **#70 upstream app/ datetime sweep**(关键里程碑):**第一次** session 0 主动改 upstream surface(`app/*` 10 文件 + 1 新文件 `app/utils/_aegis_clocks.py`)。26 + 1 callsite 替换。理由:Python 3.12 必修 deprecation + 行为字节级保持 + bounded surface(11 文件)+ 上游必将做相同事

**Round 1 leftover 状态**:**全部清零**(原 6 项,过去会话 5 项已清,本轮清最后 1 项)。

**Auto-merge 节奏稳态确立**(本轮强信号):
- session 0 PR + Monitor → CI 全绿 → `gh pr merge --squash --delete-branch` → `git pull --ff-only` 链路验证 4 次,**用户 0 手动操作**
- 失败路径(CI 红灯)Monitor 设的 `if [ "$fail" = "0" ]` 守卫会停止合并,人工介入 — 本轮 4 PR 没触发,但守卫健全

**新增 LESSONS / DECISIONS**:
- **L-022** 何时打破"不改 upstream 文件"的 Round 1 默认规则:Python 3.12 必修 deprecation + 行为字节级保持 + 触面 ≤ 一打文件 + 上游早晚必做。三条同时满足 = 改;缺一条 = 不改

**SESSIONS.md 状态**:仍 active session count = 0(从 #66 合到 late-5 之间无新 active session;session 0 全自动跑了 4 个 micro 任务)。Round 1 leftover 清零是节奏切片,不强制启 Round 4 — 等用户决定下一步差异化(R.1 Reality 配置审计 / A.5 scheduler / 真接 ¥0.01 round-trip)。

---

**late-4 追加同步**(2026-04-26 late-4,承接 late-3 后的 6 个 merge — #61/#62/#63/#64/#65/#66):

- **#61 / #62 / #63** 收尾 S-O late-3 触发 + session 0 工具扩展 + S-X X.3 测试 infra 收口(coverage artifact 非阻塞 + test-utils README)
- **#64 S-D D.0** SPEC-deploy.md flesh-out:Reality 区域 SNI 矩阵(`REALITY_SNI_DEFAULT_{GLOBAL,JP,KR,US}` 按 compass 选冷门 CDN 域)+ DPI blocklist(`www.google.com` / `speedtest.net` 硬拒)+ uTLS 指纹白名单(只许 `chrome / firefox / edge / safari / ios`,拒 `chrome_pq` / `randomized`)+ 生产 compose 9 维度对比表 + CF Tunnel token 最小权限矩阵 + AC-D.1.10/11/12 + AC-D.4.5/6 + 3 条 risks。session 0 cross-checked `REALITY_*` env 命名空间与 SPEC-sni-selector.md 不冲突
- **#65 S-B A.2.2 + session 0 安全 review**:S-B 落 `POST /api/billing/cart/checkout` + `POST /api/billing/webhook/epay/{channel_code}` + Fernet `merchant_key_encrypted` + `extra_config_json` (`sign_body_mode` / `allowed_ips`) + 5 张表 schema 微扩 + 19 测试。session 0 加 commits 修了 1 个 🔴 critical(`X-Forwarded-For` 任意来源被信任 → IP 白名单可伪造 → 加 `BILLING_TRUSTED_PROXIES` env)+ 3 处 `datetime.utcnow()` Python 3.12 deprecation + webhook disabled-channel 404 → 410 + 2 个新回归测试(spoofing-detection / disabled-410)。CI 4 轮过(2 轮 ruff format/check 漂移修)
- **#66 OPS-sni-runbook 落地**(session 0,SPEC-sni-selector follow-up #3):`docs/ai-cto/OPS-sni-runbook.md` ~270 行,9 段(标准流程 / 输出结构 / 退出码 / 零候选 emergency / ASN 查不到 emergency / 上线后验证 / 周期性维护 / blacklist+seeds SOP / 已知限制),按 OPS-deploy-runbook 四段式("检测 / 判定 / 处置 / 验证")。`deploy/README.md` 加 5 份 OPS-* 索引表;`hardening/sni/README.md` 加 runbook 入口

**差异化 #1(SNI 智能选型器)端到端闭环完成**:SPEC(#10)→ core+CLI(#13)→ REST endpoint(#16)→ dashboard UI(#18)→ ops runbook(#66)。**5 段五个 PR**,从 spec-driven 到运维手册 全程符合 D-005 模板规约。Round 2 v0.2 差异化 #1 标记为 ✅ Done。

**A.2.x 计费链路推进**:`A.2.2 webhook 端到端可接收 + 状态机 + 审计 + 加密` 全部就位。下一步 A.5 scheduler(自动 expire / cron 巡检)+ 真实 ¥0.01 round-trip(stage 验证,需 mock 码商或真接一家)。

**新增 LESSONS / DECISIONS**:
- **L-019** Reverse-proxy 信任 = per-feature CIDR env(不是全局 middleware)
- **L-020** `TestClient` 默认 peer `"testclient"` 不是 IP,IP-aware 测试要 `client=("127.0.0.1", port)` 显式传
- **L-021** Cross-session reviewer push commit 前必须同时跑 `ruff check + ruff format --check` 全自有目录
- **D-012** 锁定"per-feature `*_TRUSTED_PROXIES` env"作为反代信任的设计模式,模板代码已在 `ops/billing/config.py` + `checkout_endpoint.py:_peer_is_trusted_proxy`,下个 IP-aware feature copy 即可

**SESSIONS.md 状态**:S-B / S-D / S-X / S-F / S-O 全部"完成本轮一块",当前 active session count = 0(从 #66 合后到 late-4 触发 之间)。Round 3 mid 节奏在 "merge → S-O 微刷 → 下一 session 启动" 之间稳态。

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
