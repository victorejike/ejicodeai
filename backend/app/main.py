"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database import close_db, init_db
from backend.app.metrics import PrometheusMiddleware, metrics_endpoint
from backend.app.rate_limiter import RateLimitMiddleware
from backend.app.routers import (
    agents,
    auth,
    companies,
    contacts,
    dashboard,
    enterprise,
    events,
    individual,
    opportunities,
    outreach,
    proposals,
    public,
    rag,
    reports,
)
from backend.app.security import get_current_active_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager for startup and shutdown."""
    logger.info("Starting Ejicode AI BD Platform...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        raise

    yield

    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as exc:
        logger.error("Database shutdown cleanup failed: %s", exc)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Ejicode AI Business Development Platform",
        description="Autonomous multi-agent system for business development",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Observability and rate limiting
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "status": "operational",
            "service": "Ejicode AI BDP",
            "version": "1.0.0",
            "environment": settings.environment,
        }
    
    @app.get("/health")
    async def health():
        checks: dict = {"database": "error", "redis": "error"}

        # Database check
        try:
            from backend.app.database import engine
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            pass

        # Redis check
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception:
            pass


        overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
        return {
            "status": overall,
            "service": "backend",
            "environment": settings.environment,
            **checks,
        }

    @app.get("/metrics")
    async def metrics():
        return metrics_endpoint()
    
    # API v1 routes
    app.include_router(events.router)
    app.include_router(public.router, prefix="/v1/public", tags=["Public"])
    app.include_router(auth.router, prefix="/v1/auth", tags=["Auth"])
    auth_dependency = [Depends(get_current_active_user)]
    app.include_router(individual.router, prefix="/v1/individual", tags=["Individual"], dependencies=auth_dependency)
    app.include_router(enterprise.router, prefix="/v1/enterprise", tags=["Enterprise"], dependencies=auth_dependency)
    app.include_router(companies.router, prefix="/v1/companies", tags=["Companies"], dependencies=auth_dependency)
    app.include_router(opportunities.router, prefix="/v1/opportunities", tags=["Opportunities"], dependencies=auth_dependency)
    app.include_router(contacts.router, prefix="/v1/contacts", tags=["Contacts"], dependencies=auth_dependency)
    app.include_router(proposals.router, prefix="/v1/proposals", tags=["Proposals"], dependencies=auth_dependency)
    app.include_router(outreach.router, prefix="/v1/outreach", tags=["Outreach"])
    app.include_router(reports.router, prefix="/v1/reports", tags=["Reports"], dependencies=auth_dependency)
    app.include_router(agents.router, prefix="/v1/agents", tags=["Agents"], dependencies=auth_dependency)
    app.include_router(dashboard.router, prefix="/v1/dashboard", tags=["Dashboard"], dependencies=auth_dependency)
    app.include_router(rag.router, prefix="/v1/rag", tags=["RAG"], dependencies=auth_dependency)

    # Static file uploads (avatars, documents)
    import os
    from fastapi.staticfiles import StaticFiles
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(os.path.join(uploads_dir, "avatars"), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )
