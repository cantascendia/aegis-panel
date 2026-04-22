"""
Pricing engine — pure functions, no I/O, no DB.

Called by:
- Cart checkout flow (A.4 user UX): to compute and display total
  before creating an invoice
- Invoice creation (A.1.3 admin REST + A.4 user REST): to lock the
  price into ``InvoiceLine.unit_price_fen_at_purchase`` at order
  time
- TRC20 provider (A.3): ``convert_fen_to_usdt_millis`` to translate
  CNY to the on-chain USDT amount at invoice creation time with a
  rate snapshot

Invariants (SPEC-billing-mvp.md):

- All money math is **integer**. ``price_cny_fen`` everywhere
  (1 fen = 1/100 CNY, so ``880 == ¥8.80``). USDT amounts are
  ``int`` millis (1/1000 USDT).
- Fixed plans MUST have ``quantity == 1`` on a cart line; flexible
  plans MUST have ``quantity >= 1``. ``validate_cart_line`` enforces;
  ``compute_cart_total_fen`` calls validate for every line.
- Cart math is deterministic and platform-independent: no
  floating-point, no locale-aware rounding, no timezone dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from ops.billing.db import (
    PLAN_KIND_FIXED,
    PLAN_KIND_FLEXIBLE_DURATION,
    PLAN_KIND_FLEXIBLE_TRAFFIC,
    Plan,
)


class InvalidCart(ValueError):
    """Raised when a cart line is internally inconsistent (e.g.
    fixed plan with quantity > 1, flexible plan with bad dimension,
    missing/disabled plan). Carries a typed ``.reason`` attribute
    so REST handlers can map to specific 400 error codes without
    string-matching."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


# ---------------------------------------------------------------------
# Dataclasses — transport only, not persisted
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class CartLine:
    """What the user/admin wants to buy, pre-invoice.

    Resolves to an ``InvoiceLine`` row at checkout time; this
    dataclass is the interchange shape between UI → REST → pricing
    engine → DB.
    """

    plan_id: int
    quantity: int


@dataclass(frozen=True)
class UserGrant:
    """What a paid invoice entitles the user to. Computed by
    ``compute_user_grant``; applied to ``User.data_limit`` and
    ``User.expire_date`` by the ``apply_paid_invoices`` scheduler
    (A.5).

    Both values are **additive** — they extend the user's existing
    quota, not replace it. For a brand-new user with no prior plan,
    the caller is responsible for initializing ``data_limit=0`` and
    ``expire_date=now`` before adding the grant.
    """

    data_limit_gb_delta: int
    duration_days_delta: int


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def validate_cart_line(line: CartLine, plan: Plan) -> None:
    """Raise ``InvalidCart`` if the line + plan combo is malformed.

    Checks:
    - plan exists and is enabled
    - quantity >= 1
    - fixed plans use quantity == 1
    - flexible_traffic plans have ``data_limit_gb`` set and
      ``duration_days`` null
    - flexible_duration plans have ``duration_days`` set and
      ``data_limit_gb`` null
    """
    if not plan.enabled:
        raise InvalidCart(
            "plan_disabled",
            f"Plan {plan.operator_code!r} is disabled and cannot "
            f"appear in a new cart.",
        )
    if line.quantity < 1:
        raise InvalidCart(
            "bad_quantity",
            f"quantity must be >= 1, got {line.quantity}",
        )

    if plan.kind == PLAN_KIND_FIXED:
        if line.quantity != 1:
            raise InvalidCart(
                "fixed_plan_quantity",
                f"Fixed plan {plan.operator_code!r} must have "
                f"quantity == 1, got {line.quantity}. For multiple "
                f"periods, purchase the plan multiple times or "
                f"configure a longer-duration fixed plan.",
            )
        # Fixed plans need BOTH dimensions declared upfront.
        if plan.data_limit_gb is None and plan.duration_days is None:
            raise InvalidCart(
                "fixed_plan_empty",
                f"Fixed plan {plan.operator_code!r} must specify "
                f"at least one of data_limit_gb / duration_days.",
            )
    elif plan.kind == PLAN_KIND_FLEXIBLE_TRAFFIC:
        if plan.data_limit_gb is None:
            raise InvalidCart(
                "flexible_traffic_missing_gb",
                f"Flexible-traffic plan {plan.operator_code!r} must "
                f"have data_limit_gb set (per-unit GB).",
            )
        if plan.duration_days is not None:
            raise InvalidCart(
                "flexible_traffic_has_days",
                f"Flexible-traffic plan {plan.operator_code!r} must "
                f"NOT set duration_days (use flexible_duration for "
                f"day-based addons).",
            )
    elif plan.kind == PLAN_KIND_FLEXIBLE_DURATION:
        if plan.duration_days is None:
            raise InvalidCart(
                "flexible_duration_missing_days",
                f"Flexible-duration plan {plan.operator_code!r} must "
                f"have duration_days set (per-unit days).",
            )
        if plan.data_limit_gb is not None:
            raise InvalidCart(
                "flexible_duration_has_gb",
                f"Flexible-duration plan {plan.operator_code!r} must "
                f"NOT set data_limit_gb (use flexible_traffic for "
                f"GB-based addons).",
            )
    else:
        raise InvalidCart(
            "unknown_plan_kind",
            f"Plan {plan.operator_code!r} has unknown kind "
            f"{plan.kind!r}. See PLAN_KINDS in ops.billing.db.",
        )


