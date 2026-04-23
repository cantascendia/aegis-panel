# SPEC — Billing A.2 易支付 + A.3 TRC20(Round 3 mid path A)

> Round 3 mid path A — "能变现"的最后一跃。
>
> Status: draft → implementation。A.1(data + admin UI)已在 PR
> #28/#29/#30/#32/#33/#35 完整落地;现 panel 可"管理 plans / channels /
> invoices",**但还不能收钱**。本 SPEC 填补 A.2(支付发起 + webhook)
> 与 A.3(链上入账轮询)。
>
> 基线:`docs/ai-cto/SPEC-billing-mvp.md`(总蓝图)+ `D-010`(支付策略
> 决策)+ A.1 code on main at `cc99566`。本文档只细化 A.2/A.3,其他
> scope 参见总蓝图。
>
> Template: D-005 Spec-Driven shape。

---

## 何以必要(延续 SPEC-billing-mvp 的论证)

A.1 把 panel 从"不能收钱"推进到"管理员能手动 apply_manual 一张
invoice"。但管理员手动确认每笔支付 = **O(付费用户数 × 续费频率)** 的人
工负担,对 >200 用户的目标市场不可行。A.2 + A.3 把这条人工链路自
动化,使得:

- 用户扫 支付宝/微信 付完款 → 60 秒内 invoice 自动 applied,流量 +
  时长自动续
- 用户转 USDT 付完款 → 下一轮 poll(30s)后 invoice 自动 applied

这是"试运营 → 正式运营"的门槛。A.2/A.3 不落地就没有变现闭环。

---

## 前置依赖(main 已有)

A.1 已就位的资产,A.2/A.3 直接复用:

- `ops/billing/db.py`:`Plan` / `PaymentChannel` / `Invoice` /
  `InvoiceLine` / `PaymentEvent` 五表完整,`PaymentChannel.kind` 已留
  `"epay"` 插槽,`Invoice.trc20_memo` 和 `trc20_expected_amount_millis`
  字段已建
- `ops/billing/states.py`:`transition(invoice, to_state,
  event_payload)` 单一可写路径 + `record_webhook_seen` 去重原子语义
- `ops/billing/endpoint.py`:已有 admin REST(含 `apply_manual` /
  `cancel` 动作);用户购买 REST 暂缺(属 A.4 scope,不在本 PR)
- `hardening/panel/middleware.py::apply_panel_hardening`:统一注册
  入口,A.2/A.3 新 router 走这里加一行
- APScheduler 基础设施(`hardening/iplimit/scheduler.py` 的
  lifespan-wrap 模式已沉淀)——A.3 的 poller 照搬

---

## A.2 易支付(EPay)Provider 落地

### 目标

实现**通用**易支付协议 adapter(非某一家 码商 专用)。满足:

- 用户 `POST /api/billing/cart/checkout` 指定 `channel=epay:<code>` →
  panel 生成带 MD5 sign 的跳转 URL → 用户扫码付款
- 码商 webhook POST 回 `/api/billing/webhook/epay/<channel_code>` →
  MD5 验签 → 找到 invoice → `transition(..., "paid", ...)`
- 同一 webhook 重复到达 → 基于 `(channel_code, provider_invoice_id)`
  幂等

### 目录结构(新建)

```
ops/billing/providers/
├── __init__.py             # 导出 get_provider(channel_kind, channel_code) -> BaseProvider
├── base.py                 # BasePaymentProvider 抽象基类
└── epay.py                 # 易支付 adapter
```

### 接口抽象(`base.py`)

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class CreateInvoiceResult:
    """Return shape from ``create_invoice``.

    For EPay: ``payment_url`` 是跳转第三方扫码页。
    For TRC20: ``payment_url`` 是面板内地址页(/billing/invoice/{id})。
    """
    provider_invoice_id: str
    payment_url: str
    extra_payload: dict  # 存进 PaymentEvent,便于排障


