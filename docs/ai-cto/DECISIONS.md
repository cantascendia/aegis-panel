# 决策记录(DECISIONS)

> 格式:每条决策 = (编号 + 日期 + 决策 + Why + How to apply + 推翻条件)
> 倒序排列,最新在上

---

## D-011 | 2026-04-23 | 多会话并行的裁判台机制:SESSIONS.md + worktree 隔离 + append-only 冲突地带表

**决策**: 随 Round 3 mid 进入多会话并行期(Claude Code × N 实例 + Codex + Antigravity/未来 Gemini),引入**三件套**作为并行协作契约:

1. **`docs/ai-cto/SESSIONS.md` 裁判台**:每个 session 开 PR 前必须在活跃表登记编号 / 工具 / 模型 / **独占地盘** / 当前 PR / 状态
2. **冲突地带表 + append-only 规则**:跨 session 必然触碰的公共文件(`hardening/panel/middleware.py` 的 `include_router`、`app/db/extra_models.py` 的 import、`dashboard/src/features/sidebar/items.tsx` 的 sidebar 组、两大 locale JSON、`dashboard/package.json` devDeps、`.github/workflows/*.yml`、`dashboard/src/routeTree.gen.ts`)一律 append-only,后 merge 方 rebase 处理
3. **worktree 隔离铁规则**(#52 固化):每个并发 Claude session 必须有独立 git worktree(`C:/projects/aegis-{B,D,R,X,O}`)或独立 repo 克隆;主 repo 留给 session 0(审阅 + merge 裁判);**禁止在同一个工作目录并发跑 2+ Claude session** —— 违反会造成 branch 切换撞车 / stash 污染 / PR 挂错分支(L-018 全套事故)

**Why**:

- Round 3 opener 之后观察到一个指数级 risk:多个 session 若任意一个动 `app/db/migrations/env.py` 或 `hardening/panel/middleware.py` 都会冲突;SPEC-level 分工不够细,必须到**文件级 append-only 契约**
- 过去靠口头 / PR 描述里写"我动了啥"的做法在 3+ session 并行时不可持续,必须有一份共同看齐的 source of truth
- S-O 作为 part-time 独立 session 而不是混入其他 session,避免让 feature session 分心于文档压缩;铁律 #6 才能真的执行
- **worktree 必要性的直接证据**:S-O 第一次触发时在主 repo 上改 docs,被其他 session 的 `git checkout` 反复吃掉;切到 `aegis-O` worktree 后立即稳定 —— L-018 不是理论,是运营事实

**How to apply**:

- **启动一个新 session**:
  1. 主 repo 跑 `bash tools/setup-session-worktrees.sh`(幂等,首次会建 aegis-B/D/R/X)
  2. S-O 单独建:`git worktree add C:/projects/aegis-O docs/session-O-home`(脚本未覆盖 O,按需手建)
  3. 新 Claude session 第一条消息粘 `cd C:/projects/aegis-{letter}`
  4. Session 自己 `git checkout -b feat/<specific-task>` 切到真工作分支
- **冲突地带改动**:必须 append-only(新段组 / 新 import 行 / 新 sidebar 组);`dashboard/src/routeTree.gen.ts` 禁手改,后 merge 方重跑 `npx tsr generate`
- **PR body 模板**新增两行:`I touch:` / `I don't touch:`,链接到 `SESSIONS.md`
- **S-O 刷新流程**:cd 到 `aegis-O` → `git checkout -b docs/ai-cto/round-N-<milestone>-refresh` → 改 STATUS/LESSONS/DECISIONS/ROADMAP/rules → 独立 PR → 合入后删分支 + 清 worktree
- S-O 触发时只刷 `docs/ai-cto/**`(非 SPEC-*)+ `.agents/rules/**`;如需动代码 → 停,让对应 session 处理

**推翻条件**:
- 并行 session 数回到 ≤ 1(单主 session 推进所有 scope),裁判台变冗余,worktree 规则也可弱化
- 仓库引入 monorepo 工具(Nx/Turborepo/Bazel)提供强隔离的包边界,冲突面自动收拢到包清单
- SESSIONS.md 本身变成冲突点(多人同时追加)—— 这意味着裁判台也要拆,可能的下一步是 per-session charter 文件(`docs/ai-cto/sessions/S-B.md`)

---

## D-010 | 2026-04-22 | 计费 MVP 支付策略:易支付 + TRC20 双轨,放弃 Stripe

**决策**: Round 2 path A(计费 MVP)只做两个支付通道:

1. **易支付(EPay)协议** 作为**主通道**,对接中国码商。面板实现通用协议适配器(兼容 SSPanel / Xboard / v2board 生态中的标准 易支付 接口),管理员在后台填 `merchant_code` + `merchant_key` + `gateway_url` 即启用,支持多家码商并行
2. **USDT TRC20 自建轮询** 作为**副通道**,零第三方依赖,运营方只配置一个公开收款地址,后端每 30 秒轮询 Tronscan 公开 API 匹配订单
3. **明确放弃**:Stripe、NOWPayments 等需要实体/KYC 的支付通道。**不写 stub**

**Why**:

- 运营方条件:**无公司实体、无启动资金、中国用户占多数(~70%)**(见本轮用户确认)
- 中国普通用户 70%+ 无法持有 USDT(2021 "924 通知" 后 fiat-on-ramp 基本关闭,剩余路径对普通用户门槛过高)→ 没有 易支付 通道 = 直接失去大多数市场
- 易支付 是 Chinese 机场生态的**事实标准**,一套适配器 = 兼容数十家码商,可根据需要随时切换运营方
- TRC20 直付作为副通道提供两层价值:(a) 对懂 crypto 的用户提供无中介选项,(b) 当主通道(码商)被冻或跑路时的保险机制
- Stripe 无实体 = 永不可启用。写 stub 让代码假装有选项 = **误导性代码**,有人会以为快启用就试,腐烂没人维护。未来真有实体再专门开一个 PR 加 Stripe,比延续一年半旧 stub 干净

**How to apply**:

- `ops/billing/providers/epay.py` 实现通用 易支付 协议
- `ops/billing/providers/trc20.py` 实现 Tronscan 轮询 + 订单匹配
- `BasePaymentProvider` 抽象封装,未来 BTCPay Server / NOWPayments / Stripe 追加不影响状态机
- 配置硬约束:`BILLING_TRC20_ENABLED` + `BILLING_EPAY_ENABLED` 独立默认关,不启用则对应通道不暴露给用户
- 面板 checkout UI 展示两个 tab(易支付默认、USDT 第二),**不是选单**,让用户明确看到"还有一条路"
- 收款资金路径由用户在**码商后台**选 USDT 结算 → 汇到运营方 TRC20 钱包 → 运营方手动 OTC 换 JPY(见 `OPS-jpy-cashout.md`)
- 码商选择与合作规范见 `OPS-epay-vendor-guide.md`
- Aegis Panel 代码只管"到 USDT 为止";JPY 换汇是**运营过程**不是产品功能,不进代码

**推翻条件**:
- 运营方注册了日本法人且 Stripe 批准了商业类目(极罕见,VPN 类目 AUP 明令禁止) → 追加 Stripe provider(独立 PR)
- 中国码商生态集体崩溃 / 易支付协议变更 → 重新评估通道策略
- 运营方转目标市场(例:转欧洲) → 重新从零设计通道(本决策不再适用)

---

## D-009 | 2026-04-21 | CI 门禁:自研目录扫,upstream 不扫;pip-audit 非阻塞但可视

**决策**: 本项目 CI 的三档硬门禁:

1. `ruff check` + `ruff format --check` **只扫** `hardening/` `deploy/` `ops/` `tests/`。`app/` / `dashboard/` 走 upstream 自己的风格,我们不擅自格式化
2. `pytest` 跑全量 22 个测试,任何 fail 阻塞合并
3. `pip-audit` **step 级** `continue-on-error: true`:job 整体 report 绿,但日志保留发现。继续让 CVE 可见不让它阻塞日常 PR

**Why**:
- 反例:Round 1 第一轮 PR 里 `ruff check .` 扫 upstream 刷出 218 个错误,瞬间不可合。扫自研 = 严格,扫 upstream = churn 战争
- `pip-audit` job 级 `continue-on-error` 会让 PR UI 继续红,对强迫症不友好。step 级 + step 失败等于 `exit 0` job 报绿
- 真的要阻塞 CVE,用 Dependabot / Renovate 自动开 PR,不用门禁打人

**How to apply**:
- 新增自研目录(未来的 `ops/billing/` 等),按相同惯例加到 CI
- upstream 合并后若新增 upstream 代码格式化风格,本项目不强行对齐
- 当下 pip-audit 非阻塞;哪天我们真的要 "新代码禁止引入新 CVE 依赖",单独加一个 job 只扫 diff 的包

**推翻条件**: 我们决定主动接管 `app/` 代码风格(有独立格式化 sweep PR 了),或 CVE 密度突然爆炸需要强门禁。

---

## D-008 | 2026-04-21 | Redis 客户端契约:可选 + lazy + 类型化 disabled

**决策**: `app/cache/redis.py` 的三条硬契约:

1. **可选**:`REDIS_URL` 为空 == 功能禁用。`is_redis_configured()` 返回 False
2. **lazy**:`get_redis()` 首次调用才建连接池,不在 import 时建。startup 不 crash
3. **类型化 disabled**:需要 Redis 的调用方拿到 `RedisDisabled` 异常(dedicated class)而不是 generic `RuntimeError`。调用方按"必需"/"可选"分层选择 fail-loud 或 graceful skip

**Why**:
- 很多 Python 项目的 Redis 客户端 import-time connect → 一处 Redis 下线整个 app 起不来。拒绝这个陷阱
- generic `RuntimeError` 无法让调用方区分"配置没设"和"Redis 挂了"。前者是运维策略决定(刻意禁用),后者是 incident。同名不同因就是 bug magnet
- 配置 Redis 是二阶段:启用 → 提供 URL。两者分离让升级路径平滑

**How to apply**:
- 需要 Redis 的特性(rate limit / 未来的缓存 / session store)**必须** `if not is_redis_configured(): raise FeatureRequiresRedis(...)` 或类似
- 可以降级的特性(opportunistic cache)**必须** `if is_redis_configured(): try_use(...)` 且失败也不影响主路径
- 新增 Redis 消费者时,导入 `from app.cache import get_redis, is_redis_configured, RedisDisabled`

**推翻条件**: 改用别的 KV 存储(比如 etcd)替代 Redis,或产品决定 Redis 从"可选"变"必须"(那时把 `REDIS_URL` 设为必填,删 `RedisDisabled` 代码路径)。

---

## D-007 | 2026-04-21 | compose 可选服务用 profile,upstream-sync 冲突面控制在零

**决策**: PostgreSQL 16 + Redis 7 通过 Docker Compose 的 `profiles: [postgres]` / `profiles: [redis]` 挂在根 `docker-compose.yml`,而不是新开 `docker-compose.prod.yml`。

**Why**:
- upstream `docker-compose.yml` 目前只有 `marzneshin` + `marznode` 两个服务,再加服务的冲突面小到几乎零
- `profiles` 是 Compose 原生机制,没 profile 标志就像服务不存在,零行为变化给 SQLite-only 部署
- 开新 `docker-compose.prod.yml` 会让 "启动命令 + 环境切换" 翻倍,新人容易走错文件

**陷阱**(Round 1 里踩过,经 user 修复):
- Compose 变量展开 (`${VAR:?error}`) 在 **profile 过滤前**发生。对可选 profile 服务的"必需"变量用 `:?err` 会让不启该 profile 的部署直接 parse 失败
- 修法:用 `${VAR:-}` 空默认,运行时启动 postgres 容器自身会因无密码退出,fail 时机正确转移到 startup 而非 parse

**How to apply**:
- 未来新增可选服务(如 `deploy/compose/monitoring.yml` 的 Prometheus + Grafana)继续用 profiles
- 任何 "required env" 检查,用 `:-` + 启动时验证,不用 `:?`
- 文档必须说明:用户启哪个 profile,必须设哪些 env

**推翻条件**: 生产 compose 需要跟开发 compose 本质不同的拓扑(比如生产用 overlay network + external secrets),那时分文件合理。

---

## D-006 | 2026-04-21 | 速率限制契约:opt-in + 失 Redis 即 fail-loud,禁止降级内存

**决策**: `RATE_LIMIT_ENABLED=false` 默认关;开启时 `REDIS_URL` 必须设,否则 **import 时抛 `RateLimitMisconfigured`,panel 拒绝启动**。

**Why**:
- 多 worker 部署下内存计数器让每个 worker 独立限流 = 攻击者直接 scale out 就过,等于没限
- 内存计数器的"看起来有限速"比"明确没有"更糟,是典型**误导性安全**(security theater)
- opt-in 让现有部署升级不吃 429,运维确认 Redis 可达了再翻开关

**How to apply**:
- `/api/admins/token` 已装 `@limiter.limit(ADMIN_LOGIN_LIMIT)`,默认 `5/minute` 按 IP
- 未来装更多 rate limit 的端点(比如 `/api/subscription/*` 防爬),沿用 `hardening/panel/rate_limit.limiter` 单例,别重新建一个 Limiter
- 反代场景下,必须同时配 Uvicorn `--forwarded-allow-ips` 或未来的 `TrustedProxyMiddleware`,否则所有请求看起来同 IP,要么 0 限速要么全 429

**推翻条件**: 未来某端点必须 rate limit 且可接受 per-worker 计数(比如真正本地化的限流),单独实现另一个 Limiter 不走这个单例。

---

## D-005 | 2026-04-21 | Spec-Driven 首次应用:SPEC-postgres-redis.md 作为模板

**决策**: Round 1 的 PostgreSQL + Redis PR 按 CTO handbook §18 先写 `docs/ai-cto/SPEC-postgres-redis.md`,作为未来大功能 PR 的**事实模板**:

- **What**:能做什么 / 不能做什么(scope boundaries 列 ❌ 边界)
- **Why**:引用 VISION / AUDIT / ROADMAP 的具体段落
- **How**:按数据库 / cache / infra / 依赖 / 测试 / 文档六个维度列落地
- **Risks**:风险矩阵 + mitigation
- **Acceptance criteria**:checklist 形式的完成定义

**Why**:
- 第一次用,走通了"写 SPEC → 写 PR 描述 → 写 commit 消息"的三段式,每层都能引用上一层,commit history 自带上下文
- 未来大功能(计费 / SNI 选型 / 健康度仪表盘)都需要这种尺度,现在有模板比临时发明好

**How to apply**:
- 下次 "非 trivial 新功能" PR 前,先在 `docs/ai-cto/SPEC-<kebab-name>.md` 起草,参考 postgres-redis 结构
- SPEC 提交为 PR 的第一个 commit,让后续代码 review 有背景
- SPEC 落地完成后可删(或改为 "ARCHIVED" 标记),路线图上的决策进入 `docs/ai-cto/DECISIONS.md`

**推翻条件**: 小 PR(<100 行 diff 或纯 bug 修复)不强制 SPEC;只有"新增模块/服务/架构决策"级别才走。

---

## D-004 | 2026-04-21 | Round 0 完成,Round 1 聚焦 P0 安全 + 基础测试设施

**决策**: Round 1 **不做新功能**,只做:
1. P0 安全修复(JWT secret 外置 + Admin 速率限制 + CORS 收紧 + JWT 时效收紧)
2. PostgreSQL 切换 + 迁移
3. 测试基础设施(pytest fixture + CI + 至少关键路由端点测试)
4. 目录骨架(`hardening/` + `deploy/` + `ops/` 创建 + README)

**Why**: AUDIT.md 显示安全 3/10、测试 1/10。在这两块没达标前做任何新功能都是在**不可审计的沙滩上盖楼**,每次上线都会带安全债务和回归风险。>200 用户商业场景容不得这种脆弱。

**How to apply**: Round 1 所有任务必须属于以上 4 类。新功能(SNI 选型器、计费等)推到 Round 2+。

**推翻条件**: 用户明确要求优先做 SNI 选型器或计费 demo(商业 deadline 驱动),可调整;但至少 JWT 外置和速率限制这两条必须先做。

---

## D-003 | 2026-04-21 | 商业化机场法律合规 —— 用户已知,CTO 留痕

**决策**: CTO 对用户明确提示了运营付费机场(>200 用户)在中国大陆/伊朗/俄罗斯的刑事风险,用户接受风险并继续。CTO 不再阻止,但在项目多处留下合规警示。

**Why**:
- 2023-2025 年有多起"运营翻墙收费"刑事判例
- CTO 的职责是提示和加固防御,不是代替用户做价值判断
- 留痕后若未来出问题,历史记录清晰

**How to apply**:
- `NOTICE.md` 和 `.agents/rules/security.md` "合规红线"段落已写入
- 建议(非强制):
  - 运营主体 / 支付通道 / 域名 / VPS 账单全部境外化且隔离
  - 中国大陆 IP 黑名单屏蔽
  - 管理面板访问走 CF Tunnel + Access
  - 管理员居住地非高风险司法管辖区
  - 不保留用户真实身份信息;支付走加密货币或境外 SaaS
- 任何涉及"收款"、"实名制"、"电话验证"的功能请求必须再次提醒用户合规风险

**推翻条件**: 用户明确说"只在合规法域运营 + 仅面向持牌用户",此限制可放宽。

---

## D-002 | 2026-04-21 | AGPL-3.0 合规策略 —— 保留版权 + 独立仓库 + 源码披露入口

**决策**: 采用 "hard fork + 独立仓库 + 致谢保留" 策略。

- ✅ `git clone` 上游后 `rm -rf .git && git init` 成为独立仓库,不显示 "forked from"
- ✅ **保留**原版 `LICENSE`(AGPL-3.0)和所有源文件版权头
- ✅ 新增 `NOTICE.md` 致谢 upstream 并标注 fork commit SHA
- ✅ 自研新模块(`hardening/`、`deploy/`、`ops/`)可选独立 license(Apache-2.0 / MIT,与 AGPL 兼容)
- ❌ **禁止**闭源商业化运营;必须对用户提供源码获取入口(面板 footer 或 `/source` 路由)

**Why**:
- 用户希望"不显示 upstream 来源"(不想让其他运营方看到 fork 关系)
- Hard fork + 独立 git init 能满足这个需求(不是 GitHub fork,也不显示 forked 标记)
- **但** AGPL-3.0 不允许隐藏 upstream 版权或不对用户披露源码,这两条必须坚守
- 违反 AGPL 会导致法律风险(强制开源 / 撤销使用权),这是项目生存问题

**How to apply**:
- 所有 commit 中,涉及 upstream 代码的修改必须保留原文件头 Copyright 行
- 上线前必须跑 `.agents/skills/agpl-compliance/SKILL.md` 定义的完整检查
- 面板必须在合理位置(footer、关于页、`/source` API)提供公开的 Git 仓库链接
- 自研模块若要用非 AGPL license,在该模块目录下独立声明 `LICENSE`

**推翻条件**: 只要 upstream license 仍是 AGPL-3.0,不可推翻。若未来 upstream 换 license,重新评估。

---

## D-001 | 2026-04-21 | Fork 基底:Marzneshin(不是 Marzban)

**决策**: 放弃已完成的 Marzban fork(commit `d3cf9fa`,已 `rm -rf .git` 销毁),改从 Marzneshin clone 重做。

**Why**:
- Marzban(Gozargah/Marzban)**最后活跃 2025-01-09**,15 个月无提交,官方团队已迁到 Marzneshin
- Marzneshin 是官方继任,**最近 release v0.7.4 @ 2025-10-02**,仍在活跃维护
- Marzneshin **原生多节点弹性**(control/data plane 分离 + gRPC 到 marznode),与 >200 用户 + 多节点目标完全对齐
- Marzneshin 前端是 **TypeScript + Vite + React + shadcn/ui**(比 Marzban 的 Vue2 现代);有 tests/ 骨架
- 代价:Marzban 生态的 V2IpLimit / luIP / miplimiter 等 IP 限制外挂**不兼容 Marzneshin**,我们需要改造或自研(详见 COMPETITORS.md 建议 3)

**How to apply**:
- 所有以后对"上游"的引用默认指 Marzneshin
- 不要 copy-paste Marzban 的 issue/PR 讨论作为 Marzneshin 的指导
- 季度性评估 `marzneshin/marzneshin` upstream 变更,策略性同步(不盲合)

**推翻条件**:
- Marzneshin 停更超过 12 个月 → 评估再 fork 或换基底
- 出现更优秀的活跃替代品(如 Remnawave 进入多节点阶段且生态起来)→ 重新评估

---

## 模板(新决策按此格式追加到顶部)

```
## D-NNN | YYYY-MM-DD | <一句话决策>

**决策**: <详细描述>

**Why**: <为什么这样选,而不是其他方案>

**How to apply**: <具体如何落地,哪些文件/流程受影响>

**推翻条件**: <什么情况下这条决策失效,要重新讨论>

---
```
