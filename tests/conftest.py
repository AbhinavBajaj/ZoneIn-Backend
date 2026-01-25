"""Pytest fixtures: test DB, client, auth."""
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import create_access_token
from app.core.database import Base, get_db
from app.main import app
from app.models.session_report import SessionReport
from app.models.user import User


def _sqlite_url() -> str:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = f.name
    f.close()
    return f"sqlite:///{path}"


@pytest.fixture
def engine():
    url = _sqlite_url()
    e = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    Path(url.replace("sqlite:///", "")).unlink(missing_ok=True)


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db: Session):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user_a(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        google_sub="google-sub-a",
        email="a@example.com",
        name="User A",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def user_b(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        google_sub="google-sub-b",
        email="b@example.com",
        name="User B",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def token_a(user_a: User) -> str:
    return create_access_token(user_a.id)


@pytest.fixture
def token_b(user_b: User) -> str:
    return create_access_token(user_b.id)


@pytest.fixture
def report_payload():
    return {
        "session_id": str(uuid.uuid4()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "duration_sec": 14400,
        "focused_sec": 12000,
        "distracted_sec": 1200,
        "neutral_sec": 1200,
        "zone_in_score": 83.33,
        "timeline_buckets_json": '[{"bucket_start_ts":0,"bucket_duration_sec":300,"state":"focused"}]',
        "cloud_ai_enabled": True,
    }
