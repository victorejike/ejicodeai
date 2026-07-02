"""Auth router - JWT authentication endpoints."""
from datetime import timedelta
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.security import (
    _decode_token,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    User,
)

router = APIRouter()
settings = get_settings()


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint - accepts form data, returns JWT tokens."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token = create_access_token(
        username=user.username,
        roles=user.roles,
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    refresh_token = create_refresh_token(
        username=user.username,
        roles=user.roles,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    token_data = _decode_token(refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(
        username=token_data.get("sub"),
        roles=token_data.get("roles", []),
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_active_user)):
    """Get the current authenticated user."""
    return {
        "username": current_user.username,
        "roles": current_user.roles,
        "is_active": current_user.is_active,
    }


@router.post("/logout")
async def logout():
    """Logout endpoint."""
    return {"status": "logged_out"}
