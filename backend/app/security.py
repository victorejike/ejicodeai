from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.app.config import get_settings

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


class User(BaseModel):
    username: str
    roles: list[str] = ["user"]
    is_active: bool = True


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
    roles: list[str] = ["user"]


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
    if username != settings.dev_username or password != settings.dev_password:
        return None

    return User(username=username, roles=settings.dev_user_roles)


def create_access_token(username: str, roles: list[str], expires_delta: timedelta) -> str:
    return _create_token(
        {"sub": username, "type": "access", "roles": roles},
        expires_delta=expires_delta,
    )


def create_refresh_token(username: str, roles: list[str], expires_delta: timedelta) -> str:
    return _create_token(
        {"sub": username, "type": "refresh", "roles": roles},
        expires_delta=expires_delta,
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = _decode_token(token)
    token_data = TokenPayload(**payload)
    return User(username=token_data.sub, roles=token_data.roles)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return current_user


def require_role(role: str):
    async def _require_role(current_user: User = Depends(get_current_active_user)) -> User:
        if role not in current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return current_user

    return _require_role
