"""Pydantic settings for API dependencies."""
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_session():
        yield session


async def resolve_user_id(current_user, db: AsyncSession) -> uuid.UUID:
    """The ``users.id`` behind an authenticated caller.

    The JWT usually carries it, but tokens issued through the dev login path do
    not, so fall back to a lookup by username/email. Every user-scoped query in
    the app funnels through here: getting this wrong is how one user ends up
    reading another user's rows.
    """
    if getattr(current_user, "id", None):
        try:
            return uuid.UUID(str(current_user.id))
        except ValueError:
            pass

    from backend.app.models.core import User as DBUser

    stmt = select(DBUser.id).where(
        (DBUser.username == current_user.username) | (DBUser.email == current_user.email)
    )
    db_id = (await db.execute(stmt)).scalars().first()
    if db_id:
        return db_id if isinstance(db_id, uuid.UUID) else uuid.UUID(str(db_id))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User record not found")
