"""Tests for /auth/token rate limiting."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.router import _token_requests


def test_token_endpoint_rate_limited_after_5_requests(client: TestClient) -> None:
    """Calling POST /auth/token 6 times rapidly should return 429 on the 6th."""
    _token_requests.clear()

    for i in range(5):
        response = client.post("/auth/token")
        assert response.status_code == 200, (
            f"Request {i + 1} should succeed but got {response.status_code}"
        )
        assert "access_token" in response.json()

    response = client.post("/auth/token")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many token requests"


def test_token_endpoint_allows_after_window_reset(client: TestClient) -> None:
    """After clearing the rate-limit window, requests should succeed again."""
    _token_requests.clear()

    for _ in range(5):
        client.post("/auth/token")

    # Simulate window expiry by clearing the tracker
    _token_requests.clear()

    response = client.post("/auth/token")
    assert response.status_code == 200
    assert "access_token" in response.json()
