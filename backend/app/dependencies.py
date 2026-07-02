"""Pydantic settings for API dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_session():
        yield session