@dataclass(frozen=True)
class WebhookOutcome:
    """Return shape from ``handle_webhook``.

    - ``invoice_id``: 目标 invoice(回查 DB 得到)
    - ``new_state``: 期望转到的 state(通常是 "paid",支持 "failed")
    - ``provider_event_id``: 供 ``record_webhook_seen`` 去重
    - ``raw``: 原始 payload,入 PaymentEvent.payload_json
    """
    invoice_id: int
    new_state: str
    provider_event_id: str
    raw: dict


class BasePaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(
        self,
        invoice_id: int,
        amount_cny_fen: int,
        subject: str,
        success_url: str,
        cancel_url: str,
    ) -> CreateInvoiceResult: ...

    @abstractmethod
    async def handle_webhook(
        self, params: Mapping[str, str], raw_body: bytes
    ) -> WebhookOutcome: ...
```

### EPay adapter(`epay.py`)

**协议参考**:SSPanel / Xboard / v2board 实现均遵循同一变体,字段集
合稳定:

**发起支付(submit)**:
- 方法:`POST` 到 `gateway_url + "/submit.php"`(部分 码商 用
  GET,参数相同)
- 参数(按 key 字典序排序 + merchant_key 拼接 MD5 得 `sign`):
  - `pid` = `merchant_code`
  - `type` = `"alipay" | "wxpay"`(本实现固定 `"alipay"` 作为 MVP,
    后续 channel 表加 `payment_method` 字段支持 wxpay)
  - `out_trade_no` = `f"INV-{invoice_id}-{ts_sec}"`(必须全局唯一;
    invoice_id 已唯一,叠时间戳防重发)
  - `notify_url` = `"{public_base}/api/billing/webhook/epay/{channel_code}"`
  - `return_url` = `success_url`(传进来,外部可见)
  - `name` = subject
  - `money` = `f"{amount_cny_fen / 100:.2f}"`
  - `sign_type` = `"MD5"`
  - `sign` = 计算得出(见下)

**sign 算法**(常见 70% 实现):
```python
def _compute_sign(params: dict[str, str], merchant_key: str) -> str:
    # 1. 过滤 sign / sign_type 本身 + 过滤空值
    # 2. key 字典序升序
    # 3. 拼接 "k1=v1&k2=v2...&KEY=<merchant_key>"
    # 4. MD5(utf-8).hexdigest().lower()
    filtered = {k: v for k, v in params.items()
                if k not in ("sign", "sign_type") and v != ""}
    sorted_items = sorted(filtered.items())
    body = "&".join(f"{k}={v}" for k, v in sorted_items)
    body += f"&{merchant_key}"    # 注意:部分码商用 "&key={merchant_key}",需在 channel 表配开关
    return hashlib.md5(body.encode("utf-8")).hexdigest().lower()
```

**边际兼容**:部分 码商 用 `body += f"&key={merchant_key}"`(带 key=
前缀);`PaymentChannel.extra_config_json` 加 `"sign_body_mode":
"plain" | "with_key_prefix"`,default `"plain"`。首批支持一家,其他
上线再扩。

**webhook verify**:
```python
async def handle_webhook(self, params, raw_body):
    received_sign = params.get("sign")
    computed = _compute_sign(params, self._merchant_key)
    if received_sign != computed:
        raise InvalidSignature()

    if params.get("trade_status") != "TRADE_SUCCESS":
        # 码商 也会 POST "TRADE_FAIL" 等;当前 MVP 只处理 SUCCESS,
        # 其他 state_new 设为 None 表示"已观察但不改状态"(由上层
        # 忽略)
        raise UnhandledEventType(params.get("trade_status"))

    out_trade_no = params["out_trade_no"]  # "INV-123-1714..."
    invoice_id = _parse_invoice_id(out_trade_no)  # -> 123
    return WebhookOutcome(
        invoice_id=invoice_id,
        new_state="paid",
        provider_event_id=params["trade_no"],  # 码商 的订单号,去重 key
        raw=dict(params),
    )
