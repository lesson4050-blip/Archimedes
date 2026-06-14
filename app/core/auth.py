"""Authentication helpers for API and WebSocket connections."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError  # type: ignore[import-untyped]

from app.core.config import get_settings


def verify_ws_token(token: str | None) -> bool:
    """Validate a JSON Web Token (JWT) from a WebSocket query parameter.

    Args:
        token: The raw JWT string, or None.

    Returns:
        True if the token is present, valid, and successfully decoded; False otherwise.
    """
    if not token:
        return False
    try:
        settings = get_settings()
        jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return True
    except JWTError:
        return False


def create_access_token(user_id: str) -> str:
    """Create a JWT access token for a given user ID.

    Args:
        user_id: The ID of the user.

    Returns:
        The encoded JWT string with sub and exp claims.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=settings.jwt_expiry_hours)
    to_encode = {
        "sub": user_id,
        "exp": expire,
    }
    encoded_jwt: str = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_api_key(key: str | None) -> bool:
    """Verify an admin API key using constant-time comparison.

    Args:
        key: The API key to verify, or None.

    Returns:
        True if the key matches settings.admin_api_key; False otherwise.
    """
    if key is None:
        return False
    settings = get_settings()
    return secrets.compare_digest(key, settings.admin_api_key)
