"""Database configuration and async session management."""
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

Base = declarative_base()

_connect_args = {}
if "postgresql" in settings.database_url or "postgres" in settings.database_url:
    _connect_args = {"timeout": 30, "command_timeout": 30}

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and register ORM models."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")

        import backend.app.models  # noqa: F401

        if settings.environment == "development":
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Development tables created/verified")

    except Exception as exc:
        logger.error("Database initialization error: %s", exc)
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")

