"""Auth flow (mocked)."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def test_google_login_redirects(client: TestClient):
    r = client.get("/auth/google/login", follow_redirects=False)
    assert r.status_code in (200, 302, 307)
    if r.status_code in (302, 307):
        loc = r.headers.get("location", "")
        assert "accounts.google.com" in loc
        assert "client_id=" in loc
        assert "redirect_uri=" in loc
        assert "state=" in loc


def test_google_callback_missing_code(client: TestClient):
    r = client.get("/auth/google/callback")
    assert r.status_code == 400  # missing code or state


def test_google_callback_invalid_state(client: TestClient):
    r = client.get("/auth/google/callback?code=abc&state=invalid")
    assert r.status_code == 400
    assert "state" in (r.json().get("detail") or "").lower()
