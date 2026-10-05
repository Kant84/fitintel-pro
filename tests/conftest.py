# tests/conftest.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine, StaticPool, JSON, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.db.session import get_db


@compiles(JSONB, "sqlite")
def _jsonb_on_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(element, **kw)


TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Таблицы моделей + runtime-DDL таблицы (auth_refresh_tokens)."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS auth_refresh_tokens ("
            " id VARCHAR(36) PRIMARY KEY,"
            " user_id VARCHAR(36) NOT NULL,"
            " token_hash VARCHAR(64) NOT NULL,"
            " expires_at TIMESTAMP NOT NULL,"
            " revoked BOOLEAN NOT NULL DEFAULT FALSE,"
            " created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client, db_session):
    from app.core.security import pwd_context
    from app.models.user import User
    if not db_session.query(User).filter_by(username="testuser").first():
        db_session.add(User(
            username="testuser", email="test@test.com",
            password_hash=pwd_context.hash("testpass123"),
            is_active=True, is_superuser=True))
        db_session.commit()
    resp = client.post("/api/v1/auth/login", json={
        "login": "testuser", "password": "testpass123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": "Bearer " + resp.json()["access_token"]}