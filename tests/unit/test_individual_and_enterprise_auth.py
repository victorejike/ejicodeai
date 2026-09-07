"""Unit tests for individual/enterprise registration and forgot-password flow."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long!!")

from backend.app.main import app
from backend.app.dependencies import get_db
from backend.app.models.core import Base, User, Organization, UserProfile, PasswordResetToken


@pytest.fixture
async def test_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(test_db_session):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_individual_user(client, test_db_session):
    payload = {
        "email": "sarah.connor@ai-dev.com",
        "password": "Password123!",
        "full_name": "Sarah Connor",
        "title": "Lead Security Architect",
        "skills": ["Python", "FastAPI", "Cybersecurity", "Docker"],
        "location": "Remote, UK",
        "remote_preference": "remote",
    }
    response = client.post("/v1/auth/register/individual", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert "access_token" in data
    assert data["user"]["email"] == "sarah.connor@ai-dev.com"
    assert data["user"]["account_type"] == "individual"

    # Duplicate registration should return 409
    dup_res = client.post("/v1/auth/register/individual", json=payload)
    assert dup_res.status_code == 409


def test_register_enterprise_user(client, test_db_session):
    payload = {
        "organization_name": "Acme AI Systems",
        "email": "cto@acmeai.com",
        "password": "SecurePassword123!",
        "full_name": "Marcus Wright",
        "domain": "acmeai.com",
    }
    response = client.post("/v1/auth/register/enterprise", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert "access_token" in data
    assert data["organization"]["name"] == "Acme AI Systems"
    assert data["user"]["account_type"] == "enterprise"
    assert data["user"]["organization_id"] == data["organization"]["id"]

    # Verify login works with the new enterprise user
    login_res = client.post(
        "/v1/auth/login",
        json={"username": data["user"]["username"], "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["account_type"] == "enterprise"


def test_forgot_and_reset_password_flow(client, test_db_session):
    # 1. Register user
    reg_payload = {
        "email": "forgot.tester@example.com",
        "password": "OldPassword123!",
        "full_name": "Forgot Tester",
    }
    reg_res = client.post("/v1/auth/register/individual", json=reg_payload)
    assert reg_res.status_code == 201

    # 2. Request forgot password
    forgot_res = client.post("/v1/auth/forgot-password", json={"email": "forgot.tester@example.com"})
    assert forgot_res.status_code == 200
    forgot_data = forgot_res.json()
    assert forgot_data["status"] == "success"
    reset_token = forgot_data["dev_reset_token"]
    assert reset_token is not None

    # 3. Verify reset token
    verify_res = client.post("/v1/auth/verify-reset-token", json={"token": reset_token})
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True
    assert verify_res.json()["email"] == "forgot.tester@example.com"

    # 4. Reset password
    reset_res = client.post(
        "/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewBrandNewPassword123!"},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "success"

    # 5. Old token should now be invalid/consumed
    reverify_res = client.post("/v1/auth/verify-reset-token", json={"token": reset_token})
    assert reverify_res.status_code == 400

    # 6. Can log in with new password
    login_res = client.post(
        "/v1/auth/login",
        json={"username": "forgot.tester@example.com", "password": "NewBrandNewPassword123!"},
    )
    assert login_res.status_code == 200

    # Old password fails
    old_login = client.post(
        "/v1/auth/login",
        json={"username": "forgot.tester@example.com", "password": "OldPassword123!"},
    )
    assert old_login.status_code == 401