```

### REST surface(新增)

Mount 到 `apply_panel_hardening(app)`:

```python
# ops/billing/endpoint.py(扩增)

@router.post("/api/billing/cart/checkout")
async def checkout(
    body: CheckoutRequest,       # lines + channel_code
    admin: CurrentUserDep,
    db: DBDep,
) -> CheckoutResponse:
    """创建 invoice + 调 provider.create_invoice() + 返回 payment_url。"""
    # 1. 验 channel enabled
    # 2. pricing.compute_cart_total_fen()
    # 3. create Invoice (state="pending")
    # 4. get_provider(channel).create_invoice(...) → 得 payment_url
    # 5. transition("pending" → "awaiting_payment", event=...)
    # 6. return {"invoice_id": ..., "payment_url": ...}


@router.post("/api/billing/webhook/epay/{channel_code}")
async def epay_webhook(
    channel_code: str,
    request: Request,
    db: DBDep,
) -> Response:
    """无需 auth;sig + IP 白名单双层防护。"""
    # 1. (可选)校验来源 IP 在 channel.extra_config_json["allowed_ips"] 内
    # 2. provider = get_provider("epay", channel_code)
    # 3. outcome = await provider.handle_webhook(request.query_params, body)
    # 4. record_webhook_seen(db, invoice_id=outcome.invoice_id,
    #                        provider_event_id=outcome.provider_event_id)
    # 5. 若 replay → return "success"(码商 约定:回 "success" 字面串停止重试)
    # 6. 否则 transition(invoice, outcome.new_state, event_payload=outcome.raw)
    # 7. return "success"
```

### 测试

**单元**(离线,mock request):
- `test_epay_sign_matches_vendor_reference`:用一组公开的 SSPanel
  fixture 算出来的 sign,验证我们的 `_compute_sign` 产出相同
- `test_epay_webhook_invalid_sign_raises`
- `test_epay_webhook_replay_is_noop`:发两次 identical webhook,第二
  次 `record_webhook_seen` 返回 False → 跳 `transition`
- `test_epay_webhook_trade_fail_does_not_transition`
- `test_epay_create_invoice_url_has_all_required_params`

**集成**(stub 码商 gateway,`tests/test_billing_epay_flow.py`):
- 拉起 FastAPI TestClient
- 发 POST `/api/billing/cart/checkout` → 断言返回 `payment_url`
  含 `pid=` / `money=` / `sign=`
- 模拟 码商 POST 到 webhook(自己用同样的 `_compute_sign` 伪造 sign)
  → 断言 invoice.state 从 `awaiting_payment` → `paid`
- 触发 `apply_paid_invoices` 一次 → 断言 invoice.state → `applied`
  + 用户 `data_limit` 和 `expire_date` 正确扩容

**目标**:≥ 12 tests,全离线(不打 码商 gateway,不接真实 APScheduler)。

### 部署配置

```
# .env 新增
BILLING_PUBLIC_BASE_URL=https://panel.example.com
# 用于构造 webhook notify_url;必须是 码商 可达的公网 URL
# 码商 会从外网 POST 过来,所以不能用 127.0.0.1
```

`PaymentChannel` 表 runtime 配置(无需 .env 侧改):
- `merchant_code`:pid
- `merchant_key`:明文存储,但表字段加密(`cryptography.fernet` 对称
  加密,key 来源 `BILLING_SECRET_KEY` env;admin UI 显示脱敏)
- `gateway_url`:`https://pay.xxxxx.com`(不同 码商 不同)
- `extra_config_json`:`{"sign_body_mode": "plain",
  "allowed_ips": ["1.2.3.4"]}`

**Admin UI**(复用 PR #33 已有的 channels 页,加两个输入框 +
一个 "Test sign" 按钮即可)。

---

