# 项目状态(STATUS)

> 最后更新:2026-04-23(Round 3 opener — iplimit MVP + billing 数据面/Admin 落地 + Alembic 不变性规则沉淀)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 3 opener —— 商业化 MVP + 差异化 #2 同步推进中**

状态:🔄 进行中。Round 2 v0.2 差异化 #1 SNI 三层闭环已在 PR #18 封顶,Round 3 开局同步推进两条线并沉淀基础设施债。

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

## 未解决问题 / Round 3 后续待做

- **差异化核心**:
  - ✅ SNI 智能选型器 MVP(差异化 #1 三层全通,PR #13/#16/#18)
  - ✅ IP 限制 MVP(差异化 #2 三层全通,PR #24/#26 + 补丁 #31)→ **用户可见闭环完成**
  - ⏳ **IP 限制真实节点 E2E**(本地 fake Redis + fake Marznode 已覆盖,未验证真 Xray access.log 格式、容器 TZ 一致性、生产 Redis 规模)
  - ⏳ **IP 限制白名单 CIDR + Redis SCAN**(cross-review M-5 / T-1,CGNAT 移动网络误杀防线 + 2000 用户规模防 KEYS block)
  - ⏳ SNI rate-limit 回填(slowapi async-def 兼容方案,LESSONS.md L-010)
  - ⏳ SNI runbook(`deploy/README.md` "全部候选不合格" 排查手册)
  - Reality 配置审计器(Skill 已定义,代码未起)
  - Reality 健康度仪表盘(差异化 #3,v0.3)
- **商业化 MVP(A 线 Round 3 opener 已完成数据面 + Admin UI)**:
  - ✅ 数据面 + 状态机 + Webhook 去重(PR #28/#29)
  - ✅ Admin REST + dashboard + channels + invoices(PR #30/#32/#33/#35)
  - ⏳ **A.2 EPay 网关对接实现**(发起支付 / 接收 webhook 的实际 code 未落,目前只有凭据管理 + 状态机)
  - ⏳ **A.3 TRC20 poller**(USDT 链上入账轮询 + 对账)
  - ⏳ **订阅模型**(`Subscription` 表 + 流水 + 到期动作 + 用户订阅面板)
  - 告警系统(超额 / 临期 / 异常登录)
  - RBAC(v0.3)
  - 审计日志(`AuditLog` 表 + 中间件)
- **部署**:
  - `deploy/install.sh` 一键单节点
  - `deploy/cloudflare/` CF Tunnel 自动化
  - Ansible 多节点 playbook
- **基础设施遗留**(Round 2 tail + Round 3 opener 已清大部分):
  - ✅ `UVICORN_HOST` 默认 127.0.0.1 / [tool.black] 清理 / CI PostgreSQL matrix / TrustedProxyMiddleware
  - ✅ CI stepped-upgrade alembic gate(PR #31)/ 自研 model aggregator(PR #34)/ Translations drift gate → diff-based(PR #27)
  - ⏳ `datetime.utcnow()` → timezone-aware(`ops/billing/states.py` 等处仍有 DeprecationWarning)
  - ⏳ `v2share==0.1.0b31` beta 替代评估
  - ⏳ cryptography 46 的 x509 `not_valid_before_utc` / `not_valid_after_utc` 迁移

## 竞品关键发现

不变 —— 见 `docs/ai-cto/COMPETITORS.md`。Round 3 末建议补一轮刷新,重点看 Hiddify 最近的 `shared_limit` 变动是否引入我们未覆盖的场景。

## 🔀 分支状态

- `main` — PR #1~#35 全部合入,head `a4e0c15`(Round 3 opener PR #35 合并点)
- **Stale 远端分支**(2026-04-23 同步后大批已清):已 auto-delete `feat/billing-data-models`、`feat/billing-pricing-and-states`、`feat/dashboard-sni-suggest`、`feat/sni-dashboard-endpoint`、`feat/sni-selector-core` 等合并后分支
- **本地可清理**:`hardening/ip-limiter`(PR #24/#26 已合)、`fix/iplimit-disabled-state-safety-net`(PR #31 已合)、`chore/extra-models-aggregator`(PR #34 已合)—— `git branch -D` 即可,origin 对应 ref 也可删
- 下一个建议分支:取决于用户下一步选择(A.2 EPay / A.3 TRC20 / iplimit E2E / SNI rate-limit 回填)

## 📅 最后同步确认

**Round 3 opener —— 差异化 #2 + 商业化 MVP 数据面/Admin UI 双线落地**(2026-04-23):
- **35 个 PR 合入**(#1~#35)
- **171 个后端通过测试** + 1 skip;dashboard 2 个(未扩)
- 差异化 #2 三层全通:数据面(#24)→ review 修复(#26)→ safety-net + CI 门禁(#31);cross-review 的 C-1/C-2/M-1/M-2/M-3 全部修掉
- 商业化 MVP A.1 全 5 个子 PR 全通:data models(#28)→ pricing+states(#29)→ admin REST(#30)→ admin dashboard(#32)→ admin channels(#33)→ admin invoices(#35)
- 基础设施大升级:`test-alembic-stepped` CI 门禁(阻塞 mutated migration 类 bug)+ `app/db/extra_models.py` aggregator(env.py 永久 1 行 diff)+ 两条硬规则(Alembic 不变性 / 自研 model 注册)
- 三条新教训入库:L-014(自研 model 注册)/ L-015(已 merge revision 不可 mutate)/ L-016(fresh-DB CI 是 false-green)

## 💭 最新想法(给未来的 CTO)

**Round 1 教训(仍有效)**:
- **"附加看似小的 infra PR" 是 Round 1 最大价值**:PG/Redis compose profile + 速率限制一次到位,让 Round 2 SNI 选型器直接吃到 PR 门禁与测试 infra 的红利
- **PR 粒度稳定模式**:1 PR = 1 SPEC + 1-3 个关联 commit + 测试 + 文档

**Round 2 反思(仍有效)**:
- **SPEC-Driven 模式在 SNI 的成功复制到 Round 3**:IP 限制 BRIEF → PR #24 实现 → cross-review → PR #26 修复,验证"先 SPEC 再动手"可以 scale 到跨轮次、多 agent(Codex 实现 + Opus review)协作
- **"upstream 冲突面 = 一行"原则升级**:从"每个模块 1 行"(env.py 散装 import)进化到"整个 fork 1 行"(aggregator 聚合),这是 Round 3 架构抽象的一次质变
- **CI debt 独立清**:Round 2 PR #20/#22/#23 + PR #27 的清债批次模式验证成立,不要捆进 feature PR

**Round 3 opener 反思**:
- **Cross-review 的 ROI 在 iplimit 上爆表**:Opus 主轮 + sub-agent 独立轮两票收敛发现 C-1(buffer replay 造成误封)和 C-2(无条件 re-enable 冲突管理员操作),这两个若 merge 进生产都是"付费用户被误 disable + 管理员无法纠正"的事故。30 分钟 review 换回 P1 生产事故,这个模式 Round 3 全面推广 —— 尤其针对任何**触碰用户状态机**的 PR
- **L-015 Alembic 不变性是本轮最贵的教训**:PR #26 mutate 已 merge 的 `4f7b7c8e9d10` 直接导致"已部署环境永远缺一张表"的静默 bug,CI 全绿完全察觉不到。修复链路 safety-net → stepped-upgrade CI gate → 硬规则进 rules,是标准的"教训 → 防线 → 规则"三步沉淀
- **aggregator 模式适合所有 upstream-owned 注册点**:env.py 是第一个,未来若要扩展 `app/routes/` 的 upstream router 列表、`app/tasks/` 的定时任务注册,都可以用同样的"upstream 文件 1 行 import → fork aggregator 文件集中注册"模式。这是 Round 3+ 的架构红利

**Round 3 mid 的分叉**:

| 路径 | 内容 | 预计 | 推进哪个商业目标 |
|---|---|---|---|
| A | **A.2 EPay 对接 + A.3 TRC20 poller**(把商业化 MVP 从"Admin 可管"推进到"用户可付款") | 4-6 天 | 能变现(关键一跃) |
| B | **iplimit 真实节点 E2E + 白名单 / SCAN 小 🟡**(差异化 #2 从 fake test 推到生产就绪) | 2-3 天 | 稳定性 + 差异化可信度 |
| C | **Reality 配置审计器**(差异化 #3 MVP) | 3-5 天 | 差异化 #3 |
| D | **订阅模型 + 用户订阅面板**(商业化 MVP 的"用户面",与 A.2 耦合) | 3-4 天 | 能变现(串行在 A 之后) |

**CTO 建议**:A → B 并行(A 用主线,B 委派 Codex worktree);A 完工后接 D 闭环用户面。C 放 Round 3 末或 Round 4。最终还是看用户的**运营 deadline 和变现优先级**,开工前主动问一次。
