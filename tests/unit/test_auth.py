"""Unit tests for JWT authentication helpers."""

from __future__ import annotations

from app.core.auth import verify_ws_token, create_access_token, verify_api_key


def test_verify_ws_token_missing_returns_false() -> None:
    """verify_ws_token must return False when token is missing or None."""
    assert verify_ws_token(None) is False
    assert verify_ws_token("") is False


def test_verify_ws_token_invalid_returns_false() -> None:
    """verify_ws_token must return False when token is invalid or malformed."""
    assert verify_ws_token("invalid-token") is False
    assert verify_ws_token("not.a.jwt") is False


def test_verify_ws_token_valid_returns_true(valid_token: str) -> None:
    """verify_ws_token must return True when a valid JWT token is provided."""
    assert verify_ws_token(valid_token) is True


def test_create_and_verify_token_roundtrip() -> None:
    """create_access_token followed by verify_ws_token should successfully validate."""
    token = create_access_token(user_id="another-user")
    assert verify_ws_token(token) is True


def test_verify_api_key_valid() -> None:
    """verify_api_key returns True for correct api key, False otherwise."""
    from app.core.config import get_settings
    settings = get_settings()
    assert verify_api_key(settings.admin_api_key) is True
    assert verify_api_key("wrong-key") is False
    assert verify_api_key(None) is False
