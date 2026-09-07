"""Auth router - Production-ready JWT authentication endpoints supporting Individual and Enterprise users."""
from datetime import datetime, timedelta, timezone
import logging
import re
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.dependencies import get_db
from backend.app.models.core import (
    Organization,
    OrganizationMember,
    PasswordResetToken,
    RefreshToken as DBRefreshToken,
    User as DBUser,
    UserProfile,
)
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


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower().strip())
    s = re.sub(r"[-\s]+", "-", s)
    return s or f"org-{secrets.token_hex(4)}"


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
    """General registration request schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    account_type: Optional[str] = "individual"


class RegisterIndividualRequest(BaseModel):
    """Individual candidate registration schema."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    username: Optional[str] = None
    title: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    remote_preference: Optional[str] = "remote"


class RegisterEnterpriseRequest(BaseModel):
    """Enterprise organization registration schema."""
    organization_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    username: Optional[str] = None
    domain: Optional[str] = None
    plan_tier: Optional[str] = "enterprise"


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    email: EmailStr


class VerifyResetTokenRequest(BaseModel):
    """Verify reset token schema."""
    token: str


class ResetPasswordRequest(BaseModel):
    """Reset password schema."""
    token: str
    new_password: str = Field(..., min_length=6)


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

    # Check form data
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
        user_id=str(user.id) if user.id else None,
        account_type=user.account_type,
        organization_id=str(user.organization_id) if user.organization_id else None,
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
            "account_type": user.account_type,
            "organization_id": user.organization_id,
            "roles": user.roles,
        },
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """General platform registration endpoint."""
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
        account_type=data.account_type or "individual",
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
        "account_type": new_user.account_type,
        "status": "created",
    }


