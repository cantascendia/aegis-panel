"""
Tests for ``ops.billing.pricing`` — pure-function cart math.

No DB access, no network; all inputs are constructed inline. These
tests exercise the public contract called by A.1.3 admin REST and
A.4 user checkout UI.
"""

from __future__ import annotations

import pytest

from ops.billing.db import (
    PLAN_KIND_FIXED,
    PLAN_KIND_FLEXIBLE_DURATION,
    PLAN_KIND_FLEXIBLE_TRAFFIC,
    Plan,
)
from ops.billing.pricing import (
    CartLine,
    InvalidCart,
    UserGrant,
    compute_cart_total_fen,
    compute_user_grant,
    convert_fen_to_usdt_millis,
    validate_cart_line,
)

# ---------------------------------------------------------------------
# Helpers — construct Plans without touching the DB
# ---------------------------------------------------------------------


def _fixed_plan(
    pid: int, gb: int | None, days: int | None, fen: int, enabled: bool = True
) -> Plan:
    p = Plan(
        id=pid,
        operator_code=f"fixed-{pid}",
        display_name_en="Test Fixed",
        display_name_i18n={},
        kind=PLAN_KIND_FIXED,
        data_limit_gb=gb,
        duration_days=days,
        price_cny_fen=fen,
        enabled=enabled,
        sort_order=0,
    )
    return p


def _flex_traffic(
    pid: int, gb_per_unit: int, fen_per_unit: int, enabled: bool = True
) -> Plan:
    return Plan(
        id=pid,
        operator_code=f"flex-gb-{pid}",
        display_name_en="Traffic Addon",
        display_name_i18n={},
        kind=PLAN_KIND_FLEXIBLE_TRAFFIC,
        data_limit_gb=gb_per_unit,
        duration_days=None,
        price_cny_fen=fen_per_unit,
        enabled=enabled,
        sort_order=0,
    )


def _flex_duration(
    pid: int, days_per_unit: int, fen_per_unit: int, enabled: bool = True
) -> Plan:
    return Plan(
        id=pid,
        operator_code=f"flex-day-{pid}",
        display_name_en="Duration Addon",
        display_name_i18n={},
        kind=PLAN_KIND_FLEXIBLE_DURATION,
        data_limit_gb=None,
        duration_days=days_per_unit,
        price_cny_fen=fen_per_unit,
        enabled=enabled,
        sort_order=0,
    )


# ---------------------------------------------------------------------
# validate_cart_line
# ---------------------------------------------------------------------


def test_validate_accepts_fixed_qty_1():
    plan = _fixed_plan(1, gb=30, days=30, fen=5000)
    validate_cart_line(CartLine(plan_id=1, quantity=1), plan)  # no raise


def test_validate_rejects_disabled_plan():
    plan = _fixed_plan(1, gb=30, days=30, fen=5000, enabled=False)
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=1), plan)
    assert exc.value.reason == "plan_disabled"


def test_validate_rejects_quantity_zero():
    plan = _fixed_plan(1, gb=30, days=30, fen=5000)
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=0), plan)
    assert exc.value.reason == "bad_quantity"


def test_validate_rejects_fixed_plan_quantity_gt_1():
    plan = _fixed_plan(1, gb=30, days=30, fen=5000)
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=3), plan)
    assert exc.value.reason == "fixed_plan_quantity"


def test_validate_rejects_fixed_plan_with_both_dims_null():
    plan = _fixed_plan(1, gb=None, days=None, fen=5000)
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=1), plan)
    assert exc.value.reason == "fixed_plan_empty"


def test_validate_accepts_flex_traffic_normal():
    plan = _flex_traffic(1, gb_per_unit=1, fen_per_unit=50)
    validate_cart_line(CartLine(plan_id=1, quantity=20), plan)  # no raise


def test_validate_rejects_flex_traffic_missing_gb():
    plan = _flex_traffic(1, gb_per_unit=0, fen_per_unit=50)
    # simulate malformed: pretend gb is None (operator-side bug)
    plan.data_limit_gb = None
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=1), plan)
    assert exc.value.reason == "flexible_traffic_missing_gb"


def test_validate_rejects_flex_traffic_with_days_set():
    plan = _flex_traffic(1, gb_per_unit=1, fen_per_unit=50)
    plan.duration_days = 7  # malformed by operator
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=1), plan)
    assert exc.value.reason == "flexible_traffic_has_days"


def test_validate_accepts_flex_duration_normal():
    plan = _flex_duration(1, days_per_unit=1, fen_per_unit=100)
    validate_cart_line(CartLine(plan_id=1, quantity=14), plan)  # no raise


def test_validate_rejects_flex_duration_with_gb_set():
    plan = _flex_duration(1, days_per_unit=1, fen_per_unit=100)
    plan.data_limit_gb = 10
    with pytest.raises(InvalidCart) as exc:
        validate_cart_line(CartLine(plan_id=1, quantity=1), plan)
    assert exc.value.reason == "flexible_duration_has_gb"


