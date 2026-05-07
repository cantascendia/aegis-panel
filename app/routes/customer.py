"""Customer-facing API — `/api/customers/*`.

Track B endpoints powering the Nilou customer portal at `/portal/`. Each
customer authenticates by submitting their subscription URL once
(`POST /sub-login`); the backend validates `(username, key)` against the
existing User row and issues a 15-min JWT scoped `access: "customer"`.
Subsequent calls (`GET /me`, `GET /me/traffic`, `GET /me/invoices`) use
that JWT.

Forbidden-path scope (`.claude/rules/forbidden-paths.md`):
* This file requires double-sign before merge
* Any change must trigger codex cross-review
* See `app/utils/customer_auth.py` for the JWT layer (also forbidden)

Why a separate route file (vs adding to `app/routes/user.py`):
* `user.py` is upstream Marzneshin, admin-only — different audience,
  different auth model. Keeping customer endpoints separate keeps the
  upstream-sync diff at zero.
* Mounted via `hardening/panel/middleware.py:apply_panel_hardening`,
  matching the same pattern as audit / billing / iplimit / sni / health.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import crud
from app.dependencies import get_db
from app.utils.customer_auth import (
    create_customer_token,
    get_customer_payload,
    parse_sub_url,
)

router = APIRouter(prefix="/api/customers", tags=["customer"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SubLoginRequest(BaseModel):
    """Customer login payload — single field: their subscription URL."""

    sub_url: str = Field(..., min_length=8, max_length=2048)


class SubLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    expires_in_seconds: int = 15 * 60


class CustomerMeResponse(BaseModel):
    """What a customer sees about themselves on the portal dashboard."""

    user_id: int
    username: str
    used_traffic: int
    data_limit: int | None
    data_limit_reset_strategy: str | None
    expire_date: datetime | None
    expire_strategy: str | None
    is_active: bool
    online_at: datetime | None
    note: str | None


# ---------------------------------------------------------------------------
# Auth dependency — derive User from JWT
# ---------------------------------------------------------------------------


from fastapi.security import OAuth2PasswordBearer  # noqa: E402

customer_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/customers/sub-login",
    scheme_name="customer",
    auto_error=False,
)


def get_current_customer(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Depends(customer_oauth2_scheme)],
):
    """Validate a customer JWT, return the User row.

    Raises 401 on:
    * No bearer token
    * Bad / expired JWT
    * Wrong access claim (admin tokens can't be reused here)
    * User no longer exists, removed, or disabled
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing customer credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = get_customer_payload(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired customer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload["user_id"]
    user = db.get(_user_model(), user_id)
    if user is None or getattr(user, "removed", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def _user_model():
    """Lazy import — avoids circular import with crud during module load."""
    from app.db.models import User

    return User


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sub-login", response_model=SubLoginResponse)
def sub_login(payload: SubLoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Exchange a subscription URL for a 15-min customer JWT."""
    parsed = parse_sub_url(payload.sub_url)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription URL is malformed",
        )

    user = crud.get_user(db, parsed.username)
    if user is None or getattr(user, "removed", False):
        # Same generic 401 as a key mismatch — don't leak which usernames exist.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subscription URL",
        )

    if user.key != parsed.key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subscription URL",
        )

    return SubLoginResponse(
        access_token=create_customer_token(user.id),
        user_id=user.id,
        username=user.username,
    )


@router.get("/me", response_model=CustomerMeResponse)
def get_me(user=Depends(get_current_customer)):
    """Return the authenticated customer's own state."""
    return CustomerMeResponse(
        user_id=user.id,
        username=user.username,
        used_traffic=getattr(user, "used_traffic", 0) or 0,
        data_limit=user.data_limit,
        data_limit_reset_strategy=getattr(
            user.data_limit_reset_strategy, "value", user.data_limit_reset_strategy
        )
        if user.data_limit_reset_strategy
        else None,
        expire_date=user.expire_date,
        expire_strategy=getattr(user.expire_strategy, "value", user.expire_strategy)
        if user.expire_strategy
        else None,
        is_active=getattr(user, "is_active", False),
        online_at=getattr(user, "online_at", None),
        note=user.note,
    )
