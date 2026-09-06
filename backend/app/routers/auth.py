"""Auth router - Production-ready JWT authentication endpoints with database persistence."""
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.dependencies import get_db
from backend.app.models.core import RefreshToken as DBRefreshToken, User as DBUser
from backend.app.security import (
    _decode_token,
    authenticate_user_db,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    hash_password,
    hash_token,
    User,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None


class LoginRequest(BaseModel):
    """JSON login request."""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login endpoint supporting both OAuth2 form data and JSON body."""
    username = None
    password = None

    # Check form data (application/x-www-form-urlencoded or multipart/form-data)
    try:
        form = await request.form()
        if form:
            username = form.get("username")
            password = form.get("password")
    except Exception:
        pass

    # Check JSON body
    if not username:
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = body.get("username")
                password = body.get("password")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password",
        )

    user = None
    try:
        user = await authenticate_user_db(db, str(username), str(password))
    except Exception as exc:
        logger.warning("Database auth error, attempting fallback: %s", exc)
        from backend.app.security import authenticate_user
        user = authenticate_user(str(username), str(password))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        username=user.username,
        roles=user.roles,
        email=user.email,
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    refresh_token = create_refresh_token(
        username=user.username,
        roles=user.roles,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    if user.id:
        try:
            db_refresh = DBRefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
                revoked=False,
            )
            db.add(db_refresh)
            await db.commit()
        except Exception:
            await db.rollback()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
        },
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new platform user."""
    existing = await db.execute(
        select(DBUser).where((DBUser.email == data.email) | (DBUser.username == data.username))
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists",
        )

    new_user = DBUser(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name or "",
        roles=["user"],
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "username": new_user.username,
        "full_name": new_user.full_name,
        "status": "created",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    data: Optional[RefreshTokenRequest] = None,
    refresh_token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token with token rotation."""
    token_str = (data.refresh_token if data else None) or refresh_token
    if not token_str:
        # Also check form or JSON body
        try:
            body = await request.json()
            token_str = body.get("refresh_token")
        except Exception:
            pass

    if not token_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required")

    token_data = _decode_token(token_str)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_h = hash_token(token_str)
    try:
        stored = await db.execute(select(DBRefreshToken).where(DBRefreshToken.token_hash == token_h))
        db_token = stored.scalars().first()
        if db_token and db_token.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    except HTTPException:
        raise
    except Exception:
        db_token = None

    username = token_data.get("sub")
    roles = token_data.get("roles", ["user"])

    new_access_token = create_access_token(
        username=username,
        roles=roles,
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    new_refresh_token = create_refresh_token(
        username=username,
        roles=roles,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    if db_token:
        try:
            db_token.revoked = True
            new_db_token = DBRefreshToken(
                user_id=db_token.user_id,
                token_hash=hash_token(new_refresh_token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
                revoked=False,
            )
            db.add(new_db_token)
            await db.commit()
        except Exception:
            await db.rollback()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the profile of current authenticated user."""
    try:
        stmt = select(DBUser).where(DBUser.username == current_user.username)
        result = await db.execute(stmt)
        db_user = result.scalars().first()
        if db_user:
            return {
                "id": str(db_user.id),
                "username": db_user.username,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "roles": db_user.roles or ["user"],
                "is_active": db_user.is_active,
                "is_superuser": db_user.is_superuser,
                "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            }
    except Exception:
        pass

    return {
        "username": current_user.username,
        "email": current_user.email or f"{current_user.username}@ejicode.com",
        "roles": current_user.roles,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
    }


@router.post("/logout")
async def logout(
    data: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token on logout."""
    if data and data.refresh_token:
        try:
            token_h = hash_token(data.refresh_token)
            await db.execute(
                update(DBRefreshToken).where(DBRefreshToken.token_hash == token_h).values(revoked=True)
            )
            await db.commit()
        except Exception:
            await db.rollback()

    return {"status": "logged_out"}