## A.3 TRC20 自建轮询

### 目标

- 用户 checkout 指定 `channel_code="trc20"` → panel 分配 8-char
  唯一 memo + 计算 expected USDT-millis + 返回面板内 QR 页 URL
- 每 30 秒 `poll_trc20_invoices` 任务扫 Tronscan 最近 tx,按 memo
  优先 / amount-dither fallback 匹配 open invoice
- 匹配且 confirmations ≥ 3 → `transition(inv, "paid", ...)`
- Tronscan 不可用时**降级**:任务 skip 这一轮,不 crash,下轮重试

### 目录结构(续建)

```
ops/billing/providers/
├── trc20.py                # Trc20Provider
└── tronscan.py             # thin HTTP client (httpx-based)

ops/billing/tasks/
├── __init__.py
├── trc20_poller.py         # poll_trc20_invoices
└── apply_paid.py           # 已在 A.5 scope,本 PR 顺带补一个最小版
```

### Trc20Provider(`trc20.py`)

```python
class Trc20Provider(BasePaymentProvider):
    """无外部 call 的 provider;payment 发生在链上。"""

    def __init__(self, receive_address: str, rate_source: str):
        self._receive_address = receive_address
        self._rate_source = rate_source  # "tronscan" | "fixed:720"

    async def create_invoice(
        self, invoice_id, amount_cny_fen, subject,
        success_url, cancel_url,
    ) -> CreateInvoiceResult:
        # 1. 查当前 CNY/USDT 汇率(Tronscan 返回;fixed:720 走固定)
        rate_fen_per_usdt = await self._fetch_rate_fen_per_usdt()

        # 2. fen → USDT-millis,向上取整保证收款方不亏
        usdt_millis_base = (amount_cny_fen * 1000 + rate_fen_per_usdt - 1) \
                           // rate_fen_per_usdt

        # 3. cents dither:加 invoice_id % 100 作"尾数",杜绝两张 invoice
        #    同金额导致 amount-fallback 错配
        usdt_millis = usdt_millis_base + (invoice_id % 100)

        # 4. memo:8 char base32(blake2b(invoice_id + secret))
        memo = _gen_memo(invoice_id)

        # 5. 写回 invoice.trc20_memo + trc20_expected_amount_millis
        #    (通过调用方写;provider 只计算)
        return CreateInvoiceResult(
            provider_invoice_id=memo,
            payment_url=f"/dashboard/billing/invoice/{invoice_id}",  # in-panel
            extra_payload={
                "receive_address": self._receive_address,
                "expected_amount_millis": usdt_millis,
                "memo": memo,
                "rate_fen_per_usdt": rate_fen_per_usdt,
            },
        )

    async def handle_webhook(self, params, raw_body):
        # TRC20 没有 webhook;所有 state 推进由 poller 驱动
        raise NotImplementedError(
            "TRC20 uses polling, not webhooks. Do not route here."
        )
```

### Tronscan thin client(`tronscan.py`)

```python
class TronscanClient:
    """Read-only client for public Tronscan APIs.

    No API key required. Rate limit 100 req/s,远超需要。
    网络失败时抛 TronscanUnavailable,上层(poller)吞并重试。
    """

    BASE = "https://apilist.tronscanapi.com"
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC20

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client or httpx.AsyncClient(timeout=10.0)

    async def list_recent_usdt_transfers(
        self, to_address: str, *, limit: int = 50,
    ) -> list[Trc20Tx]:
        """GET /api/token_trc20/transfers?toAddress=...&limit=...

        返回按时间倒序的最近 tx。每条包含:
        - transaction_id (txHash)
        - quant(字符串,USDT-millis,需转 int)
        - confirmed(bool)
        - confirmations_count(int,用于 3-confs 判断)
        - block_ts(ms)
        - from_address / to_address
        - data(可选;若用户钱包带 memo,这里有)
        """
        resp = await self._client.get(
            f"{self.BASE}/api/token_trc20/transfers",
            params={
                "toAddress": to_address,
                "contract_address": self.USDT_CONTRACT,
                "limit": limit,
                "start": 0,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [_parse_tx(item) for item in data.get("token_transfers", [])]

    async def fetch_usdt_cny_rate_fen(self) -> int:
        """返回 1 USDT 当前值多少 fen(取整)。

        用 Tronscan 主页 API:
        ``/api/tokens/overview?symbol=usdt`` → price_in_cny。
        失败抛 TronscanUnavailable。
        """
        ...
```

