# SPEC — Billing MVP (Round 2 path A)

> Round 2 v0.2 closing — per `docs/ai-cto/ROADMAP.md` and
> `docs/ai-cto/VISION.md` row "商业化运营层".
>
> Status: draft → implementation in the `ops/billing/` branch series
> that follows. This PR only introduces the spec.
>
> Template: follows D-005 Spec-Driven shape.
> See D-010 (appended with this PR) for the payment-strategy
> decision rationale.

---

## What

A self-service billing stack for an operator with **zero company
entity, zero startup capital, Chinese-majority user base**. Two
payment channels share one invoice state machine:

1. **易支付 (EPay) protocol** — **primary** user-facing channel.
   Takes 支付宝 / 微信 scan payments via third-party 码商 aggregator
   gateways. The panel implements the protocol adapter; the operator
   plugs in whichever 码商 they contract with. 70%+ of the target
   Chinese user base cannot realistically hold USDT; this channel is
   non-optional for the market.
2. **USDT TRC20 (自建轮询)** — **secondary** channel for users who
   have USDT + insurance against 码商 freezes. Zero third-party
   dependency: the operator publishes a wallet address, the panel
   polls Tronscan's free API on a per-invoice schedule and matches
   incoming txs by `(address, amount ± tolerance, unique memo)`.

A `BasePaymentProvider` abstraction keeps both behind the same
invoice / cart / REST surface. Future providers (BTCPay Server,
NOWPayments, Stripe Japan) plug in without touching state machine
or UI.

### User journey

1. Operator logs into admin panel, creates plans:
   - **Fixed**: "Starter 30GB/30d ¥35", "Pro 100GB/30d ¥88", etc.
   - **Flexible addon**: "Extra traffic ¥0.5/GB", "Extra days ¥1/day"
2. End user visits `/dashboard/billing`, picks Pro + adds 20 GB
   extra → cart totals ¥98.
3. User clicks Checkout. Two buttons appear: **支付宝/微信 (易支付)**
   and **USDT TRC20**. Defaults to 易支付 since most Chinese users
   land there. USDT is a second tab, not hidden.
4a. 易支付 path: user is redirected to 码商 gateway, pays via
    扫码 in 支付宝/微信, lands back on `/billing/success`. Webhook
    lands on our `/api/billing/webhook/epay/{merchant_code}`,
    HMAC-verified, invoice state → `paid`.
4b. USDT path: user stays in the dashboard, sees QR + wallet
    address + exact USDT amount + 30-min countdown. Backend
    polling task detects matched tx, invoice → `paid`.
5. Either way: `apply_paid_invoices` APScheduler task (every 30s)
   picks up `paid` invoices, extends `expire_date` and
   `data_limit`, writes audit row, sends Telegram+email, flips
   state to `applied`. User sees "✓ Activated" in real time.
6. 7 days before expire → Telegram reminder. At expiry →
   auto-disable + "expired" notification.

**Scope boundaries (MVP)**:

- ✅ 易支付 protocol generic adapter (works with any 码商 implementing
  the de-facto spec — the same one SSPanel/Xboard/v2board use). Admin
  configures `merchant_id` + `merchant_key` + `gateway_url` per
  provider; multiple providers can be active simultaneously for
  redundancy (failover if primary 码商 goes down).
- ✅ USDT TRC20 self-polling via Tronscan public API (no API key
  needed). Match by `(address, amount ± $0.01, unique memo within
  payment window)`. Wait 3 confirmations before applying grant.
- ✅ Mixed plan model (Fixed + Flexible addon), cart combines.
- ✅ Full i18n 8 languages, en + zh-cn canonical. Plan names
  operator-configurable per-locale.
