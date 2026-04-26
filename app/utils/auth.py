from datetime import UTC, datetime, timedelta
from typing import Union

import jwt

from app.config import get_secret_key
from app.config.env import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from app.utils._aegis_clocks import now_utc_naive


def create_admin_token(username: str, is_sudo=False) -> str:
    data = {
        "sub": username,
        "access": "sudo" if is_sudo else "admin",
        "iat": now_utc_naive(),
    }
    if JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0:
        expire = now_utc_naive() + timedelta(
            minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        data["exp"] = expire
    encoded_jwt = jwt.encode(data, get_secret_key(), algorithm="HS256")
    return encoded_jwt


def get_admin_payload(token: str) -> Union[dict, None]:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return

    username: str = payload.get("sub")
    access: str = payload.get("access")
    if not username or access not in ("admin", "sudo"):
        return
    try:
        # `datetime.utcfromtimestamp` is also Python 3.12-deprecated.
        # `datetime.fromtimestamp(ts, UTC)` returns aware UTC; strip
        # tzinfo to keep the same naive shape callers expect (matches
        # `now_utc_naive()` output and the DB columns it lands in).
        created_at = datetime.fromtimestamp(
            payload["iat"], UTC
        ).replace(tzinfo=None)
    except KeyError:
        created_at = None

    return {
        "username": username,
        "is_sudo": access == "sudo",
        "created_at": created_at,
    }
