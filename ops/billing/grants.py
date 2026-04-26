"""
Grant application — translate a paid invoice into ``User`` quota mutations.

Purely additive: a paid grant **extends** the user's plan (more bytes /
more days) rather than replacing it. New users start from
``data_limit=NULL`` / ``expire_date=NULL``; the helper handles those
NULL-baselines correctly so the ``apply_paid_invoices`` scheduler can
operate on any user without a pre-init step.

Why a separate module from ``pricing.py``?
------------------------------------------
- ``pricing.py`` is **pre-payment**: validates carts, computes totals,
  produces a ``UserGrant`` (delta in GB + days). Pure math, no User row.
- ``grants.py`` is **post-payment**: takes the ``UserGrant`` and a
  ``User`` row and applies it. Touches ``User.data_limit`` /
  ``User.expire_date`` / ``User.expire_strategy``.

Splitting them keeps ``pricing.py`` import-clean for the cart-checkout
path (no SQLAlchemy Plan needed when the caller already has the lines).
``grants.py`` owns the policy decisions about how a grant lands on an
existing user state.

Unit conversion
---------------
``UserGrant.data_limit_gb_delta`` is an integer in **binary GB**
(1 GB = 1024**3 bytes) because that's the canonical unit upstream uses
in ``app/routes/user.py``: ``data_limit must be in Bytes, e.g.
1073741824B = 1GB``. We convert at the boundary here so callers can
think in human GB.

Expire strategy policy
----------------------
Three states a user can be in, three rules:

- ``FIXED_DATE`` — extend ``expire_date`` from ``max(now, expire_date)``
  by ``duration_days_delta``. The ``max`` matters: a user whose plan
  already expired buying a renewal should restart their clock from
  *now*, not from the lapsed date. Without it, an offline user buying
  the day after expiry would receive a 30-day grant where the first
  ~24h were already in the past.

- ``NEVER`` (or ``activated=True`` no-expire user) — granting any
  ``duration_days_delta`` switches them to ``FIXED_DATE`` anchored at
  ``now + days``. A grant of 0 days leaves the strategy untouched.

- ``START_ON_FIRST_USE`` — same switch as ``NEVER``: a grant promotes
  the user to ``FIXED_DATE``. The "wait until first use" semantic was
  meaningful before payment; once they've paid, anchor the timer.

These policies are documented in ``SPEC-billing-mvp.md`` §"A.5 grant
application" so future operators reading the audit trail understand
why ``expire_strategy`` flipped silently.

Idempotency
-----------
``apply_grant_to_user`` is **not** idempotent on its own — calling it
twice would extend the user twice. Idempotency is enforced one level
up by the state-machine guard in :mod:`ops.billing.states.transition`:
``paid → applied`` is a one-way transition, and re-running
``apply_paid_invoices`` against an already-applied invoice rejects
before reaching this helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.user import UserExpireStrategy
from ops.billing.pricing import UserGrant

_BYTES_PER_GB = 1024**3


@dataclass(frozen=True)
class AppliedGrant:
    """Snapshot of what changed on the user, for the PaymentEvent
    audit log. Captured AFTER mutation so the row reflects the actual
    DB-visible new values (not predicted ones).

    Stored as the ``payload`` of the ``state_applied`` event so an
    operator reading the audit log can answer "what did this user
    receive from invoice 4321?" without re-deriving the math.
    """

    data_limit_bytes_before: int | None
    data_limit_bytes_after: int | None
    expire_strategy_before: str
    expire_strategy_after: str
    expire_date_before: datetime | None
    expire_date_after: datetime | None
    grant_gb_delta: int
    grant_days_delta: int


def apply_grant_to_user(
    user_row: object,  # SQLAlchemy User; typed as object to dodge cyclic import
    grant: UserGrant,
    *,
    now: datetime,
) -> AppliedGrant:
    """Mutate ``user_row`` in place to reflect ``grant``; return what changed.

    Caller (``apply_paid_invoices``) owns the ``Session``; this helper
    only touches in-Python attributes. The session.commit happens after
    the matching ``transition(invoice, "applied")`` so DB and state
    machine flush together.

    Behavior
    --------
    - ``data_limit``: bytes-additive. ``None`` is treated as 0 baseline,
      so a previously-unlimited user receiving a grant becomes
      *limited* to exactly the grant size — operator should not sell
      flexible-traffic addons to unlimited users (operator policy
      enforced at admin UI, not here).
    - ``expire_date``: see module docstring. ``UserExpireStrategy``
      may flip from NEVER/START_ON_FIRST_USE to FIXED_DATE.
    - Grants of 0 GB and 0 days (e.g. a free-trial plan with no
      duration) are no-ops on the User but still record an
      ``AppliedGrant`` snapshot so the audit log shows the apply
      happened.
    """
    # Snapshot before
    before_bytes = user_row.data_limit
    before_strategy = (
        user_row.expire_strategy.value
        if hasattr(user_row.expire_strategy, "value")
        else str(user_row.expire_strategy)
    )
    before_date = user_row.expire_date

    # ---- data_limit (bytes-additive) ----
    if grant.data_limit_gb_delta:
        baseline = user_row.data_limit or 0
        user_row.data_limit = (
            baseline + grant.data_limit_gb_delta * _BYTES_PER_GB
        )

    # ---- expire_date / expire_strategy ----
    if grant.duration_days_delta:
        delta = timedelta(days=grant.duration_days_delta)
        # Compare against UserExpireStrategy enum values (StrEnum, so
        # `==` works against either the enum or its string form).
        if user_row.expire_strategy == UserExpireStrategy.FIXED_DATE:
            base = user_row.expire_date or now
            if base < now:
                base = now
            user_row.expire_date = base + delta
        else:
            # NEVER or START_ON_FIRST_USE: anchor a fresh fixed window
            # starting now.
            user_row.expire_strategy = UserExpireStrategy.FIXED_DATE
            user_row.expire_date = now + delta
            # `usage_duration` / `activation_deadline` are
            # START_ON_FIRST_USE-specific; FIXED_DATE doesn't read them
            # but leaving stale values is confusing in admin UIs. Clear
            # them to match the "set" pathway in
            # ``app/db/crud.py::update_user``.
            user_row.usage_duration = None
            user_row.activation_deadline = None

    after_strategy = (
        user_row.expire_strategy.value
        if hasattr(user_row.expire_strategy, "value")
        else str(user_row.expire_strategy)
    )
    return AppliedGrant(
        data_limit_bytes_before=before_bytes,
        data_limit_bytes_after=user_row.data_limit,
        expire_strategy_before=before_strategy,
        expire_strategy_after=after_strategy,
        expire_date_before=before_date,
        expire_date_after=user_row.expire_date,
        grant_gb_delta=grant.data_limit_gb_delta,
        grant_days_delta=grant.duration_days_delta,
    )


__all__ = ["AppliedGrant", "apply_grant_to_user"]
