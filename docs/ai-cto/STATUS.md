# 项目状态(STATUS)

> 最后更新:2026-04-22(Round 2 v0.2 — SNI 用户可见闭环完成)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**Round 2 v0.2 —— 差异化落地中**

状态:🔄 进行中。
- ✅ SPEC-sni-selector.md 已合(PR #10)
- ✅ Round 1 tail(LESSONS → rules + [tool.black] 清理,PR #9)
- ✅ cryptography 46 迁移(PR #11)
- ✅ L-009 教训记入 LESSONS.md(PR #12)
- ✅ `app/utils/crypto.py` 单测补齐 128 行(PR #14)
- ✅ **SNI 智能选型器 MVP**(差异化 #1)落地(PR #13,`6ade9bf`)
  - 6 条硬指标 async 实现 + Team Cymru ASN 查询 + LRU 缓存
  - 5 份区域 seeds + blacklist 零代码可编辑
  - 41 个完全离线 mock 测试 + golden JSON schema drift guard
  - CLI + 退出码契约完整
- ✅ **SNI dashboard 端点**(SPEC follow-up #2)落地(PR #16,`c75359e`)
  - `POST /api/nodes/sni-suggest` 通过 `apply_panel_hardening()` 注册,零 upstream 修改
  - Pydantic 校验 + sudo-admin gate + 60s wall-clock + Semaphore(5) 防并发滥用
  - 10 个 TestClient 测试(auth 401/403 + 422 validation x3 + happy x2 + 504 timeout + 500 seed-load + route contract + rejected section guard)
  - Rate limit(slowapi 装饰器)因 async def 兼容性问题延后,见 LESSONS.md L-010
- ✅ **SNI dashboard 前端集成**(SPEC follow-up #3)落地(PR #18,`efabf43`)
  - `hardening/sni/endpoint.py` 的 REST API 现在有 UI 入口:新建节点对话框底部 "Suggest SNI" 按钮
  - 独立 `SniSuggestDialog` 组件:VPS IP(默认从 address 字段同步)+ count(1-50)+ region(auto/global/jp/kr/us/eu)+ Probe 按钮
  - 结果展示:ASN/国家/耗时 context 条 + 候选列表(score + 6 指标 ✓/✗ 图标 + 复制按钮)+ rejected 折叠区
  - 全部 `t()` 调用配英文 defaultValue,不触发 locale parity CI 陷阱(见 L-012)

## 项目画像(一句话)

Marzneshin 硬 fork,面向商业化机场 >200 付费用户 + 多节点,**Round 2 v0.2 差异化 #1 用户可见闭环完成**(SNI CLI + REST 端点 + 新建节点表单 UI 三层全通)。下一件:Round 2 后半 scope(计费 MVP vs SNI rate-limit 回填 vs CI infra 清债,待用户定 deadline 后决)。

## 产品完成度

- 上游功能 6/6 保留(面板 / 多节点 / Reality / 订阅 / Telegram / 多语言)
- 自研核心功能 **2/8** 落地(admin 速率限制,SNI 智能选型器 MVP)
- 自研基础设施 **全部就绪**:
  - ✅ 安全基线(JWT 外置 / CORS 白名单 / bcrypt 固化 / JWT 时效 60min)
  - ✅ Auth 依赖升级(pyjwt 2.12 / pynacl 1.6.2 / cryptography 46.0.7)
  - ✅ 非 auth 依赖升级(aiohttp / starlette / jinja2 / requests / protobuf / python-multipart)
  - ✅ Redis 客户端(可选,默认禁用,fail-loud 模式)
  - ✅ PostgreSQL 16 compose profile(可选,零破坏)
  - ✅ 速率限制(slowapi + Redis 令牌桶,默认禁用)
  - ✅ 测试基础设施(pytest + ruff + pip-audit CI,**78 个通过测试** + 1 个 SQLite skip):
    - Round 1: smoke / P0 security / cache redis / rate limit / compose profiles / migrations(22)
    - Round 2 新增: sni_asn(6) + sni_checks(16) + sni_loaders(10) + sni_selector(9) + crypto(5) + sni_endpoint(10)
    - Dashboard 单测仍为 2 个(`features/support-us/*.test.*`);SniSuggestDialog 单测留待专项前端 test infra PR(LESSONS L-010/L-012 记录了原因)
  - ✅ 目录骨架(`hardening/` + `deploy/` + `ops/` 各自 README)
  - ✅ **`hardening/sni/`**(Round 2)—— candidate / asn / checks / scoring / loaders / selector + seeds + blacklist + endpoint
  - ✅ **`dashboard/src/modules/nodes/dialogs/sni-suggest/`** + API client(Round 2)—— SniSuggestDialog + useSniSuggestMutation
- 关键缺口(Round 2+):计费 / IP 限制 / CF Tunnel 集成 / 审计日志 / 健康度仪表盘 / 备用通道 / RBAC;小债:SNI rate-limit 回填 / locale drift 清理 / Chromatic token 配置

## 当前代码质量评分

**7.1 / 10**(R0 5.0 → R1 6.8 → R2 前半 +0.3)

| 维度 | R0 | R1 | **R2 前半** | 变化驱动 |
|---|---|---|---|---|
| 架构 | 7 | 7 | **7** | SNI 模块做到了"upstream 冲突面零",验证了 hardening/ 隔离哲学 |
| 代码质量 | 6 | 6 | **7** | `hardening/sni/` 是第一个完全符合 `.agents/rules/python.md` 的新模块 |
| 性能 | 5 | 6 | **6** | LRU 缓存 ASN 查询是未来 SNI 健康度仪表盘的性能护城河 |
| 安全 | 3 ⚠️ | 8 | **8** | Round 2 前半未改安全面 |
| 测试 | 1 ⚠️ | 5 | **6** | 63 个通过测试(+41 SNI +5 crypto,全 mock 离线)|
| DX | 6 | 8 | **8** | DEVELOPMENT.md 加 SNI 用法段,panel README 交叉引用 |
| 功能完整性 | 4 | 4 | **5** | 自研核心 2/8(+SNI 选型器 MVP)|
| UX | 7 | 7 | **7** | 未动(等 SNI dashboard 对接 PR)|

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

**Round 1 tail + Round 2**(6 个 PR):

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
