"""
Cart checkout + EPay webhook REST surface (A.2.2).

Sits beside the admin router in ``ops.billing.endpoint`` but with its
own module because:

- Auth shape differs per route. ``POST /api/billing/cart/checkout``
  is gated by ``SudoAdminDep`` today (A.4 will add a user-self-serve
  sibling under ``UserDep``); ``POST /api/billing/webhook/epay/...``
  is **unauthenticated** by design — the 码商 is the anonymous
  caller, and we rely on MD5 signature + optional IP allowlist.
- Lifecycle boundaries are cleaner. Admin CRUD lives in ``endpoint.py``
  and evolves independently of the payment-flow plumbing here.

Both routes go through :func:`ops.billing.states.transition` for
every state change, so the audit log (PaymentEvent) reflects every
attempt, replay, and sign-mismatch without extra bookkeeping here.
"""

from __future__ import annotations

import ipaddress
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select

from app.dependencies import DBDep, SudoAdminDep
from ops.billing import config as billing_config
from ops.billing import trc20_config
from ops.billing.db import (
    INVOICE_STATE_AWAITING_PAYMENT,
    INVOICE_STATE_PENDING,
    Invoice,
    InvoiceLine,
    PaymentChannel,
    Plan,
)
from ops.billing.pricing import (
    CartLine,
    InvalidCart,
    compute_cart_total_fen,
)
from ops.billing.providers import get_provider
from ops.billing.providers.base import (
    InvalidSignature,
    UnhandledEventType,
)
from ops.billing.schemas import CheckoutIn, CheckoutOut
from ops.billing.states import (
    InvoiceStateError,
    record_webhook_seen,
    transition,
)

logger = logging.getLogger(__name__)

# 30-minute payment window is the SPEC default. Exposed as a module
# constant so operators / tests can monkeypatch; not env-driven in
# A.2.2 because we have no operator ask for tuning it yet.
CHECKOUT_PAYMENT_WINDOW = timedelta(minutes=30)

# 码商 convention: reply "success" in the response body to stop the
# retry cadence. Any other status code / body triggers the 码商's
# 10-attempt exponential backoff.
WEBHOOK_SUCCESS_BODY = "success"

checkout_router = APIRouter(prefix="/api/billing", tags=["Billing Checkout"])


# ---------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------