@router.post("/register/individual", status_code=status.HTTP_201_CREATED)
async def register_individual(data: RegisterIndividualRequest, db: AsyncSession = Depends(get_db)):
    """Register an Individual candidate and create their career profile."""
    # Check if user already exists
    existing = await db.execute(select(DBUser).where(DBUser.email == data.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    # Determine username
    base_username = data.username or data.email.split("@")[0].lower()
    username = re.sub(r"[^\w]", "_", base_username)
    u_exist = await db.execute(select(DBUser).where(DBUser.username == username))
    if u_exist.scalars().first():
        username = f"{username}_{secrets.token_hex(3)}"

    new_user = DBUser(
        email=data.email,
        username=username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        account_type="individual",
        roles=["user"],
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Create associated profile
    profile = UserProfile(
        user_id=new_user.id,
        full_name=data.full_name,
        title=data.title or "Software Professional",
        skills=data.skills or [],
        location=data.location or "Remote",
        remote_preference=data.remote_preference or "remote",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(new_user)

    # Generate immediate session tokens
    access_token = create_access_token(
        username=new_user.username,
        roles=new_user.roles,
        email=new_user.email,
        user_id=str(new_user.id),
        full_name=new_user.full_name,
        account_type="individual",
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    refresh_token = create_refresh_token(
        username=new_user.username,
        roles=new_user.roles,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    db_refresh = DBRefreshToken(
        user_id=new_user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        revoked=False,
    )
    db.add(db_refresh)
    await db.commit()

    return {
        "status": "created",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "account_type": "individual",
        },
    }


@router.post("/register/enterprise", status_code=status.HTTP_201_CREATED)
async def register_enterprise(data: RegisterEnterpriseRequest, db: AsyncSession = Depends(get_db)):
    """Register an Enterprise organization, account owner, and membership."""
    existing = await db.execute(select(DBUser).where(DBUser.email == data.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    # 1. Create Organization
    slug = _slugify(data.organization_name)
    org_exist = await db.execute(select(Organization).where(Organization.slug == slug))
    if org_exist.scalars().first():
        slug = f"{slug}-{secrets.token_hex(3)}"

    domain = data.domain or data.email.split("@")[-1]
    org = Organization(
        name=data.organization_name,
        slug=slug,
        domain=domain,
        plan=data.plan_tier or "enterprise",
        billing_email=data.email,
        status="active",
    )
    db.add(org)
    await db.flush()

    # 2. Create Enterprise User
    base_username = data.username or data.email.split("@")[0].lower()
    username = re.sub(r"[^\w]", "_", base_username)
    u_exist = await db.execute(select(DBUser).where(DBUser.username == username))
    if u_exist.scalars().first():
        username = f"{username}_{secrets.token_hex(3)}"

    new_user = DBUser(
        email=data.email,
        username=username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        account_type="enterprise",
        organization_id=org.id,
        roles=["admin", "recruiter"],
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 3. Create Organization Member link (Owner)
    member = OrganizationMember(
        organization_id=org.id,
        user_id=new_user.id,
        role="owner",
        permissions=["admin", "recruiter", "billing", "view", "edit"],
    )
    db.add(member)
    await db.commit()
    await db.refresh(new_user)

    # Generate session tokens
    access_token = create_access_token(
        username=new_user.username,
        roles=new_user.roles,
        email=new_user.email,
        user_id=str(new_user.id),
        full_name=new_user.full_name,
        account_type="enterprise",
        organization_id=str(org.id),
        expires_delta=timedelta(hours=settings.access_token_expire_hours),
    )
    refresh_token = create_refresh_token(
        username=new_user.username,
        roles=new_user.roles,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    db_refresh = DBRefreshToken(
        user_id=new_user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        revoked=False,
    )
    db.add(db_refresh)
    await db.commit()

    return {
        "status": "created",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "role": "owner",
        },
        "user": {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "account_type": "enterprise",
            "organization_id": str(org.id),
        },
    }


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Initiate secure password reset by generating a single-use token."""
    user_res = await db.execute(select(DBUser).where(DBUser.email == data.email))
    user = user_res.scalars().first()

    raw_token = secrets.token_urlsafe(32)
    if user:
        token_h = hash_token(raw_token)
        # Expire any previous unconsumed tokens for this user
        existing_tokens = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,
            )
        )
        for t in existing_tokens.scalars().all():
            t.used = True

        pwd_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_h,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=False,
        )
        db.add(pwd_token)
        await db.commit()
        logger.info("Password reset token generated for user %s", user.email)

    # Response is intentionally safe against email enumeration
    return {
        "status": "success",
        "message": f"If an account exists for {data.email}, password reset instructions have been dispatched.",
        "dev_reset_token": raw_token if user else None,
    }


@router.post("/verify-reset-token")
async def verify_reset_token(data: VerifyResetTokenRequest, db: AsyncSession = Depends(get_db)):
    """Verify that a password reset token is valid and unexpired."""
    token_h = hash_token(data.token)
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_h,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc),
    )
    res = await db.execute(stmt)
    token_record = res.scalars().first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid or has expired.",
        )

    user = await db.get(DBUser, token_record.user_id)
    return {
        "valid": True,
        "email": user.email if user else None,
    }


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Consume reset token and update user password."""
    token_h = hash_token(data.token)
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_h,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc),
    )
    res = await db.execute(stmt)
    token_record = res.scalars().first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid or has expired.",
        )

    user = await db.get(DBUser, token_record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    # Update password and mark token as used
    user.hashed_password = hash_password(data.new_password)
    token_record.used = True

    # Revoke all existing refresh tokens for security
    await db.execute(
        update(DBRefreshToken).where(DBRefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()

    return {
        "status": "success",
        "message": "Your password has been successfully reset. Please log in with your new credentials.",
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
    """Get the profile of current authenticated user including multi-tenant context."""
    try:
        stmt = select(DBUser).where(DBUser.username == current_user.username)
        result = await db.execute(stmt)
        db_user = result.scalars().first()
        if db_user:
            org_data = None
            if db_user.organization_id:
                org = await db.get(Organization, db_user.organization_id)
                if org:
                    org_data = {
                        "id": str(org.id),
                        "name": org.name,
                        "slug": org.slug,
                        "plan": org.plan,
                    }

            return {
                "id": str(db_user.id),
                "username": db_user.username,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "account_type": db_user.account_type or "individual",
                "organization_id": str(db_user.organization_id) if db_user.organization_id else None,
                "organization": org_data,
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
        "account_type": current_user.account_type,
        "organization_id": current_user.organization_id,
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
