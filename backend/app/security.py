"""Security and authentication utilities using JWT and bcrypt."""
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, List, Optional
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


class User(BaseModel):
    id: Optional[str] = None
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    account_type: str = "individual"
    organization_id: Optional[str] = None
    roles: List[str] = ["user"]
    is_active: bool = True
    is_superuser: bool = False


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
    roles: List[str] = ["user"]
    email: Optional[str] = None
    full_name: Optional[str] = None
    user_id: Optional[str] = None
    account_type: Optional[str] = "individual"
    organization_id: Optional[str] = None


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Generate SHA256 hash of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=4))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Synchronous authenticate function for backward compatibility and test mock suites."""
    if username == settings.dev_username and password == settings.dev_password:
        return User(
            id="00000000-0000-0000-0000-000000000001",
            username=username,
            email=f"{username}@ejicode.com",
            full_name="Admin User",
            roles=settings.dev_user_roles,
            is_active=True,
            is_superuser=True,
        )
    return None


async def authenticate_user_db(session: AsyncSession, username_or_email: str, password: str) -> Optional[User]:
    """Authenticate user against database with fallback to dev credentials."""
    from backend.app.models.core import User as DBUser

    # 1. Search database
    stmt = select(DBUser).where(
        (DBUser.username == username_or_email) | (DBUser.email == username_or_email)
    )
    result = await session.execute(stmt)
    db_user = result.scalars().first()

    if db_user:
        if verify_password(password, db_user.hashed_password):
            return User(
                id=str(db_user.id),
                username=db_user.username,
                email=db_user.email,
                full_name=db_user.full_name or "",
                account_type=getattr(db_user, "account_type", "individual") or "individual",
                organization_id=str(db_user.organization_id) if getattr(db_user, "organization_id", None) else None,
                roles=db_user.roles or ["user"],
                is_active=db_user.is_active,
                is_superuser=db_user.is_superuser,
            )
        return None

    # 2. Fallback to dev username & password
    if username_or_email == settings.dev_username and password == settings.dev_password:
        return User(
            id="00000000-0000-0000-0000-000000000001",
            username=username_or_email,
            email=f"{username_or_email}@ejicode.com",
            full_name="Dev Admin",
            roles=settings.dev_user_roles,
            is_active=True,
            is_superuser=True,
        )

    return None


def create_access_token(
    username: str,
    roles: list[str],
    expires_delta: Optional[timedelta] = None,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
    full_name: Optional[str] = None,
    account_type: Optional[str] = "individual",
    organization_id: Optional[str] = None,
) -> str:
    payload: dict[str, Any] = {
        "sub": username,
        "type": "access",
        "roles": roles,
        "user_id": str(user_id) if user_id else None,
        "full_name": full_name,
        "account_type": account_type or "individual",
        "organization_id": str(organization_id) if organization_id else None,
    }
    if email:
        payload["email"] = email
    return _create_token(payload, expires_delta=expires_delta or timedelta(hours=settings.access_token_expire_hours))


def create_refresh_token(username: str, roles: list[str], expires_delta: Optional[timedelta] = None) -> str:
    return _create_token(
        {"sub": username, "type": "refresh", "roles": roles},
        expires_delta=expires_delta or timedelta(days=settings.refresh_token_expire_days),
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = _decode_token(token)
    token_data = TokenPayload(**payload)
    return User(
        id=token_data.user_id,
        username=token_data.sub,
        email=token_data.email,
        full_name=token_data.full_name,
        account_type=token_data.account_type or "individual",
        organization_id=token_data.organization_id,
        roles=token_data.roles,
        is_active=True,
    )


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return current_user


def require_role(role: str):
    async def _require_role(current_user: User = Depends(get_current_active_user)) -> User:
        if role not in current_user.roles and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return current_user

    return _require_role