# ---------------------------------------------------------------------
# compute_cart_total_fen
# ---------------------------------------------------------------------


def test_total_empty_cart_raises():
    with pytest.raises(InvalidCart) as exc:
        compute_cart_total_fen([], {})
    assert exc.value.reason == "empty_cart"


def test_total_unknown_plan_id_raises():
    with pytest.raises(InvalidCart) as exc:
        compute_cart_total_fen([CartLine(plan_id=999, quantity=1)], {})
    assert exc.value.reason == "unknown_plan_id"


def test_total_single_fixed_plan():
    p = _fixed_plan(1, gb=30, days=30, fen=5000)
    total = compute_cart_total_fen([CartLine(plan_id=1, quantity=1)], {1: p})
    assert total == 5000


def test_total_mixed_cart_fixed_plus_flex_traffic():
    """Starter ¥50 + 20 GB @ ¥0.50 = ¥60 = 6000 fen."""
    fixed = _fixed_plan(1, gb=30, days=30, fen=5000)
    addon = _flex_traffic(2, gb_per_unit=1, fen_per_unit=50)
    total = compute_cart_total_fen(
        [
            CartLine(plan_id=1, quantity=1),
            CartLine(plan_id=2, quantity=20),
        ],
        {1: fixed, 2: addon},
    )
    assert total == 5000 + 50 * 20  # 6000


def test_total_flexible_duration_multiplies_correctly():
    addon = _flex_duration(1, days_per_unit=1, fen_per_unit=100)
    total = compute_cart_total_fen(
        [CartLine(plan_id=1, quantity=14)], {1: addon}
    )
    assert total == 100 * 14


# ---------------------------------------------------------------------
# compute_user_grant
# ---------------------------------------------------------------------


def test_grant_fixed_plan_returns_both_dims():
    p = _fixed_plan(1, gb=30, days=30, fen=5000)
    g = compute_user_grant([CartLine(plan_id=1, quantity=1)], {1: p})
    assert g == UserGrant(data_limit_gb_delta=30, duration_days_delta=30)


def test_grant_fixed_plan_with_null_dim_uses_zero():
    """Fixed plan with only data_limit_gb → days stays 0."""
    p = _fixed_plan(1, gb=100, days=None, fen=8000)
    g = compute_user_grant([CartLine(plan_id=1, quantity=1)], {1: p})
    assert g == UserGrant(data_limit_gb_delta=100, duration_days_delta=0)


def test_grant_flex_traffic_contributes_gb_only():
    p = _flex_traffic(1, gb_per_unit=1, fen_per_unit=50)
    g = compute_user_grant([CartLine(plan_id=1, quantity=20)], {1: p})
    assert g == UserGrant(data_limit_gb_delta=20, duration_days_delta=0)


def test_grant_flex_duration_contributes_days_only():
    p = _flex_duration(1, days_per_unit=1, fen_per_unit=100)
    g = compute_user_grant([CartLine(plan_id=1, quantity=7)], {1: p})
    assert g == UserGrant(data_limit_gb_delta=0, duration_days_delta=7)


def test_grant_mixed_cart_aggregates():
    """Starter 30/30 + 20GB addon + 5 days addon."""
    fixed = _fixed_plan(1, gb=30, days=30, fen=5000)
    traffic = _flex_traffic(2, gb_per_unit=1, fen_per_unit=50)
    duration = _flex_duration(3, days_per_unit=1, fen_per_unit=100)
    g = compute_user_grant(
        [
            CartLine(plan_id=1, quantity=1),
            CartLine(plan_id=2, quantity=20),
            CartLine(plan_id=3, quantity=5),
        ],
        {1: fixed, 2: traffic, 3: duration},
    )
    assert g == UserGrant(
        data_limit_gb_delta=30 + 20, duration_days_delta=30 + 5
    )


# ---------------------------------------------------------------------
# convert_fen_to_usdt_millis
# ---------------------------------------------------------------------


def test_usdt_conversion_exact():
    # At rate 1000 fen/USDT (i.e. ¥10 = $1): 5000 fen = 5 USDT = 5000 millis
    assert convert_fen_to_usdt_millis(5000, 1000) == 5000


def test_usdt_conversion_rounds_up():
    # At rate 720 fen/USDT: 880 fen = 1222.22 millis → should round UP
    # so operator is never short. ceil = 1223.
    assert convert_fen_to_usdt_millis(880, 720) == 1223


def test_usdt_conversion_zero_fen_is_zero():
    assert convert_fen_to_usdt_millis(0, 720) == 0


def test_usdt_conversion_rejects_zero_rate():
    with pytest.raises(ValueError):
        convert_fen_to_usdt_millis(5000, 0)


def test_usdt_conversion_rejects_negative_fen():
    with pytest.raises(ValueError):
        convert_fen_to_usdt_millis(-1, 720)