### Poller task(`tasks/trc20_poller.py`)

```python
async def poll_trc20_invoices() -> None:
    """Every 30s. Idempotent via tx_hash dedup + state machine."""
    # 1. 读 .env:enabled? receive_address 配置没?
    if not _is_trc20_enabled():
        _log_once("trc20 disabled")
        return

    client = TronscanClient()
    try:
        txs = await client.list_recent_usdt_transfers(
            to_address=TRC20_RECEIVE_ADDRESS, limit=50,
        )
    except TronscanUnavailable as e:
        logger.warning("trc20 poller: Tronscan unavailable, skip: %s", e)
        return

    with GetDB() as db:
        open_invoices = _fetch_awaiting_trc20_invoices(db)

        for inv in open_invoices:
            match = _match_tx(txs, inv)
            if match is None:
                continue
            if match.confirmations < TRC20_MIN_CONFIRMATIONS:
                continue

            # record_webhook_seen 的 provider_event_id = tx_hash
            first = record_webhook_seen(
                db, invoice_id=inv.id, provider_event_id=match.tx_hash,
            )
            if not first:
                continue  # replay;别二次 transition

            transition(
                db, inv, "paid",
                event_payload={
                    "tx_hash": match.tx_hash,
                    "amount_millis": match.amount_millis,
                    "from_address": match.from_address,
                    "confirmations": match.confirmations,
                    "matched_by": match.matched_by,  # "memo" | "amount_dither"
                },
            )
            logger.info(
                "trc20 matched invoice=%d tx=%s (%s)",
                inv.id, match.tx_hash, match.matched_by,
            )


def _match_tx(txs: list[Trc20Tx], inv: Invoice) -> MatchedTx | None:
    """Match priority: memo > amount-dither > None."""
    # 1. memo match — 首选
    for tx in txs:
        if tx.memo and tx.memo.strip() == inv.trc20_memo:
            return MatchedTx(..., matched_by="memo")

    # 2. amount match within invoice window (created_at .. expires_at)
    #    + exact amount_millis(含 cents dither)
    for tx in txs:
        if tx.block_ts_ms < inv.created_at.timestamp() * 1000:
            continue
        if tx.block_ts_ms > inv.expires_at.timestamp() * 1000 + 3600_000:
            # 60 分钟宽容窗口,容忍链上延迟
            continue
        if tx.amount_millis == inv.trc20_expected_amount_millis:
            return MatchedTx(..., matched_by="amount_dither")

    return None
```

### Scheduler 挂载

沿用 `hardening/iplimit/scheduler.py` 的 lifespan-wrap pattern:

```python
# ops/billing/scheduler.py
def install_billing_scheduler(app: FastAPI) -> None:
    if getattr(app.state, "billing_scheduler_installed", False):
        return

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        poll_trc20_invoices, "interval", seconds=TRC20_POLL_INTERVAL,
        coalesce=True, max_instances=1,
        id="aegis-billing-trc20", replace_existing=True,
    )
    scheduler.add_job(
        apply_paid_invoices, "interval", seconds=APPLY_PAID_INTERVAL,
        coalesce=True, max_instances=1,
        id="aegis-billing-apply-paid", replace_existing=True,
    )

    # wrap lifespan,同 iplimit
    ...

    app.state.billing_scheduler = scheduler
    app.state.billing_scheduler_installed = True
```

