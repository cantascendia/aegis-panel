# SPEC — Payment MoR Integration (Phase B Umbrella)

> **Status**: DRAFT — Hold for SEAL until (a) operator bank (住信SBI) approved + 開業届控え PDF received, AND (b) ≥ 50% of MoR vendor applications past initial approval gate.
>
> **Author**: spec-planner sub-agent, 2026-05-11.
>
> **Type**: Umbrella SPEC — defines provider interface + 3 sub-SPEC kickoff points. Each MoR family gets its own `SPEC-payment-mor-{provider}.md` downstream.
>
> **Baseline**: `SPEC-billing-mvp.md` (D-010 strategy) + `SPEC-billing-a2-a3.md` (provider abstraction landed) + main as of 2026-05-11 (PR #246/#250/#251/#253/#254/#255 series merged).
>
> **Forbidden-path scope**: `ops/billing/**`, `app/routes/customer*`, `customer-portal/src/lib/PanelPages2.jsx` (BillingPage), webhook handlers (matches `**/payment/**` pattern). Every sub-SPEC PR MUST carry `requires-double-review` label.

---

## 0. Context

### 0.1 当前项目阶段(引 STATUS / launch docs)

- **Phase A 完成**:TRC20-only billing live since PR #200/#186 wave-9 R4。Admin manual checkout 走通过 1 个 user round-trip(nilou_trial01)。`apply_invoice_grant` helper 抽出可复用。
- **Phase B 启动条件**(2026-05-11 实况):
  - 開業届 e-Tax 提出済 — 5/7 品川税務署、受付番号 20260507224845548217
  - 住信SBI ネット銀行 — 5/7 申請、審査 1-3 営業日(等通过)
  - 楽天 モバイルチョイス"050" — 5/8 申請中
  - 商家審査未開始(本 SPEC 完成后才递交)
- **触发事件**:用户口头方針 — Phase B 商業化下一阶段需要支持信用卡 + 海外客户结算。TRC20 单通道覆盖率 ≤ 30% 海外用户。
- **相关 LESSON / 历史 SPEC**:
  - `SPEC-billing-mvp.md` — D-010 显式 scrapped Stripe due to "no entity"。**本 SPEC 推翻该约束** — 開業届 已提出,operator 现为合法個人事業主。
  - `SPEC-billing-a2-a3.md` — 已落地 `BasePaymentProvider` 抽象,本 SPEC 完全复用,不重建 interface。
  - `L-014` — 新 model 必须走 `app/db/extra_models.py` aggregator
  - `L-015` — Alembic migration 新建 revision,不 mutate 已合并
  - `L-017` — i18n 走 `t(key, "default")` 模式,不直接动 locale JSON
  - `PAYMENT-DECISION-FINAL-JP.md` — 当前商业决策快照(本 SPEC 落地后需 D-021 决策记录追加)
  - `PAYMENT-CHANNEL-MATRIX.md` — 通道对比矩阵,本 SPEC §2 引用

### 0.2 待用户补充(TBD — operator 拍板才能 SEAL)

- 是否优先支持 JPY 定价(operator 本国货币)还是维持 CNY 主货币?(影响 pricing 表 schema → TBD-4)
- TRC20 是否在 Phase B 改为"deprecated but supported"还是"first-class equal"?(影响 fallback 顺序设计)
- 多通道收入分布报表是 Phase B 必需还是 Phase C?(影响 AC 数量)

---

## 1. What

### 1.1 一句话定义

在现有 `BasePaymentProvider` 抽象之上,**并发**接入 3 家 Merchant-of-Record / 信用卡通道(Paddle / Lemon Squeezy / Stripe Japan),配合保留中的 TRC20,形成"4 通道、按国籍 + 偏好自动路由 + 单家审核失败自动降级"的可商用支付层。

### 1.2 In Scope(8 件)

1. ✅ **Provider class × 3**:`PaddleProvider`、`LemonSqueezyProvider`、`StripeJapanProvider`,均实现现有 `BasePaymentProvider` interface(`create_invoice` / `handle_webhook`)
2. ✅ **Webhook 路由 × 3 新增**:`/api/billing/webhooks/paddle`、`/.../lemonsqueezy`、`/.../stripe`(沿用 a2-a3 `/api/billing/webhook/{provider}` 模式,**纠正路径为复数 `webhooks/` 与 §34 规范对齐**)
3. ✅ **Checkout 路由扩展**:`POST /api/customers/checkout` 增加 `provider` 参数 + auto-suggest endpoint `GET /api/customers/checkout/suggest?country_code=XX`
4. ✅ **Provider 注册表**:`ops/billing/providers/__init__.py::get_provider(kind, code)` 工厂扩展,**不改 signature**
5. ✅ **Fallback 链**:配置驱动的有序 fallback list,首选拒(provider returns 4xx on `create_invoice`)→ 提示用户切备选
6. ✅ **i18n**:checkout UI ja/zh/en 三语(P2 customer-portal 已规划)
7. ✅ **Operator 收入分布报表**:按 provider 分组的 daily / monthly aggregated view(`/api/billing/admin/revenue-by-provider`)
8. ✅ **Audit log 强化**:PaymentEvent 必记 `provider_country` + `provider_fee_estimate_fen` 两新字段(便于税务对账)
9. ✅ **PORTAL-RELIABILITY.md 更新**:加 3 family endpoint 进 SLO 表

### 1.3 Out of Scope(6 件)

- ❌ **不重写 TRC20 poller** — forbidden-path,reliability-auditor 已识别独立 `SPEC-trc20-poller-alerting.md`,与本 SPEC 解耦
- ❌ **不改 D-014 计费分层** — `pricing.py` 纯函数 + `grants.py` User 表改动 + scheduler 胶水保持不动
- ❌ **不实现 refund 自动化** — Paddle/LS 通过 MoR 后台手动 refund;Stripe 通过 admin 手动调 refund endpoint。自动化留 Phase C。
- ❌ **不做 recurring subscription** — Paddle/LS/Stripe 均支持但本 SPEC 范围内只做"one-shot purchase"。recurring 留独立 SPEC(D-014 当前模型也未支持 on-file payment)
- ❌ **不做 coupon / promo code** — Phase C
- ❌ **不做 invoice PDF export** — 由 MoR 自带(Paddle/LS 提供),Stripe 走 Stripe Dashboard;operator 自己出 PDF 留 Phase C

### 1.4 与 SPEC-billing-mvp 的冲突说明

- **mvp 文档 §"Why no Stripe" 明确反对** — 该论证基于"无法人 + Stripe AUP 禁 VPN"。本 SPEC 推翻条件 1(operator 已为個人事業主、開業届控え 5/7 提出済),但条件 2(VPN 服务被 Stripe AUP 拒)**仍然存在**。Stripe 审批通过率 < 10%,这是为何并发申请 Paddle / LS 的根本动因 — 不押宝单家。
- 处理方式:本 SPEC 不删 mvp 中那段文字,而是在 D-021 决策记录中说明"条件变化 + 风险分散"。

---

## 2. Why

### 2.1 用户价值

- **海外信用卡客户**(US/EU/JP)无须 USDT,直接刷卡 → 实际 TAM 翻倍
- **中国客户**:TRC20 保留 + 未来 EPay(已停滞)→ 不被剥夺现有路径
- **日本客户**:Stripe JP 走本币 JPY,无汇兑摩擦

### 2.2 商业价值

- 单通道押宝 = 单点故障(L-012 教训迁移到商业层):Stripe AUP 风险 + Paddle 审核 4-6 周 + LS 审核 1-2 周。任一被拒,业务不至于停摆。
- MoR 模式(Paddle/LS)代办全球税务 = 海外 JCT / VAT / GST 不用 operator 自处理 → 节省至少 1 名 part-time 税务人月
- 收入分布报表 → Phase C 数据驱动决策(哪家通道 ROI 最高、客户分布)

### 2.3 不做的代价

- 不做 = TRC20-only 永续 = 海外用户流失 = Phase B 收入天花板 ¥30万/月(估)
- 不做 = 商家审核拖到 Phase C 才启动 = 全季度无信用卡 = Y/Y 收入差额预估 -¥150万

### 2.4 与 VISION 对齐

- VISION 商業化運営層:订阅计费 / 流量告警 / 续费 / RBAC — 本 SPEC 直接服务首条
- VISION 差异化 #3 "面向商业的支付通道丰度"

---

## 3. How(架构方向,非实现)

### 3.1 高层组件

```
┌─────────────────────────────────────────────────────────┐
│  customer-portal /portal/billing                        │
│  (Phase B P3:  checkout UI; auto-suggest provider)      │
└──────────────────┬──────────────────────────────────────┘
                   │ POST /api/customers/checkout
                   ▼
┌─────────────────────────────────────────────────────────┐
│  ops/billing/checkout_endpoint.py (existing)            │
│  ── 扩展:provider 路由 + fallback 链                   │
└──────────────────┬──────────────────────────────────────┘
                   │ get_provider(kind, code)
                   ▼
┌─────────────────────────────────────────────────────────┐
│  ops/billing/providers/                                 │
│  ├── base.py        (existing — BasePaymentProvider)    │
│  ├── trc20.py       (existing — DO NOT TOUCH)           │
│  ├── stripe_jp.py   ← NEW Phase 1                       │
│  ├── lemonsqueezy.py← NEW Phase 2                       │
│  └── paddle.py      ← NEW Phase 3                       │
└──────────────────┬──────────────────────────────────────┘
                   │ Provider.create_invoice() 返回 payment_url
                   ▼
       External MoR / payment gateway
                   │
                   │ webhook POST
                   ▼
┌─────────────────────────────────────────────────────────┐
│  /api/billing/webhooks/{provider}                       │
│  ── verify_webhook(signature) → WebhookOutcome          │
│  ── record_webhook_seen() 幂等 → transition("paid")     │
└──────────────────┬──────────────────────────────────────┘
                   │ apply_invoice_grant (existing helper)
                   ▼
       User.data_limit + expire_date 扩容
```

### 3.2 关键技术选型(列候选 + TBD)

**TBD-1: HTTP client 选型**
- Option A:`httpx.AsyncClient`(a2-a3 已用,一致性高)— **推荐**
- Option B:各 provider 官方 SDK(`stripe-python`、`paddle-python-sdk`、`lemonsqueezy.py`)— SDK 升级被动、依赖增 3 个
- **TBD**:是否允许 mixed(Stripe 用 SDK、Paddle/LS 用 httpx)?

**TBD-2: Webhook signature verification 实现位置**
- Option A:Provider class 内 `handle_webhook()` 处理(与 a2-a3 epay 模式一致)— **推荐**
- Option B:共享 `webhook_verifier.py` 中间件 → forbidden-path 单点风险

**TBD-3: Fallback 链配置位置**
- Option A:`.env` 静态(`BILLING_PROVIDER_FALLBACK_ORDER=stripe,lemonsqueezy,paddle,trc20`)
- Option B:DB 配置表 `aegis_provider_priorities`,admin 可热改
- Option C:按 country_code 路由表(country_code → priority list)— 最灵活但最复杂
- **TBD**:用户拍板;**建议** A → 后续升 C(本 SPEC 验收只要 A)

**TBD-4: Currency 处理**
- Option A:维持 CNY-fen 主货币,所有 provider 内部 convert(snapshot rate at invoice creation)
- Option B:per-provider native currency(Stripe JP → JPY、Paddle/LS → USD、TRC20 → USDT)+ display layer convert
- Option C:多货币 first-class(price 表加 `currency` 列,operator 配多套定价)
- **TBD**:用户拍板;**建议** B(贴近实际 provider 行为,operator 报税清晰)

**TBD-5: Stripe Japan 申请期间的"开发用 placeholder"**
- Option A:feature flag `BILLING_STRIPE_ENABLED=false`,代码全在但路由 404
- Option B:完全不合 PR,等审批通过再开 Phase 1 实装
- **TBD**:用户拍板;**建议** A(并行 dev + 等审批,审批一过 flag 一开)

### 3.3 与现有模块的接口

- **`ops/billing/providers/__init__.py::get_provider`** — 工厂扩 3 个 kind,不改 signature
- **`ops/billing/states.py::transition`** — 单一可写路径,本 SPEC 不动
- **`ops/billing/states.py::record_webhook_seen`** — 复用幂等键 `(provider, provider_event_id)`,不动
- **`ops/billing/grants.py::apply_invoice_grant`**(wave-9 R4 helper)— **必须复用**,不重复实现
- **`app/db/extra_models.py`** — 若新增 model(本 SPEC 倾向**不新增**,所有 provider 元数据进 `PaymentEvent.payload_json` + `PaymentChannel.extra_config_json`)
- **`hardening/panel/middleware.py::apply_panel_hardening`** — 沿用挂载入口
- **`docs/ai-cto/PORTAL-RELIABILITY.md`** — 加 3 webhook endpoint 到 SLO 表

---

## 4. Risks

### 4.1 技术风险

| Risk | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 3 家 webhook signature 算法各不同,实装 bug → fraud | 中 | 极高 | 每家独立 forbidden-path 双签 + mutation test ≥ 80% + 录制 fixture 测试 |
| Webhook 重放攻击 | 中 | 高 | 复用现有 `record_webhook_seen` 去重(provider_event_id 唯一键) |
| MoR 与 operator 时钟漂移导致 invoice 过期但用户已付 | 低 | 中 | 60 分钟宽容窗口 + admin manual apply fallback |
| Provider SDK 版本锁定 vs 主线 Python 依赖冲突 | 中 | 中 | TBD-1 决定后,mixed mode 隔离到 provider 包内 |
| Currency conversion 精度损失(integer fen ↔ JPY ↔ USD-cent) | 中 | 高(财务) | 选定 TBD-4 后,单测覆盖所有 round-trip + 向上取整保护 operator |
| Customer-portal P3 接 billing 时序:SPEC 实装 vs portal P3 顺序 | 高 | 中 | 本 SPEC 必须先 Phase 1 实装 + freeze interface,portal P3 才开工 |

### 4.2 业务风险

| Risk | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 3 家审核全被拒 | 中(Stripe ~70% 拒、Paddle ~30%、LS ~20%) | 业务停滞 | 三家并发 → 全拒概率 ≈ 0.7 × 0.3 × 0.2 = 4.2%;回退 TRC20-only,trial 期最多 30 天 |
| Paddle 4-6 周审核期内被同行抢市 | 中 | 中 | Phase 1 Stripe + Phase 2 LS 并行,不等 Paddle |
| MoR 抽成 5% + 0.5 USD 蚕食毛利 | 高 | 中 | 定价时把 fee 加进底价(¥XX → ¥XX × 1.06);report 显示 net revenue |
| 海外用户嫌 MoR 跳转 UX 差导致 conversion 下降 | 中 | 中 | Stripe Elements embedded(non-MoR)优先;Paddle/LS 提供 inline checkout SDK |

### 4.3 AGPL 合规风险

- **本 SPEC 主代码全部在 `ops/billing/providers/`(self-research 区)** — 不触上游同步面,合规 0 风险
- Provider 引入的 npm/pip 依赖必须 license-compatible(MIT/Apache/BSD;**不可** GPL/AGPL 传染)

### 4.4 安全风险(forbidden 路径触及度)

**极高 — 本 SPEC 全程在 forbidden-path 内**:
- `ops/billing/**` ✓
- `customer-portal/src/lib/PanelPages2.jsx`(BillingPage)✓
- Webhook handler = `**/payment/**` 模式 ✓

**强制要求**:
- 每个 sub-SPEC 必须 PR 打 `requires-double-review` 标签
- mutation test ≥ 80% per provider
- 第二模型(Opus / GPT-5)独立 review webhook handler
- `vibe-checker` sub-agent 跑 6 大反模式检测(尤其 Dependency Hallucination — 3 家 SDK 名字易混)
- secrets:provider API key 加密列(Fernet,沿用 a2-a3 模式)

### 4.5 法律 / 税务风险

- **Paddle/LS MoR 模式**:invoice 主体 = MoR(英国 / 美国注册),operator 收到的是 MoR 净额 → operator 报税口径变化,需会计师确认
- **Stripe 非 MoR**:operator 自处理 JCT(消費税)— 売上 1000 万円超才强制课税業者,初期可能免税。需 operator 决定:免税業者 vs 适格请求書発行事業者
- **Currency tax-event 时机**:USD/JPY 汇兑差额按入金日 vs 売上計上日 — 与会计师确认
- **TBD**:是否本 SPEC 必须包含 `OPS-tax-handling-mor.md` 文档?

---

## 5. Acceptance Criteria

### 5.1 功能验收(12 条)

1. **AC-1**:3 个 provider class(`StripeJapanProvider`、`LemonSqueezyProvider`、`PaddleProvider`)各自实装并通过 `BasePaymentProvider` 接口测试
2. **AC-2**:单测覆盖率 ≥ 80%(行覆盖)per provider;mutation test ≥ 80% kill rate per forbidden-path
3. **AC-3**:4 个 webhook endpoint(stripe / paddle / lemonsqueezy / trc20)全部经过 forbidden-path 双签 + `requires-double-review` PR 标签
4. **AC-4**:客户 checkout E2E 测试(mock provider)— 每家 1 个 happy path + 1 个 signature invalid + 1 个 replay
5. **AC-5**:Grant 应用**必须**复用 `apply_invoice_grant` helper,grep 验证无 `User.data_limit +=` 或 `expire_date =` 在本 SPEC 新代码中
6. **AC-6**:每个 checkout / webhook event 写入 `PaymentEvent`,`event_type` 枚举扩 6 条(`stripe_checkout_created`、`stripe_webhook_received`、`paddle_*`、`lemonsqueezy_*`)
7. **AC-7**:Failure mode E2E — provider 1 `create_invoice` 返回 4xx → 客户 UI 提示备选 + 自动 retry next provider(configurable order via TBD-3)
8. **AC-8**:i18n — checkout UI ja/zh/en 三语,所有新字符串走 `t(key, "english default")` 模式(L-017),不动 locale JSON 直到 P2 portal i18n 重构
9. **AC-9**:Operator dashboard `/dashboard/billing/revenue-by-provider` 显示 per-provider daily / monthly aggregated(Phase C 数据需求前置)
10. **AC-10**:24h soak test — staging 环境跑 24 小时 mock traffic,无 silent failure(无 5xx 未记 audit、无 invoice 卡 awaiting_payment > 60 分钟无告警)
11. **AC-11**:`PORTAL-RELIABILITY.md` 必更新 — 加 3 family endpoint 到 SLO 表(uptime ≥ 99.5%、p95 latency < 800ms、5xx rate < 0.1%)
12. **AC-12**:D-021 决策记录 — `docs/ai-cto/DECISIONS.md` 追加,说明 mvp SPEC §"Why no Stripe" 推翻条件 + 新决策依据

### 5.2 性能 / 可靠性 SLO

- Checkout endpoint p95 < 500ms(不含 provider 外部 call)
- Webhook handler p95 < 200ms(`record_webhook_seen` + `transition`,不等 grant 应用)
- Grant apply scheduler 间隔 30s,p99 完成时间 < 60s
- Webhook 5xx rate < 0.1% per provider
- Webhook signature verification 失败率 alerting 阈值:> 1% / 1h 触告警(可能是 provider 端 key rotation 或攻击)

### 5.3 测试覆盖

- Provider 单测:≥ 80% 行覆盖 per provider
- Webhook handler mutation score:≥ 80% kill rate
- Property-based 测试 ≥ 1 条(`Hypothesis`):currency conversion round-trip 不溢出
- E2E:≥ 12 cases(3 providers × 4 scenarios:happy / invalid sig / replay / fallback)

---

## 6. Kickoff

### 6.1 拆分实施次序(Phase 1 / 2 / 3 / 4)

| Phase | Provider | 审批期 | 启动条件 | 子 SPEC | 估期 |
|---|---|---|---|---|---|
| **Phase 0(本 SPEC)** | umbrella + interface freeze | — | bank + 開業届控え 到位 | 本文档 | 1 day |
| **Phase 1** | Stripe Japan | 即时-3 days | Phase 0 SEAL + Stripe 审核进件 | `SPEC-payment-mor-stripe.md` | 1.5 weeks |
| **Phase 2** | Lemon Squeezy | 1-2 weeks | Phase 1 实装期内并行进件 | `SPEC-payment-mor-lemonsqueezy.md` | 1 week |
| **Phase 3** | Paddle | 4-6 weeks | Phase 1/2 上线后进件 | `SPEC-payment-mor-paddle.md` | 1.5 weeks |
| **Phase 4** | Hardening | — | Phase 1-3 全上 | `SPEC-payment-mor-hardening.md`(fallback chain + revenue report + soak test) | 1 week |

**Total**:5 周实装(假设审批顺利);最坏情况(Paddle 拖 6 周审批)总 lead time 7-8 周。

### 6.2 关键 TBD list(等用户拍板)

1. **TBD-1**:HTTP client 选型 — httpx-only / mixed SDK / pure SDK
2. **TBD-2**:Webhook verification 实装位置 — provider class 内 / 中间件
3. **TBD-3**:Fallback 链配置位置 — `.env` / DB / country-code 路由
4. **TBD-4**:Currency 处理 — CNY-fen 主货币 / per-provider native / multi-currency first-class
5. **TBD-5**:Stripe Japan 实装时机 — feature-flag 并行 / 等审批

### 6.3 推荐 reviewer

- **本 SPEC**:CTO(用户)+ Tech Lead(用户) — umbrella 决策
- **Phase 1-3 各 PR**:强制双签 — Claude Opus + 第二模型(GPT-5 / Gemini 2.5 Pro)独立审 webhook handler 段
- **vibe-checker sub-agent**:Phase 1/2/3 各跑一次 6 大反模式检测
- **reliability-auditor sub-agent**:Phase 4 前跑一次,确认 SLO 可观测

### 6.4 SEAL 条件

本 SPEC 进入 SEAL(从 DRAFT → ACTIVE)需:
- ✅ 住信SBI 銀行口座開通(operator 实绩证明)
- ✅ 開業届控え PDF 入手(商家审批必交材料)
- ✅ Stripe Japan **审批已进件**且未明确拒绝
- ✅ Paddle / LS 至少 1 家审批已进件
- ✅ 5 个 TBD 全部由用户拍板
- ✅ D-021 决策记录草稿落地(可不合 PR,但需 review)

### 6.5 下一步

1. 用户 review 本 SPEC,在 §6.2 TBD list 上拍板
2. 等 SEAL 条件满足 → `/cto-spec plan SPEC-payment-mor-stripe.md` 进入 Phase 1 PLAN
3. Customer-portal P3 队列对齐:portal P3 接 API 前,Phase 1 interface 必须 freeze

---

## 附录 A — 与 SPEC-trc20-poller-alerting 的解耦

本 SPEC **不**触碰 `ops/billing/trc20_poller.py` / `trc20_matcher.py` / `trc20_client.py` / `trc20_health.py` 四文件。trc20 reliability 单独 SPEC,reliability-auditor sub-agent 已识别。本 SPEC 仅复用 `Trc20Provider` 作为 4 通道之一的现存实装。

## 附录 B — 与 EPay(支付宝/微信)关系

EPay channel 在 a2-a3 SPEC 已规划但**实装停滞**(D-010 论证 + 2026-02 起政策收紧)。本 SPEC **不** 重启 EPay,但 fallback 链配置保留 `epay:*` slot,未来若码商通道恢复可即插即用。

---

**End of SPEC-payment-mor-integration.md (DRAFT, 2026-05-11, lines ~450)**