@checkout_router.post(
    "/cart/checkout",
    response_model=CheckoutOut,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    body: Annotated[CheckoutIn, Body()],
    db: DBDep,
    admin: SudoAdminDep,  # noqa: ARG001  # auth gate
) -> CheckoutOut:
    """Create an invoice + call the payment provider to obtain a
    redirect URL.

    Admin-initiated on behalf of ``body.user_id``. A.4 adds the user
    self-serve variant under a separate auth dep; the shape here is
    intentionally stable so A.4 can reuse ``CheckoutIn`` / ``CheckoutOut``.
    """

    # Channel resolution.
    #
    # Two payment families coexist with very different config shapes:
    #
    # - **EPay** (``channel_code != "trc20"``): one ``PaymentChannel``
    #   row per 码商 carries merchant credentials and a notify_url
    #   hostname (``BILLING_PUBLIC_BASE_URL``) the 码商 POSTs back to.
    # - **TRC20** (``channel_code == "trc20"``): singleton, no DB row
    #   (see ``ops/billing/db.py`` ``PaymentChannel`` docstring —
    #   "TRC20 is NOT represented here"). Configured wholly in env via
    #   :mod:`ops.billing.trc20_config`. No webhook, so
    #   ``BILLING_PUBLIC_BASE_URL`` is irrelevant here.
    #
    # The pre-2026-05-01 implementation always took the EPay path,
    # which 404'd TRC20 checkouts in production after Phase A.2 wired
    # the env vars. Branch early to keep both paths cleanly isolated.
    is_trc20 = body.channel_code == "trc20"
    channel: PaymentChannel | None
    if is_trc20:
        if not trc20_config.BILLING_TRC20_ENABLED:
            raise HTTPException(
                status_code=503,
                detail=(
                    "TRC20 channel is disabled. Set "
                    "BILLING_TRC20_ENABLED=true and configure the "
                    "BILLING_TRC20_{RECEIVE_ADDRESS, "
                    "RATE_FEN_PER_USDT, MEMO_SALT} env vars."
                ),
            )
        channel = None
        provider_field = "trc20"
    else:
        channel = db.execute(
            select(PaymentChannel).where(
                PaymentChannel.channel_code == body.channel_code
            )
        ).scalar_one_or_none()
        if channel is None:
            raise HTTPException(
                status_code=404,
                detail=f"payment channel {body.channel_code!r} not found",
            )
        if not channel.enabled:
            raise HTTPException(
                status_code=409,
                detail=f"payment channel {body.channel_code!r} is disabled",
            )
        provider_field = f"epay:{body.channel_code}"

    # Resolve plans referenced by the cart. One query, no N+1.
    plan_ids = {line.plan_id for line in body.lines}
    plans: dict[int, Plan] = {
        p.id: p
        for p in db.execute(
            select(Plan).where(Plan.id.in_(plan_ids))
        ).scalars()
    }

    cart = [
        CartLine(plan_id=line.plan_id, quantity=line.quantity)
        for line in body.lines
    ]
    try:
        total_fen = compute_cart_total_fen(cart, plans)
    except InvalidCart as exc:
        raise HTTPException(
            status_code=422, detail={"reason": exc.reason, "message": str(exc)}
        ) from exc

    # Public base URL is an EPay-only requirement — the 码商 POSTs
    # back to it. Without one, the generated notify_url is garbage
    # and no webhook ever arrives. TRC20 is poll-only (no webhook),
    # so this gate must NOT apply to TRC20 checkouts.
    if not is_trc20 and not billing_config.BILLING_PUBLIC_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail=(
                "BILLING_PUBLIC_BASE_URL is not configured. EPay 码商 "
                "cannot reach webhooks without a public origin."
            ),
        )

    now = datetime.now(UTC).replace(tzinfo=None)
    subject = body.subject or _derive_subject(cart, plans)

    invoice = Invoice(
        user_id=body.user_id,
        total_cny_fen=total_fen,
        state="created",
        provider=provider_field,
        created_at=now,
        expires_at=now + CHECKOUT_PAYMENT_WINDOW,
    )
    for line, plan in zip(cart, (plans[c.plan_id] for c in cart), strict=True):
        invoice.lines.append(
            InvoiceLine(
                plan_id=line.plan_id,
                quantity=line.quantity,
                unit_price_fen_at_purchase=plan.price_cny_fen,
            )
        )
    db.add(invoice)
    db.flush()  # need invoice.id for provider_invoice_id embedding

    # created → pending
    transition(
        db,
        invoice,
        INVOICE_STATE_PENDING,
        event_type="invoice_created",
        payload={
            "channel_code": body.channel_code,
            "line_count": len(cart),
            "total_fen": total_fen,
        },
        now=now,
    )

    if is_trc20:
        provider = get_provider("trc20")
    else:
        provider = get_provider(
            "epay",
            channel=channel,
            callback_base_url=billing_config.BILLING_PUBLIC_BASE_URL,
        )

    try:
        result = await provider.create_invoice(
            invoice_id=invoice.id,
            amount_cny_fen=total_fen,
            subject=subject,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except Exception as exc:  # noqa: BLE001  # provider-side misconfig
        logger.exception(
            "provider.create_invoice failed for channel=%s invoice=%s",
            body.channel_code,
            invoice.id,
        )
        # pending → failed; audit gets the exception shape.
        try:
            transition(
                db,
                invoice,
                "failed",
                event_type="provider_submit_failed",
                payload={"error": str(exc)},
                now=datetime.now(UTC).replace(tzinfo=None),
            )
        except InvoiceStateError:
            pass
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"payment provider rejected invoice creation: {exc}",
        ) from exc

    invoice.payment_url = result.payment_url
    invoice.provider_invoice_id = result.provider_invoice_id

    # TRC20 surfaces its memo + expected USDT amount via
    # ``CreateInvoiceResult.extra_payload``. Persist them onto the
    # invoice so the dashboard's TRC20 detail page (and the trc20
    # poller) can read them straight off the row without parsing
    # PaymentEvent payloads. EPay leaves these columns NULL.
    if is_trc20:
        invoice.trc20_memo = result.extra_payload.get("memo")
        invoice.trc20_expected_amount_millis = result.extra_payload.get(
            "expected_amount_millis"
        )

    # pending → awaiting_payment
    transition(
        db,
        invoice,
        INVOICE_STATE_AWAITING_PAYMENT,
        event_type="provider_submit_succeeded",
        payload={
            "provider_invoice_id": result.provider_invoice_id,
            **result.extra_payload,
        },
        now=datetime.now(UTC).replace(tzinfo=None),
    )
    db.commit()
    db.refresh(invoice)

    return CheckoutOut(
        invoice_id=invoice.id,
        total_cny_fen=invoice.total_cny_fen,
        payment_url=invoice.payment_url or "",
        provider_invoice_id=invoice.provider_invoice_id or "",
        state=invoice.state,
        expires_at=invoice.expires_at,
        trc20_memo=invoice.trc20_memo,
        trc20_expected_amount_millis=invoice.trc20_expected_amount_millis,
        trc20_receive_address=(
            result.extra_payload.get("receive_address") if is_trc20 else None
        ),
    )


