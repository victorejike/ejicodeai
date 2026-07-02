import os
from datetime import timedelta
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SMTP_HOST", "smtp.example.com")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "password")

from backend.app import main
from backend.app.config import get_settings
from backend.app.security import create_access_token

settings = get_settings()


def setup_client(monkeypatch):
    monkeypatch.setattr(main, "init_db", AsyncMock())
    return TestClient(main.create_app())


def test_login_success(monkeypatch):
    client = setup_client(monkeypatch)
    response = client.post(
        "/v1/auth/login",
        data={"username": settings.dev_username, "password": settings.dev_password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure(monkeypatch):
    client = setup_client(monkeypatch)
    response = client.post(
        "/v1/auth/login",
        data={"username": "invalid", "password": "invalid"},
    )
    assert response.status_code == 401


def test_me_requires_auth(monkeypatch):
    client = setup_client(monkeypatch)
    response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(monkeypatch):
    client = setup_client(monkeypatch)
    token = create_access_token(
        username=settings.dev_username,
        roles=["admin"],
        expires_delta=timedelta(hours=1),
    )
    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == settings.dev_username
    assert "admin" in data["roles"]
