# 项目状态(STATUS)

> 最后更新:2026-04-21(Round 1 收官)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 1 —— v0.1 基底加固**

状态:✅ 已完成。代码 PR #1/#2/#3/#4/#7 已合并,记忆刷新 PR #8 收尾中。

## 项目画像(一句话)

Marzneshin 硬 fork,面向商业化机场 >200 付费用户 + 多节点,**Round 1 完成了 P0 安全 + 测试基础设施 + PostgreSQL/Redis 可选集成 + 目录骨架**,进入 Round 2 差异化阶段。

## 产品完成度

- 上游功能 6/6 保留(面板 / 多节点 / Reality / 订阅 / Telegram / 多语言)
- 自研核心功能 **1/8** 落地(admin 登录速率限制,PR #7)
- 自研基础设施 **全部就绪**:
  - ✅ 安全基线(JWT 外置 / CORS 白名单 / bcrypt 固化 / JWT 时效 60min)
  - ✅ Auth 依赖升级(pyjwt 2.12 / pynacl 1.6.2 / cryptography 46.0.7)
  - ✅ 非 auth 依赖升级(aiohttp / starlette / jinja2 / requests / protobuf / python-multipart)
  - ✅ Redis 客户端(可选,默认禁用,fail-loud 模式)
  - ✅ PostgreSQL 16 compose profile(可选,零破坏)
  - ✅ 速率限制(slowapi + Redis 令牌桶,默认禁用)
  - ✅ 测试基础设施(pytest + ruff + pip-audit CI,22 个通过测试 + 1 个 SQLite skip)
  - ✅ 目录骨架(`hardening/` + `deploy/` + `ops/` 各自 README)
- 关键缺口(Round 2+):SNI 选型器 / 计费 / IP 限制 / CF Tunnel 集成 / 审计日志 / 健康度仪表盘 / 备用通道 / RBAC

## 当前代码质量评分

**6.8 / 10**(Round 0 的 5.0 → Round 1 提升 1.8)

| 维度 | Round 0 | Round 1 | 变化驱动 |
|---|---|---|---|
| 架构 | 7 | **7** | 保留上游控制面/数据面分离,新增 `hardening/ops/deploy/` 与 upstream 解耦 |
| 代码质量 | 6 | **6** | ruff + biome CI 就位,但 upstream 代码本身未动 |
| 性能 | 5 | **6** | PostgreSQL 支持路径打通,N+1 修复留给 v0.2 |
| 安全 | 3 ⚠️ | **8** | JWT 外置 + CORS 白名单 + bcrypt=12 + 速率限制 + auth / runtime 依赖清 CVE |
| 测试 | 1 ⚠️ | **5** | pytest + pytest-alembic + pytest-cov + 22 个通过测试(全部 P0 / 脚手架关键路径)|
| DX | 6 | **8** | DEVELOPMENT.md 完整 / makefile 补齐 / CI 全绿门禁 / .gitattributes 根治 CRLF |
| 功能完整性 | 4 | **4** | 商业化功能 0/8,下轮开干 |
| UX | 7 | **7** | 未动 |

## 关键决策记录(Round 1 新增)

见 `docs/ai-cto/DECISIONS.md`(D-005 至 D-009)。

## Round 1 PR 汇总

| PR | 内容 | 状态 | SHA |
|---|---|---|---|
| #1 | 脚手架 + 测试 infra + .gitattributes | ✅ 合并 | `e9b543c` |
| #2 | P0 安全(JWT/CORS/bcrypt/auth 依赖升级) | ✅ 合并 | `8969e58` |
| #3 | 非 auth 依赖升级(aiohttp/starlette/jinja2/...) | ✅ 合并 | `a3d932c` |
| #4 | PostgreSQL 16 + Redis 7 可选集成 | ✅ 合并 | `2097542` |
| #5 | STATUS 依赖安全基线中间刷新 | ✅ 合并 | `67a8c3a` |
| #6 | 修复 `_testcapi.INT_MAX` 阻塞 full app import | ✅ 合并 | `f5188f2` |
| #7 | Admin 登录速率限制 | ✅ 合并 | `482d2cc` |
| #8 | Round 1 记忆刷新(STATUS / DECISIONS / LESSONS) | 🟡 待合 | `74eb830` |

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

## 未解决问题 / Round 2 待启动

- **差异化核心**:
  - SNI 智能选型器 MVP(ROADMAP v0.2 差异化 #1)
  - Reality 配置审计器
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

- `main` — Round 1 代码 PR #1/#2/#3/#4/#5/#6/#7 已合入
- `docs/round-1-memory-refresh` — PR #8,本次记忆刷新,待合
- 下一个建议分支:`chore/round-1-tail-cleanup`(LESSONS → rules + 小工程债)

## 📅 最后同步确认

**Round 1 结束**,确认:
- 5 个功能 / 基建 PR 全绿通过 CI(lint / test / pip-audit):#1/#2/#3/#4/#7
- 2 个收尾 PR 已合:#5 STATUS 中间刷新,#6 `_testcapi.INT_MAX` 修复
- 22 个通过测试 + 1 个 SQLite DDL skip:smoke / P0 security(6)/ cache redis(5)/ rate limit(4)/ compose profiles(1)/ migrations(3+1 skip)
- 7 条新 "session-level 经验" 记入 `docs/ai-cto/LESSONS.md`

## 💭 最新想法(给未来的 CTO)

- **"附加看似小的 infra PR" 是 Round 1 最大价值**:PG/Redis compose profile + 速率限制一次到位,让下一轮 SNI 选型器 / 计费 MVP 直接能用 Redis 做缓存而不用先改基础设施
- **PR 粒度**:1 PR = 1 SPEC + 1-3 个关联 commit + 测试 + 文档是这轮的稳定模式,继续沿用
- **"upstream 冲突面 = 一行"原则有效**:所有涉及 `app/marzneshin.py` 的功能都通过 `apply_panel_hardening(app)` 之类的单入口函数注入,未来 upstream sync 只合一行即可
- **CI 教训密集出现**:7 条经验里 6 条是 CI/工具配置坑,说明 Round 0 的 CTO 配置不够具体。Round 2 开始前,应该把 LESSONS.md 里的条目纳入 `.agents/rules/` 作为硬性 rule
- **Round 2 启动前需要一份"商业化最小 MVP"的 scope 文档** —— ROADMAP 列了计费 + SNI 选型 + 一键部署三件事,但哪个先做取决于"能变现"和"能抗封"哪个是当前最大瓶颈。下轮第一件事是 CTO 与运营方对齐这个 scope