# ---------------------------------------------------------------------
# Pricing math
# ---------------------------------------------------------------------


def compute_cart_total_fen(
    lines: list[CartLine], plans: dict[int, Plan]
) -> int:
    """Return cart total in integer fen.

    ``plans`` is a ``{plan_id: Plan}`` map the caller has already
    fetched — pricing is pure math, not a DB accessor. Raises
    ``InvalidCart`` (unknown plan id) or propagates the typed
    reasons from ``validate_cart_line``.

    Fixed plans contribute ``price_cny_fen`` once. Flexible plans
    contribute ``price_cny_fen * quantity`` (unit-priced).
    """
    if not lines:
        raise InvalidCart("empty_cart", "Cart has no lines.")

    total = 0
    for line in lines:
        plan = plans.get(line.plan_id)
        if plan is None:
            raise InvalidCart(
                "unknown_plan_id",
                f"plan_id {line.plan_id} not found in plan map. "
                f"Caller must fetch all referenced plans before "
                f"invoking compute_cart_total_fen.",
            )
        validate_cart_line(line, plan)
        total += plan.price_cny_fen * line.quantity
    return total


def compute_user_grant(
    lines: list[CartLine], plans: dict[int, Plan]
) -> UserGrant:
    """Aggregate across all lines → total (gb, days) delta the user
    will receive when the invoice is applied.

    Contributions:
    - fixed plan: quantity * (data_limit_gb or 0) GB + quantity *
      (duration_days or 0) days, where quantity is always 1
    - flexible_traffic: quantity * data_limit_gb GB, 0 days
    - flexible_duration: 0 GB, quantity * duration_days days
    """
    gb = 0
    days = 0
    for line in lines:
        plan = plans.get(line.plan_id)
        if plan is None:
            raise InvalidCart(
                "unknown_plan_id",
                f"plan_id {line.plan_id} not found in plan map",
            )
        # compute_cart_total_fen validates; but compute_user_grant may
        # also be called standalone (e.g. in apply_paid_invoices
        # task), so validate here too. Double-validation is cheap.
        validate_cart_line(line, plan)

        if plan.kind == PLAN_KIND_FIXED:
            gb += (plan.data_limit_gb or 0) * line.quantity
            days += (plan.duration_days or 0) * line.quantity
        elif plan.kind == PLAN_KIND_FLEXIBLE_TRAFFIC:
            # data_limit_gb is not None (validated)
            assert plan.data_limit_gb is not None
            gb += plan.data_limit_gb * line.quantity
        elif plan.kind == PLAN_KIND_FLEXIBLE_DURATION:
            assert plan.duration_days is not None
            days += plan.duration_days * line.quantity

    return UserGrant(data_limit_gb_delta=gb, duration_days_delta=days)


def convert_fen_to_usdt_millis(fen: int, rate_fen_per_usdt: int) -> int:
    """Convert integer fen to integer USDT-millis (1/1000 USDT).

    ``rate_fen_per_usdt`` is the operator-snapshotted cost of 1 USDT
    in fen, set at invoice-create time. E.g. 720 = 7.20 CNY/USDT.

    Rounds **up** on the remainder so the operator is never short
    of the displayed price. A user paying ¥8.80 at a 7.20 rate
    needs to pay ceil(880 * 1000 / 720) = ceil(1222.22) = 1223
    millis (≈ 1.223 USDT); the 0.78-fen over-pay is absorbed as
    operator upside.

    Raises ``ValueError`` on non-positive rate (callers should
    snapshot a live rate; zero/negative indicates a config bug, not
    a runtime condition worth swallowing).
    """
    if rate_fen_per_usdt <= 0:
        raise ValueError(
            f"rate_fen_per_usdt must be > 0, got {rate_fen_per_usdt}"
        )
    if fen < 0:
        raise ValueError(f"fen must be >= 0, got {fen}")
    # ceil(fen * 1000 / rate) without floats:
    numerator = fen * 1000
    return (numerator + rate_fen_per_usdt - 1) // rate_fen_per_usdt


__all__ = [
    "CartLine",
    "InvalidCart",
    "UserGrant",
    "compute_cart_total_fen",
    "compute_user_grant",
    "convert_fen_to_usdt_millis",
    "validate_cart_line",
]