在 `hardening/panel/middleware.py::apply_panel_hardening` 加:
```python
from ops.billing.scheduler import install_billing_scheduler
install_billing_scheduler(app)
```

### 测试

**单元**(`tests/test_billing_trc20_matcher.py`):
- `test_match_by_memo_exact`
- `test_match_by_amount_dither_within_window`
- `test_no_match_different_amount`
- `test_no_match_out_of_time_window`
- `test_memo_takes_priority_over_amount`
- `test_cents_dither_prevents_collision`:两张 invoice 基准金额相同,
  dither 后 amount_millis 不同 → 只匹配对应的那张

**Tronscan client**(mocked httpx):
- `test_list_recent_transfers_parses_fixture`:用一份落盘的 Tronscan
  response JSON fixture,验证 parse 正确
- `test_tronscan_unavailable_raises_clean_exception`
- `test_rate_fetch_converts_to_fen_correctly`

**Poller**(fake Redis? 不需要 Redis;只需 DB + mock Tronscan):
- `test_poller_skips_when_disabled`
- `test_poller_survives_tronscan_outage`:client.list_* 抛异常 → 日
  志 + return,不 crash
- `test_poller_matches_invoice_and_transitions_to_paid`:mock 返回
  一条 match tx → invoice.state 从 `awaiting_payment` → `paid`
- `test_poller_skips_under_3_confirmations`
- `test_poller_idempotent_on_replay`:同样 tx 跑两轮,state 不重复
  transition(`record_webhook_seen` 拦下)

**Apply-paid scheduler**(离线):
- `test_apply_paid_transitions_paid_to_applied_and_grants_user`
- `test_apply_paid_idempotent_for_already_applied`

**目标**:≥ 18 tests(matcher 6 + client 3 + poller 5 + apply_paid 2
+ 集成 2 = 18),全离线。

### 部署配置

```
# .env 新增
BILLING_TRC20_ENABLED=false
BILLING_TRC20_RECEIVE_ADDRESS=             # TRC20 公开地址
BILLING_TRC20_TRONSCAN_API_BASE=https://apilist.tronscanapi.com
BILLING_TRC20_POLL_INTERVAL_SECONDS=30
BILLING_TRC20_MIN_CONFIRMATIONS=3
BILLING_TRC20_PAYMENT_WINDOW_MINUTES=30

BILLING_APPLY_PAID_INTERVAL_SECONDS=30

BILLING_CNY_USDT_RATE_SOURCE=tronscan       # 或 fixed:720 for CI/dev
```

Fail-loud:`BILLING_TRC20_ENABLED=true` 但 `BILLING_TRC20_RECEIVE_ADDRESS`
空 → panel startup 抛 `BillingMisconfigured`(类比 `RateLimitMisconfigured`
模式)。

---

## 跨 A.2 / A.3 的共性

### 失败模式处理

| 失败 | 响应 | 防线 |
|---|---|---|
| EPay 码商 webhook 伪造 | 验签失败 → 400 | MD5 + optional IP 白名单 |
| EPay 重放攻击 | `record_webhook_seen` 去重 | DB 唯一键 |
| EPay 签名算法变体(`&key=` 前缀) | 按 channel 配置切换 | `extra_config_json.sign_body_mode` |
| TRC20 chain reorg | 要求 confirmations ≥ 3 | 配置项 + 文档化 |
| TRC20 Tronscan 宕机 | 任务 skip,下轮重试 | 日志 warn 不 crash |
| TRC20 用户付少了 / 付多了 | 当前 MVP 不匹配,进超时 → expired | 文档建议用户严格按金额转 |
| 两张 TRC20 invoice 基数同 | cents dither 消歧 | invoice_id % 100 毫分位 |
| 用户付款后 panel 宕机 | 重启后 poller 下一轮扫到,正常 transition | 状态机 `paid` 只允许一次 |
| apply_paid 多 worker 并发 | `transition` 本身带 `record_webhook_seen` 或状态检查 | state machine 单路径 |

