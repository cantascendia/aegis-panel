# ops/billing/ — 商业化计费层

**状态**: 🔄 建设中(Round 2 path A)

**定位**: 为 Aegis Panel 添加一个完整的自助计费栈:套餐配置 → 购物车 → 支付 → 激活 → 续费提醒 → 过期执行。面向"无实体、无启动资金、中国用户为主"的运营者。

## 方案

**双通道**(见 `docs/ai-cto/SPEC-billing-mvp.md` 与 `docs/ai-cto/DECISIONS.md#D-010`):

| 通道 | 面向 | 现实 |
|---|---|---|
| **易支付(EPay)** — 主通道 | 70%+ 中国普通用户 | 对接第三方 码商 聚合网关;管理员后台配置 `merchant_id`/`merchant_key`/`gateway_url` |
| **USDT TRC20** — 副通道 | 20% 技术型用户 + 主通道失效保险 | 自建 Tronscan 轮询,零第三方依赖 |

**明确不做**:
- ❌ Stripe(无实体 → 永不可启用,stub 代码只会腐烂)
- ❌ NOWPayments / Oxapay(仍需 KYC 捆身份)
- ❌ 退款自动化 / Coupons / 循环订阅(v0.3+)

## 已落地(A.1.1 — 本 PR)

- `db.py` — 5 张 SQLAlchemy 2.0 typed 模型:
  - `Plan` — 套餐(fixed / flexible_traffic / flexible_duration)
  - `PaymentChannel` — 码商配置(运行时增删,不需重启)
  - `Invoice` — 订单 + 状态机字段 + 服务商对应字段
  - `InvoiceLine` — 购物车明细
  - `PaymentEvent` — 审计日志(append-only)
- Alembic 迁移(单次,双 DB 兼容 SQLite + PG 16)
- `env.py` 注册(LESSONS L-014 硬规矩)

## 待落地

| 子 PR | 内容 | 预计 |
|---|---|---|
| A.1.2 | `pricing.py` + `states.py` + 单测(购物车计算、状态机迁移、幂等) | 2-3 天 |
| A.1.3 | 管理员 REST 端点(plan/channel CRUD, invoice 列表/手工激活) | 2-3 天 |
| A.1.4 | 管理员 Dashboard 页面(plan CRUD + 通道配置 + invoice 对账) | 2-3 天 |
| A.2 | EPay provider + webhook + 签名验证 | 1 周 |
| A.3 | TRC20 provider + Tronscan 轮询 + memo 匹配 | 1 周 |
| A.4 | 用户购买 UI(双通道 tab + i18n 8 语言) | 1 周 |
| A.5 | APScheduler 续费提醒 + 过期执行 | 0.5 周 |

## 目录约定(与 `hardening/sni/` 一致)

- `ops/billing/__init__.py` — 显式公共 API(当前为空)
- `ops/billing/db.py` — 所有 SQLAlchemy 模型
- `ops/billing/pricing.py` — 纯函数购物车计算(A.1.2)
- `ops/billing/states.py` — 状态机迁移逻辑(A.1.2)
- `ops/billing/endpoint.py` — FastAPI router(A.1.3)
- `ops/billing/scheduler.py` — APScheduler 任务注册 + `start_billing_scheduler(app)`(A.5)
- `ops/billing/tasks/` — 每任务独立文件(A.5)
- `ops/billing/providers/` — `base.py` + `epay.py` + `trc20.py`(A.2 / A.3)

## upstream 冲突面

与 `hardening/sni` 一致:
- 仅在 `hardening/panel/middleware.py::apply_panel_hardening` 加 **一行** `app.include_router(ops.billing.endpoint.router)` + **一行** `start_billing_scheduler(app)`
- 不修改任何 `app/routes/*.py` / `app/tasks/*.py` / `app/models/*.py`
- 对 `app/db/migrations/env.py` 追加一行 `import ops.billing.db  # noqa: F401`(L-014)

## 相关

- SPEC: [docs/ai-cto/SPEC-billing-mvp.md](../../docs/ai-cto/SPEC-billing-mvp.md)
- 决策:[docs/ai-cto/DECISIONS.md](../../docs/ai-cto/DECISIONS.md) D-010
- 码商选择: [docs/ai-cto/OPS-epay-vendor-guide.md](../../docs/ai-cto/OPS-epay-vendor-guide.md)
- JPY 换汇: [docs/ai-cto/OPS-jpy-cashout.md](../../docs/ai-cto/OPS-jpy-cashout.md)
