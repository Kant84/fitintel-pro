# tests/conftest.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.db.session import get_db


# In-memory SQLite для тестов
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
    """Создать таблицы перед всеми тестами"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Новая сессия БД для каждого теста"""
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client():
    """TestClient для FastAPI"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Получить JWT токен для тестов"""
    # Регистрация
    resp = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
    })
    
    # Логин
    resp = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123",
    })
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