### 日志 + 审计(每个 transition 必写 PaymentEvent)

- `event_type` 枚举:
  - `"invoice_created"`
  - `"provider_submit_succeeded"` / `"provider_submit_failed"`
  - `"webhook_received"`(A.2)
  - `"trc20_matched"`(A.3)
  - `"state_transition"`(任何一次 state 改动)
  - `"user_granted"`(apply_paid 成功后 user 扩容记录)
  - `"admin_manual_apply"` / `"admin_cancel"`(A.1 已有)
- `payload_json`:原始数据 + sign/raw params + matched tx 细节
- **append-only**:不修不删,只插入,排障最可靠

### 前端(次要,本 PR 范围内最小实现)

本 SPEC 的 PR 不做完整 UI(属 A.4);但需要**两个最小 stub** 满足端
到端 smoke:

1. `/dashboard/billing/checkout-demo`(内部测试页,admin only):一
   个最简表单 + checkout 按钮,POST `/api/billing/cart/checkout`,
   显示返回的 payment_url。用于 A.2 联调
2. `/dashboard/billing/invoice/{id}`(TRC20 支付页):只在 channel=
   trc20 且 state=awaiting_payment 时渲染,显示地址 + QR + 金额 +
   memo + 倒计时。轮询 `GET /api/billing/invoices/{id}` 直到 state
   变 paid/applied 显示"✓ 已到账"。用于 A.3 联调

两个都用 defaultValue 模式的 i18n,**不碰 locale JSON**。

真正面向 C 端用户的"plan 卡片 + cart + tabs" UI 留给 A.4。

---

## 风险 / 边界

| 风险 | 缓解 |
|---|---|
| 所有 A.2 单测通过但真实 码商 签名方言不同 | PR 合并后先在 staging 用真 码商 小额 测试,发现 dialect 分支 → 加 `extra_config_json` 枚举分支,更新 `OPS-epay-vendor-guide.md` |
| TRC20 Tronscan API 免费版突然被墙或限额 | 已有 fallback 文档(Trongrid);.env 支持 `BILLING_TRC20_TRONSCAN_API_BASE` 可替换 |
| 码商 在我们发 webhook response 前已认为超时 | 保证 handler 在 200ms 内返回 "success"。实现:handle_webhook 只校验 + 记录 + 入 `transition`,应用扩容动作走 apply_paid scheduler 异步,webhook 不等 |
| cents dither 冲突(invoice_id 取模后同) | 100 个取模位在并发 invoice 数 <50 的环境不会真碰撞;若碰 → 双重 fallback 到"无匹配超时 expire + 管理员 apply_manual" |
| 用户付款后 panel DB 崩溃 + Tronscan 也扫不到 | 操作手册必须说明:管理员查 Tronscan web → 确认 tx → 用 A.1 的 `apply_manual` + 粘贴 tx hash 到 note。失败兜底永远可 manual |
| `.env` 里 `BILLING_SECRET_KEY` 没配 | fail-loud:启动时 `merchant_key` 加密列解密失败 → 抛明确异常 |

---

## 验收标准(Acceptance Criteria)

**A.2(易支付)PR**:
- [ ] `ops/billing/providers/base.py` + `providers/epay.py` 落地
- [ ] `ops/billing/providers/__init__.py` 导出 `get_provider(kind,
      channel_code) -> BaseProvider` 工厂
- [ ] `POST /api/billing/cart/checkout` 创建 invoice + 返回 payment_url
- [ ] `POST /api/billing/webhook/epay/{channel_code}` 验签 + 入
      state 机
- [ ] `PaymentChannel.merchant_key` 加密列(Fernet,key 来源 env)
- [ ] `PaymentChannel.extra_config_json` 支持 `sign_body_mode` +
      `allowed_ips` 两字段