# ---------------------------------------------------------------------
# EPay webhook
# ---------------------------------------------------------------------


@checkout_router.post(
    "/webhook/epay/{channel_code}",
    include_in_schema=True,
)
async def epay_webhook(
    channel_code: str,
    request: Request,
    db: DBDep,
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> Response:
    """Receive an EPay-protocol webhook.

    Unauthenticated at the HTTP layer. Authenticity comes from:

    1. MD5 signature over the request params using the channel's
       merchant_key (verified by :class:`EPayProvider.handle_webhook`)
    2. Optional IP allowlist from
       ``PaymentChannel.extra_config_json["allowed_ips"]`` (list of
       IPv4/IPv6 literals or CIDRs; missing / empty → open)

    Response body is the literal string ``"success"`` per 码商
    convention; any other body is treated as failure and retried
    up to 10 times with exponential backoff. That means:

    - invalid sign → respond with 400 (码商 will retry a few times;
      but a sign mismatch from a genuine 码商 indicates merchant_key
      rotation, so we want loud failure)
    - replay / already-processed → **still respond "success"** so
      the 码商 stops retrying
    - unknown trade_status → respond "success" as well (we observed
      the event but it's not actionable) — avoids retry storms
    """
    channel = db.execute(
        select(PaymentChannel).where(
            PaymentChannel.channel_code == channel_code
        )
    ).scalar_one_or_none()
    if channel is None:
        raise HTTPException(
            status_code=404,
            detail=f"payment channel {channel_code!r} not found",
        )
    if not channel.enabled:
        # 410 Gone (not 404): the channel exists but is intentionally
        # off. Vendors retry 404s 10x with backoff before giving up;
        # 410 is the standardised "stop retrying, this is permanent
        # for now" signal. Re-enabling the channel will produce a
        # fresh 200 on the next webhook anyway.
        raise HTTPException(
            status_code=410,
            detail=f"payment channel {channel_code!r} is disabled",
        )

    client_ip = _resolve_client_ip(request, x_forwarded_for)
    if not _ip_is_allowed(channel, client_ip):
        # 403 (not 400) so 码商 stops retrying — this is a deliberate
        # block, not a transient failure.
        raise HTTPException(
            status_code=403,
            detail=(
                f"webhook caller {client_ip!r} not in allowed_ips for "
                f"channel {channel_code!r}"
            ),
        )

    # Parse body as form-urlencoded (default content-type from 码商).
    # Fall back to query params when body is empty — a few vendors use
    # GET-style notify regardless of METHOD; being lenient here makes
    # integration less brittle.
    raw_body = await request.body()
    form_data = await request.form()
    params: dict[str, str] = {
        k: v for k, v in form_data.items() if isinstance(v, str)
    }
    if not params:
        params = dict(request.query_params)

    provider = get_provider(
        "epay",
        channel=channel,
        callback_base_url=billing_config.BILLING_PUBLIC_BASE_URL
        or "https://unset.invalid",
    )

    try:
        outcome = await provider.handle_webhook(params, raw_body)
    except InvalidSignature as exc:
        logger.warning(
            "epay webhook sign check failed channel=%s: %s", channel_code, exc
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnhandledEventType as exc:
        logger.info(
            "epay webhook non-actionable event channel=%s: %s",
            channel_code,
            exc,
        )
        # Return success to stop 码商 retrying; we observed it.
        return Response(content=WEBHOOK_SUCCESS_BODY, media_type="text/plain")

    invoice = db.get(Invoice, outcome.invoice_id)
    if invoice is None:
        # Invoice disappeared between submit and webhook — logically
        # impossible but surface explicitly rather than crashing.
        raise HTTPException(
            status_code=404,
            detail=f"invoice {outcome.invoice_id} not found",
        )

    first_time = record_webhook_seen(
        db,
        invoice_id=invoice.id,
        provider=f"epay:{channel_code}",
        payload={"provider_event_id": outcome.provider_event_id},
    )
    if not first_time:
        db.commit()  # commit the dedup check marker (noop if no write)
        logger.info(
            "epay webhook replay channel=%s invoice=%s ignored",
            channel_code,
            invoice.id,
        )
        return Response(content=WEBHOOK_SUCCESS_BODY, media_type="text/plain")

    try:
        transition(
            db,
            invoice,
            outcome.new_state,
            event_type="webhook_epay",
            payload={
                "provider_event_id": outcome.provider_event_id,
                "raw": outcome.raw,
            },
        )
    except InvoiceStateError as exc:
        # Invoice already terminal or on a path that forbids the
        # target state. Still reply "success" so the 码商 halts — the
        # audit log captures the mismatch for post-hoc inspection.
        logger.warning(
            "epay webhook state conflict channel=%s invoice=%s: %s",
            channel_code,
            invoice.id,
            exc,
        )
        db.rollback()
        return Response(content=WEBHOOK_SUCCESS_BODY, media_type="text/plain")

    db.commit()
    return Response(content=WEBHOOK_SUCCESS_BODY, media_type="text/plain")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _derive_subject(cart: list[CartLine], plans: dict[int, Plan]) -> str:
    """Pick a short human-readable subject for the payment page.

    Single-line cart: the plan's display_name_en. Multi-line:
    ``"Plan A + Plan B"`` truncated at 128 chars (EPay param limit).
    """
    if not cart:
        return "Order"
    names = [plans[line.plan_id].display_name_en for line in cart]
    subject = " + ".join(names)
    return subject[:128]


def _resolve_client_ip(request: Request, x_forwarded_for: str | None) -> str:
    """Extract the caller's IP for the per-channel ``allowed_ips`` check.

    Threat: ``/api/billing/webhook/epay/{code}`` is unauthenticated at
    the HTTP layer (the MD5 sign is the primary defence). If we trusted
    ``X-Forwarded-For`` from any caller, an attacker on the public
    internet could spoof the header and bypass the per-channel
    ``allowed_ips`` allowlist — turning a documented "double 防线"
    into security theatre.

    Rule: only honour ``X-Forwarded-For`` when the immediate transport
    peer is on the operator-curated ``BILLING_TRUSTED_PROXIES`` CIDR
    list (``ops.billing.config``). Otherwise the IP we use is the
    transport peer regardless of any header the caller set.

    A panel sitting directly on the public internet (no reverse proxy,
    empty ``BILLING_TRUSTED_PROXIES``) therefore checks ``allowed_ips``
    against the real source IP, which is the correct behaviour.
    """
    peer = request.client.host if request.client is not None else ""

    if x_forwarded_for and _peer_is_trusted_proxy(peer):
        # Format: "client, proxy1, proxy2". We want the leftmost (the
        # original caller as recorded by our trusted proxy).
        forwarded = x_forwarded_for.split(",")[0].strip()
        if forwarded:
            return forwarded
        # Trusted proxy sent an empty XFF — fall back to peer rather
        # than a blank string. Trusted proxies don't usually do this,
        # but the conservative choice is "use what we know".
        return peer

    return peer


def _peer_is_trusted_proxy(peer_ip: str) -> bool:
    """True iff ``peer_ip`` falls within ``BILLING_TRUSTED_PROXIES``.

    Reads the tuple from the live module (not a snapshot at import
    time) so ``_reload_for_tests`` / live env changes take effect.
    """
    if not peer_ip:
        return False
    if not billing_config.BILLING_TRUSTED_PROXIES:
        return False
    try:
        peer = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    return any(peer in cidr for cidr in billing_config.BILLING_TRUSTED_PROXIES)


def _ip_is_allowed(channel: PaymentChannel, client_ip: str) -> bool:
    """True if ``client_ip`` matches any entry in the channel's
    ``allowed_ips`` config, or if no allowlist is configured.

    Entries can be literals (``"1.2.3.4"``) or CIDRs (``"1.2.3.0/24"``).
    Malformed entries are skipped (logged) rather than crashing the
    webhook — the operator's typo shouldn't break production.
    """
    allowed = channel.get_extra_config("allowed_ips")
    if not allowed:
        return True
    if not client_ip:
        return False
    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in allowed:
        try:
            if "/" in entry:
                if client_addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif client_addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            logger.warning(
                "malformed allowed_ips entry %r on channel %s",
                entry,
                channel.channel_code,
            )
            continue
    return False


__all__ = ["checkout_router", "CHECKOUT_PAYMENT_WINDOW"]
