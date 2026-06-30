"""Single-password edit authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Header, HTTPException

from backend.app.config import settings

TOKEN_TTL_SECONDS = 8 * 60 * 60


def _signing_secret() -> str:
    if settings.session_secret:
        return settings.session_secret
    if settings.edit_password:
        return hashlib.sha256(settings.edit_password.encode()).hexdigest()
    return ""


def edit_auth_enabled() -> bool:
    return bool(settings.edit_password)


def verify_password(password: str) -> bool:
    if not settings.edit_password:
        return False
    return secrets.compare_digest(password, settings.edit_password)


def create_session_token() -> str:
    payload = {"exp": int(time.time()) + TOKEN_TTL_SECONDS}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(
        _signing_secret().encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def validate_session_token(token: str) -> bool:
    if not token or not edit_auth_enabled():
        return False

    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        return False

    expected_sig = hmac.new(
        _signing_secret().encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    padding = "=" * (-len(sig_b64) % 4)
    try:
        provided_sig = base64.urlsafe_b64decode(sig_b64 + padding)
    except ValueError:
        return False

    if not secrets.compare_digest(expected_sig, provided_sig):
        return False

    padding = "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
    except (ValueError, json.JSONDecodeError):
        return False

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return False

    return True


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def require_edit_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not edit_auth_enabled():
        return

    token = extract_bearer_token(authorization)
    if not token or not validate_session_token(token):
        raise HTTPException(status_code=401, detail="Authentication required to edit")