- ✅ PG 16 + SQLite dual CI (PR #23 infrastructure).
- ✅ `BasePaymentProvider` abstraction — 1 provider = 1 file in
  `ops/billing/providers/`, plug-and-play.
- ✅ Admin dashboard: plan CRUD, invoice list with state filter,
  manual-apply button for emergency / VIP cases.
- ❌ **No Stripe integration** (the earlier SPEC draft planned a
  stub; scrapped because without a Japanese legal entity it's pure
  vaporware — zero path to ever enable it. If the operator ever
  registers an entity, that's a dedicated PR, not a deferred stub
  rotting in the repo).
- ❌ No refund flow — manual out-of-band (admin UI "credit user"
  button is v0.3).
- ❌ No recurring subscription (on-file payment). Every renewal is
  an explicit purchase.
- ❌ No coupon / promo code system.
- ❌ No multi-fiat display. Prices stored + shown in CNY (primary
  market) with USD equivalent in tooltip. USDT channel converts
  CNY → USDT at current rate at invoice-create time (20-min lock).
- ❌ No BTC / USDT ERC20 / other chains in MVP — TRC20 only. Second
  chain lands v0.3 once operator has real volume to justify the
  extra polling + matching code.

## Why

Quoting `VISION.md`:

> **商业化运营层** ⏳ 待建(差异化 #2) — 订阅计费 / 流量告警 /
> 到期续费 / 管理员 RBAC

Quoting `AUDIT.md` finding ⑦-1 (still unresolved on main):

> 🔴 **缺计费系统** | 代码库无 pricing 相关表/逻辑 | 订阅模式、续费、
> 价格等完全缺失 | 无法变现 >200 用户,商业模式为零

This is the last AUDIT P0 item still not addressed on main. Every
prior Round 1/2 PR made the panel *safe* to run a paid airport on;
this PR series makes it *actually take money*.

### Why 易支付 is non-negotiable for this operator profile

(See D-010 appended with this PR for the full decision record.)

- 70-75% of the Chinese end-user base cannot realistically hold
  USDT: after China's "924 通知" (Sept 2021), mainland fiat
  on-ramps to crypto closed; remaining paths (Binance P2P / Huobi
  OTC) require offshore phones + offshore email + risky P2P
  bank-card transfers. Mainstream users quit before completing.
- 易支付 is the de-facto standard across the Chinese airport
  market — all major open-source panels (SSPanel, Xboard, v2board)
  ship it, and every 码商 aggregator implements the same protocol.
  One adapter = compatibility with dozens of 码商, pluggable.
- Without 易支付, the operator loses majority potential revenue.
  This is a factual constraint, not a preference.

### Why no Stripe in scope

- Stripe Japan requires Japanese legal entity (株式会社/合同会社).
  Operator has no entity and no capital to register one.
- Stripe's Acceptable Use Policy explicitly bans VPN/proxy
  services. Even with a Japanese entity, approval is <10% and any
  user complaint freezes the account (180-day freeze period).
- Writing a disabled stub "for future" is net-negative: it makes
  the codebase look like Stripe is a near option when it isn't,
  invites well-meaning commits, and rots while waiting for
  prerequisites that may never arrive. If an entity happens later,
  a dedicated 1-PR Stripe add-on is cleaner than a 6-month-old stub.

## How

### Directory layout

```
ops/billing/                            # new self-research top-level
├── __init__.py
├── README.md                           # operator-facing
├── db.py                               # SQLAlchemy 2.0 typed models
├── pricing.py                          # pure-function cart math
├── states.py                           # invoice state machine enum + transitions
├── endpoint.py                         # FastAPI routers (user/admin/webhook)
├── scheduler.py                        # start_billing_scheduler(app) + tasks
├── tasks/
│   ├── apply_paid.py                   # paid -> applied
│   ├── reap_expired.py                 # pending/awaiting_payment -> expired
│   ├── renewal_reminder.py             # 7d-before-expire → notify
│   ├── expiry_enforcer.py              # expire_date passed → disable user
│   └── trc20_poller.py                 # TRC20-specific tx matching task
└── providers/
    ├── __init__.py
    ├── base.py                         # BasePaymentProvider abstract
    ├── epay.py                         # 易支付 protocol adapter
    └── trc20.py                        # Tronscan polling provider

alembic/versions/<date>_billing_mvp.py  # single migration for 4 tables + indexes

dashboard/src/modules/billing/          # frontend module, mirror modules/nodes
├── api/
├── pages/BillingHomePage.tsx
├── pages/InvoiceDetailPage.tsx
├── pages/admin/PlansAdminPage.tsx
├── pages/admin/InvoicesAdminPage.tsx
└── components/
    ├── PlanCard.tsx
    ├── AddonCalculator.tsx
    ├── CartSummary.tsx
    ├── CheckoutPaymentPicker.tsx      # tabs: 易支付 / USDT
    ├── Trc20PaymentScreen.tsx         # QR + address + countdown + status poller
    └── InvoiceStatusBadge.tsx
```

### Data model (`ops/billing/db.py`)

4 tables, SQLAlchemy 2.0 typed mappings, single Alembic migration
that runs on both SQLite + PostgreSQL 16:

```python
class Plan(Base):
    __tablename__ = "aegis_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    operator_code: Mapped[str] = mapped_column(String(64), unique=True)
    display_name_en: Mapped[str] = mapped_column(String(128))
    display_name_i18n: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"zh-cn": "入门版", "ja": "スターター", ...}
    kind: Mapped[str] = mapped_column(String(32))
    # "fixed" | "flexible_traffic" | "flexible_duration"
    data_limit_gb: Mapped[int | None]
    duration_days: Mapped[int | None]
    price_cny_fen: Mapped[int]   # stored in 分 (1/100 CNY) to avoid float
    enabled: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class Invoice(Base):
    __tablename__ = "aegis_invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    total_cny_fen: Mapped[int]
    state: Mapped[str] = mapped_column(String(32), index=True)
    # created | pending | awaiting_payment | paid | applied | expired | cancelled | failed
    provider: Mapped[str] = mapped_column(String(32))
    # "epay:<merchant_code>" | "trc20" | "manual_admin"
    provider_invoice_id: Mapped[str | None] = mapped_column(String(128))
    payment_url: Mapped[str | None] = mapped_column(String(512))
    # For TRC20: the unique memo we expect in the tx
    trc20_memo: Mapped[str | None] = mapped_column(String(64))
    trc20_expected_amount: Mapped[int | None]  # USDT in 1/1000 (millis)
    created_at: Mapped[datetime]
    paid_at: Mapped[datetime | None]
    applied_at: Mapped[datetime | None]
    expires_at: Mapped[datetime]  # 30-min payment window


class InvoiceLine(Base):
    __tablename__ = "aegis_invoice_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("aegis_invoices.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("aegis_plans.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price_fen_at_purchase: Mapped[int]


class PaymentEvent(Base):
    """Immutable audit trail: every webhook, every state transition,
    every admin action. For dispute resolution + forensics.
    Append-only — no updates, no deletes."""
    __tablename__ = "aegis_payment_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("aegis_invoices.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    # "created" | "webhook_received" | "state_paid" | "applied" | "admin_manual" | ...
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]
```

Two composite indexes the migration must add:
- `(state, expires_at)` — for the reaper task
- `(user_id, state)` — for user invoice listing

Currency note: **fen (1/100 CNY) for all price math**. Avoids float;
CNY is the primary user-facing currency. USDT channel converts fen
→ USDT at invoice-create with a rate snapshot stored in
`PaymentEvent`.

### Pricing engine (`ops/billing/pricing.py`)

Pure functions, no I/O:

```python
def compute_cart_total_fen(lines: list[CartLine], plans: dict[int, Plan]) -> int:
    """Σ line.quantity × plan.price_cny_fen. Validates kind
    compatibility (flexible plans must specify quantity ≥ 1;
    fixed plans must have quantity = 1). Raises InvalidCart
    with a typed reason."""


def compute_user_grant(invoice: Invoice, plans: dict[int, Plan]) -> UserGrant:
    """Returns (data_limit_gb_delta, duration_days_delta). Aggregates
    across lines. Flexible-traffic lines contribute gb × qty, 0 days;
    flexible-duration lines contribute 0 gb, days × qty; fixed lines
    contribute both."""


def convert_fen_to_usdt_millis(fen: int, rate_fen_per_usdt: int) -> int:
    """Integer math only. rate_fen_per_usdt is the fen cost of 1 USDT
    at invoice-create snapshot time (e.g., 720 for 7.20 CNY/USDT).
    Rounds up on remainder so operator is never short."""
```

### Invoice state machine (`ops/billing/states.py`)

```
    created
       │ user clicks Checkout
       ▼
    pending  ── create-invoice fails ──> failed
       │ provider.create_invoice() succeeds
       ▼
 awaiting_payment  ── timeout 30min ──> expired
       │ provider webhook / poller detects payment
       ▼
     paid
       │ apply_paid_invoices scheduler (idempotent)
       ▼
    applied
```

Transitions enforced by a single `transition(invoice, to_state,
event_payload)` helper. Illegal transitions raise
`InvoiceStateError`. Every call writes a `PaymentEvent` row **before**
updating `Invoice.state` — so if the write fails mid-way, audit log
still captures the attempted transition.

**Idempotency** (non-negotiable):
- `apply_paid_invoices` scheduler: `UPDATE ... WHERE state = 'paid'`
  is atomic per row; if two workers contend, SQLAlchemy
  `SELECT ... FOR UPDATE SKIP LOCKED` ensures only one applies.
- Webhook replay: providers sometimes retry after timeout.
  `webhook_received` event with same `(provider, provider_invoice_id)`
  is de-duplicated by `PaymentEvent` unique key.

### 易支付 adapter (`ops/billing/providers/epay.py`)

Implements the de-facto 易支付 protocol used across the Chinese
market. Reference implementations seen in SSPanel, Xboard, v2board
— the interface is remarkably stable across 码商.

```python
class EPayProvider(BasePaymentProvider):
    """Generic 易支付 adapter. One instance per configured 码商."""

    def __init__(self, merchant_code: str, merchant_key: str,
                 gateway_url: str, callback_base_url: str):
        ...

    async def create_invoice(self, invoice, success_url, cancel_url):
        # POST gateway_url/submit with:
        #   pid, out_trade_no, notify_url, return_url, name, money, sign, sign_type="MD5"
        # sign = md5(sorted_params_without_empty_and_sign_and_sign_type + merchant_key)
        # Returns: payment_url for user to visit

    async def handle_webhook(self, query_params):
        # 码商 POSTs back to notify_url with similar sig'd params
        # Verify sign; match trade_status == "TRADE_SUCCESS"
        # Return WebhookOutcome(invoice_id, new_state="paid", event_type="epay_notify")
```

Admin can configure **multiple** EPayProvider instances
simultaneously (different `merchant_code`), each as a separate
"Payment Channel" row in the admin table. User checkout shows all
enabled ones; failover is a matter of disabling the broken channel.

### TRC20 poller (`ops/billing/providers/trc20.py` + `tasks/trc20_poller.py`)

```python
class Trc20Provider(BasePaymentProvider):
    async def create_invoice(self, invoice, ...):
        # Compute expected_amount_millis (fen -> USDT-millis conversion)
        # Attach a unique 8-char alphanumeric memo to invoice
        # Set invoice.provider_invoice_id = memo
        # Set invoice.trc20_memo + trc20_expected_amount
        # No external call; payment happens on-chain
        # payment_url returns an in-app route that shows the QR+address+memo


# Scheduled task runs every 30s:
async def poll_trc20_invoices():
    open_invoices = fetch_awaiting_payment_trc20_invoices()
    if not open_invoices:
        return
    # One API call covers all open invoices for one address
    recent_txs = await tronscan_client.list_recent_transfers(
        address=TRC20_RECEIVE_ADDRESS,
        token="USDT",
        limit=50,
    )
    for inv in open_invoices:
        match = find_matching_tx(recent_txs, inv)
        if match and match.confirmations >= 3:
            transition(inv, "paid",
                       event_payload={"tx_hash": match.hash, "amount": match.amount_usdt})
```

**Matching strategy**:
1. Preferred: memo match. TRC20 supports a 200-byte `data` field
   per tx. If the user's wallet software includes the memo we gave
   them, match is O(1).
2. Fallback: `(address, amount exact match within 0.1% tolerance,
   time window)`. Used when wallet doesn't carry memos (most
   mobile wallets don't). Amount is derived with cents dither so
   two concurrent invoices never collide (add invoice_id % 100 as
   sub-cent padding).
3. Neither matches → invoice times out at `expires_at`, refund
   happens out-of-band if the user claims they paid.

**Free Tronscan API**:
`https://apilist.tronscanapi.com/api/token_trc20/transfers` —
public, rate-limited to 100 req/s which is enormous overkill for
our 30-s poll. No API key required. Fallback: Trongrid public node.

**Operator key custody**: the `.env` stores only the **public
receive address** (read-only, safe). The private key lives on the
operator's hardware wallet or cold-storage device; they manually
move accumulated USDT out when balance crosses a threshold they
configure. See `OPS-jpy-cashout.md` for the full cashout flow.

### APScheduler tasks (`ops/billing/scheduler.py`)

| Task | Interval | Idempotent? | Purpose |
|---|---|---|---|
| `apply_paid_invoices` | 30 s | ✅ via state machine | paid → applied, grant user, notify |
| `reap_expired_invoices` | 5 min | ✅ via state machine | pending/awaiting past expires_at → expired |
| `trc20_poller` | 30 s | ✅ via tx_hash dedup | Scan blockchain for matching txs |
| `renewal_reminder` | 1 h | ✅ once-per-user-per-window | 7d before expire → TG + email |
| `expiry_enforcer` | 1 h | ✅ once-per-user-per-expiry | expire_date passed → disable user |

Task loop shape matches upstream `app/tasks/` convention — registers
via `scheduler.add_job(...)` in `start_billing_scheduler(app)`,
called exactly once from `apply_panel_hardening(app)` in
`hardening/panel/middleware.py`.

### REST API (`ops/billing/endpoint.py`)

Mounted under `/api/billing` via `apply_panel_hardening`. No edits
to `app/routes/*`.

**User-facing** (authenticated as regular user):
```
GET  /api/billing/plans                    → enabled plans, localized
GET  /api/billing/channels                  → enabled payment channels (epay instances + trc20)
POST /api/billing/cart/checkout             → body: {lines: [{plan_id, quantity}], channel}
                                              returns: {invoice_id, payment_url_or_inline}
GET  /api/billing/invoices/{id}             → poll state; trc20 includes memo + address
GET  /api/billing/invoices/me               → user's history
```

**Webhook-only** (unauthenticated, signature-validated):
```
POST /api/billing/webhook/epay/{channel_code}   → 易支付 MD5 sign
```

**Admin-only** (sudo):
```
GET   /api/billing/admin/plans              → list all (incl. disabled)
POST  /api/billing/admin/plans              → create
PATCH /api/billing/admin/plans/{id}         → update/disable
GET   /api/billing/admin/channels           → configured 易支付 + trc20 state
POST  /api/billing/admin/channels           → add 易支付 channel
PATCH /api/billing/admin/channels/{id}      → update/disable
GET   /api/billing/admin/invoices           → list all, filter by user/state/date
POST  /api/billing/admin/invoices/{id}/apply_manual   → emergency activate
POST  /api/billing/admin/invoices/{id}/cancel          → mark cancelled
```

### i18n strategy — real fix for LESSONS L-012

The billing UI has ~60 user-visible strings, too many for the
`t(key, "default")` workaround used on the SNI dialog. This PR
series lands a **proper fix**:

**Prerequisite commit** (first sub-PR, before any billing code):

1. Refactor `tools/check_translations.sh` from "drift == 0 gate"
   to "drift must not INCREASE relative to base branch":
   ```sh
   # New shape:
   base_drift=$(compute_drift_count $BASE_SHA)
   head_drift=$(compute_drift_count $HEAD_SHA)
   if [ $head_drift -gt $base_drift ]; then
       echo "::error::PR increases locale drift: $base_drift → $head_drift"
       exit 1
   fi
   ```
2. CI action updated to fetch base branch for the comparison.
3. Pre-existing debt stays unfixed (not this PR's problem); new
   PRs can't make it worse.

Then billing strings are added to `en.json` (canonical) and
`zh-cn.json` (full translation, Chinese-majority users) from day
one. Other 6 locales get English placeholders — translator-ready,
not translator-required.

Plan names use the `Plan.display_name_i18n` JSON column:
operator-configurable at runtime, no code change per-plan-per-
locale. UI reads current locale, falls back to `display_name_en`.

### Dashboard UX highlights

- `/dashboard/billing` as primary user page. Card grid of Fixed
  plans across the top; Flexible-addon calculator below (slider
  for GB, slider for extra days, live total update).
- Cart sidebar always visible; "Checkout" button disabled until
  cart total > 0.
- CheckoutPaymentPicker: two tabs, 易支付 default (supports
  failover — if primary 码商 channel is disabled by admin, next
  enabled one shows automatically).
- `Trc20PaymentScreen`: QR code of address, copy-address button,
  exact amount with cents, countdown, polling-based status badge
  ("Waiting..." → "Confirming..." → "✓ Activated").
- `/dashboard/billing/invoices/{id}` for history / re-view of
  past orders.

### Configuration (`.env` additions)

```
# Billing — TRC20 direct
BILLING_TRC20_ENABLED=false
BILLING_TRC20_RECEIVE_ADDRESS=                  # TRC20 (public, read-only)
BILLING_TRC20_TRONSCAN_API_BASE=https://apilist.tronscanapi.com
BILLING_TRC20_PAYMENT_WINDOW_MINUTES=30
BILLING_TRC20_MIN_CONFIRMATIONS=3

# Billing — 易支付 channels (one or more, admin-configured at runtime)
#   The .env only declares the runtime base URL; individual merchant
#   credentials live in the DB so multiple 码商 can be added without
#   restart.
BILLING_EPAY_ENABLED=false
BILLING_EPAY_PUBLIC_CALLBACK_BASE=https://panel.example.com

# Billing — shared
BILLING_PRIMARY_CURRENCY=CNY
BILLING_CNY_USDT_RATE_SOURCE=tronscan   # or "fixed:720" for testing
BILLING_SUCCESS_URL=/dashboard/billing/success
BILLING_CANCEL_URL=/dashboard/billing
```

All fields default-disabled. `.env.example` documents each with
the "why" inline.

## Risks

| Risk | Mitigation |
|---|---|
| 码商 absconds with unsettled balance | Short-settlement preference (T+0); small operating balance; multiple 码商 configured, failover | 
| 码商 suddenly freezes (支付宝 底层账户 被封) | Admin toggles the channel off; user checkout still has TRC20; other 码商 channels continue | 
| 码商 protocol dialect variance | Adapter is **generic** matching 90% 易支付; per-码商 quirks handled by an override hook; `OPS-epay-vendor-guide.md` documents known dialects |
| TRC20 private key leak | We only store public address; private key lives on operator hardware wallet |
| TRC20 Tronscan public API outages | 30-s polling means 30-s delay worst case; fallback to Trongrid node documented |
| Chain reorg applied before 3 confs | Task enforces `confirmations >= 3` before transition to `paid` |
| Two users purchase same plan same second, amount collision | Cents dither per invoice_id % 100; memo match preferred where wallet supports it |
| GFW blocks Chinese user reaching Tronscan | Server-side polling runs from JP VPS (non-CN); user-side dashboard never hits Tronscan directly |
| 易支付 webhook hits arrive before redirect returns user | State machine handles out-of-order: webhook sets `paid`, scheduler applies; redirect lands on success page which polls `/invoices/{id}` and sees `applied` |
| Pre-existing locale drift (L-012) blocks PR | Drift-gate refactor is sub-PR #1 of the series |
| Operator confuses `Invoice` for subscription | Named `Invoice` not `Subscription`; README explicitly contrasts |

## Acceptance criteria

Enumerated per sub-PR. Incremental landing:

**A.0 (this SPEC PR)**:
- [ ] `docs/ai-cto/SPEC-billing-mvp.md` merged
- [ ] `docs/ai-cto/OPS-epay-vendor-guide.md` merged (bundled)
- [ ] `docs/ai-cto/OPS-jpy-cashout.md` merged (bundled)
- [ ] `docs/ai-cto/DECISIONS.md` gets D-010 appended

**A.0.5 prerequisite (own PR before A.1)**:
- [ ] `tools/check_translations.sh` + `.github/workflows/translations.yml`
      switched to diff-based drift gate
- [ ] Main-branch drift baseline captured (so future PRs have a number to compare)

**A.1 — data + admin + pricing**:
- [ ] `ops/billing/db.py` with 4 models + composite indexes
- [ ] Alembic migration passing SQLite + PG 16 dual job
- [ ] `ops/billing/pricing.py` + unit tests (≥10 tests covering
      mixed carts, flexible-addon math, currency rounding)
- [ ] `ops/billing/states.py` state machine + idempotency tests
- [ ] Admin REST endpoints (plans, channels, invoices list, manual-apply)
- [ ] Admin dashboard pages: plan CRUD, channel CRUD, invoice list
- [ ] CI green on both DB backends

**A.2 — 易支付**:
- [ ] `ops/billing/providers/epay.py` with generic MD5 sign
- [ ] Webhook endpoint with signature verification
- [ ] Integration test with a stub 码商 gateway
- [ ] README section with the full protocol reference

**A.3 — TRC20**:
- [ ] `ops/billing/providers/trc20.py` + `tasks/trc20_poller.py`
- [ ] Tx matching logic (memo-preferred, amount-fallback, cents dither)
- [ ] 3-conf wait enforced
- [ ] Recorded-response unit tests; no live Tronscan in CI

**A.4 — user purchase flow**:
- [ ] `dashboard/src/modules/billing/` full module
- [ ] CheckoutPaymentPicker with 易支付/TRC20 tabs
- [ ] Trc20PaymentScreen with QR, countdown, polling
- [ ] Locale strings in en + zh-cn complete; other 6 have English seed

**A.5 — automation**:
- [ ] Renewal reminder + expiry enforcement tasks + tests
- [ ] Telegram + email via existing `app/notification/` helpers
- [ ] Once-per-window idempotency test

## Estimated effort

| Sub-PR | Content | Estimate |
|---|---|---|
| A.0 (this) | SPEC + 2 ops docs + D-010 | 1 day |
| A.0.5 | drift gate refactor | 0.5 day |
| A.1 | models + admin + pricing + state machine | 1.5 weeks |
| A.2 | 易支付 provider + webhook | 1 week |
| A.3 | TRC20 provider + poller | 1 week |
| A.4 | user purchase UI (full flow, 8-language i18n) | 1 week |
| A.5 | renewal + expiry automation | 0.5 week |
| **Total** | | **~5 weeks** |

## Follow-up PRs (after MVP, v0.3+)

- BTCPay Server self-hosted provider (zero middleman)
- BTC / USDT ERC20 second chain
- Refund automation (admin-initiated credit)
- Coupon / promo code system
- Recurring subscription with on-file payment (Stripe only, if
  operator ever has an entity)
- Invoice PDF export
- Affiliate / reseller program
- Multi-fiat display (USD / JPY / EUR toggle)
- Stripe Japan integration (**only** if operator registers a
  Japanese legal entity AND category gets approved — not speculative
  stub work)

---

_Authored by CTO session 2026-04-22 during Round 2 path A kickoff.
See D-010 for the payment-strategy decision record. Revise if scope
shifts before A.0.5 starts._
