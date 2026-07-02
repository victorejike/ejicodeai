import os
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


def test_root_endpoint(monkeypatch):
    monkeypatch.setattr(main, "init_db", AsyncMock())
    client = TestClient(main.create_app())
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"


def test_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(main, "init_db", AsyncMock())
    client = TestClient(main.create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text