- [ ] ≥ 12 后端单测 + 集成测试,全离线
- [ ] `OPS-epay-vendor-guide.md` 文档:已测 码商 清单 + dialect 分支
- [ ] CI 全绿(API CI 6 job + stepped-alembic + translations drift
      无增)

**A.3(TRC20)PR**:
- [ ] `ops/billing/providers/trc20.py` + `tronscan.py` + `tasks/
      trc20_poller.py` + `tasks/apply_paid.py` 落地
- [ ] `scheduler.py` 用 lifespan-wrap 注册两个 interval job(照搬
      iplimit 模式)
- [ ] `apply_panel_hardening(app)` 加 1 行 `install_billing_scheduler(app)`
- [ ] `_gen_memo` + cents dither + 3-confs 逻辑实装
- [ ] TRC20 disabled(env 未配)→ 任务 skip,日志一次,不 crash
- [ ] Tronscan 不可用 → 任务 skip,不 crash,下轮重试
- [ ] 面板内 `GET /dashboard/billing/invoice/{id}` 最小 TRC20 付款页
- [ ] ≥ 18 后端测试,全离线(Tronscan mock 用 recorded fixture)
- [ ] `README.md` / `OPS-trc20-runbook.md`(含地址轮换 / cashout /
      TZ / 加密密钥管理章节)
- [ ] CI 全绿(同上 + Redis 未配路径验证)

**共性**:
- [ ] 新 model / 新字段走 `app/db/extra_models.py` aggregator 注册
      (遵守 L-014 硬规则)
- [ ] 任何 Alembic migration **新建 revision**,不 mutate 已 merge
      的(L-015 硬规则)
- [ ] 没有硬编码 secrets;`.env` 全部走 `.env.example` 文档 + fail-
      loud 校验
- [ ] i18n 全部 `t(key, "english default")` 模式,不改 locale JSON
      (L-012 / L-017)

---

## PR 拆分建议

```
A.2.1  feat(ops): billing provider abstraction + epay adapter
A.2.2  feat(ops): billing cart checkout + epay webhook REST + admin UI hint
A.3.1  feat(ops): trc20 provider + tronscan client + matcher
A.3.2  feat(ops): billing scheduler (trc20 poller + apply_paid)
A.3.3  feat(dashboard): minimal TRC20 payment screen + checkout-demo
```

5 个 sub-PR,每个 ≤ 600 行 diff。Cross-review **强烈推荐** A.2.2
(webhook) 和 A.3.1 (matcher) —— 二者都涉及钱,review ROI 按 iplimit
经验是爆表的。

---

## 时间估计

| Sub-PR | 内容 | 估计 |
|---|---|---|
| A.2.1 | provider abstraction + epay adapter + 单测 | 1.5 天 |
| A.2.2 | checkout + webhook + 加密列 + 集成测试 + OPS 文档 | 1.5 天 |
| A.3.1 | trc20 + tronscan client + matcher + 单测 | 1.5 天 |
| A.3.2 | scheduler + poller + apply_paid + 集成测试 | 1.5 天 |
| A.3.3 | 前端两个 stub 页 + i18n | 1 天 |
| **Total** | | **7 天** |

对齐 SPEC-billing-mvp.md 的总 5 周估计(本 A.2+A.3 = 2 周,现修正
为 7 天,是因为 A.1 已把很多基础设施前置完成)。

---

## Follow-up(A.2+A.3 之后)

- A.4 完整用户购买 UI(plan 卡片 / cart / tabs / history)
- A.5 renewal reminder + expiry enforcer(APScheduler tasks)
- v0.3:BTCPay Server 自托管 provider / 多 码商 并行 failover UI
  优化 / 退款自动化

---

_Authored by CTO session 2026-04-23 during Round 3 mid path A kickoff.
Baseline: `SPEC-billing-mvp.md` + main @ `cc99566`. Revise if scope
shifts before A.2.1 starts._
