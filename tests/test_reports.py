"""POST /reports create + upsert, GET /reports, GET /reports/{id}, auth isolation."""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_post_reports_create(
    client: TestClient,
    token_a: str,
    user_a: User,
    report_payload: dict,
):
    r = client.post(
        "/reports",
        json=report_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == report_payload["session_id"]
    assert data["zone_in_score"] == report_payload["zone_in_score"]
    assert data["focused_sec"] == report_payload["focused_sec"]
    assert "id" in data


def test_post_reports_upsert(
    client: TestClient,
    token_a: str,
    user_a: User,
    report_payload: dict,
):
    r1 = client.post("/reports", json=report_payload, headers={"Authorization": f"Bearer {token_a}"})
    assert r1.status_code == 200
    id1 = r1.json()["id"]

    report_payload["zone_in_score"] = 50.0
    report_payload["focused_sec"] = 7000.0
    r2 = client.post("/reports", json=report_payload, headers={"Authorization": f"Bearer {token_a}"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["id"] == id1
    assert data["zone_in_score"] == 50.0
    assert data["focused_sec"] == 7000.0


def test_post_reports_unauthorized(client: TestClient, report_payload: dict):
    r = client.post("/reports", json=report_payload)
    assert r.status_code == 401  # no Bearer


def test_get_reports_list(
    client: TestClient,
    token_a: str,
    user_a: User,
    report_payload: dict,
):
    client.post("/reports", json=report_payload, headers={"Authorization": f"Bearer {token_a}"})
    r = client.get("/reports", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["session_id"] == report_payload["session_id"]


def test_get_reports_by_id(
    client: TestClient,
    token_a: str,
    user_a: User,
    report_payload: dict,
):
    create = client.post("/reports", json=report_payload, headers={"Authorization": f"Bearer {token_a}"})
    rid = create.json()["id"]
    r = client.get(f"/reports/{rid}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_auth_isolation(
    client: TestClient,
    token_a: str,
    token_b: str,
    user_a: User,
    user_b: User,
    report_payload: dict,
):
    """User B cannot read User A's reports."""
    create = client.post("/reports", json=report_payload, headers={"Authorization": f"Bearer {token_a}"})
    assert create.status_code == 200
    rid = create.json()["id"]

    r = client.get(f"/reports/{rid}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 404

    list_b = client.get("/reports", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    ids = [x["id"] for x in list_b.json()]
    assert rid not in ids
