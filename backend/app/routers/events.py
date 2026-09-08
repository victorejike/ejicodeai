"""Real-time SSE event streaming router.

The feed is what makes the agents visible while they work, so two properties
matter more than anything else here:

* **It is the caller's own feed.** The subscriber's ``user_id`` comes from the
  bearer token, not from a query parameter - otherwise anyone could watch another
  candidate's job search by guessing an id.
* **It survives a restart.** New subscribers are seeded from the persisted
  ``agent_events`` rows before the live stream takes over, so opening the
  dashboard after a run shows what happened instead of an empty panel.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.dependencies import get_db, resolve_user_id
from backend.app.models.core import AgentEvent
from backend.app.security import User, get_current_active_user
from backend.app.services.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/events", tags=["events"])


class EmitEventRequest(BaseModel):
    event_type: str
    message: str
    severity: str = "info"
    payload: dict = {}
    user_id: Optional[str] = None
    organization_id: Optional[str] = None


def _row_to_event(row: AgentEvent) -> Dict[str, Any]:
    """Persisted row in the exact shape the live bus publishes."""
    return {
        "id": str(row.id),
        "event_type": row.event_type,
        "severity": row.severity or "info",
        "message": row.message,
        "payload": row.payload or {},
        "user_id": str(row.user_id) if row.user_id else None,
        "organization_id": str(row.organization_id) if row.organization_id else None,
        "timestamp": row.created_at.isoformat() if row.created_at else None,
        "persisted": True,
    }


async def _load_history(
    *,
    user_id: Optional[uuid.UUID],
    organization_id: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """Recent stored events for this subscriber, oldest first.

    Read on a dedicated session: the streaming response outlives the request's
    own session, and holding that session open for the life of an SSE connection
    would pin a pooled connection for hours.
    """
    if limit <= 0:
        return []

    scopes = []
    if user_id:
        scopes.append(AgentEvent.user_id == user_id)
    if organization_id:
        try:
            scopes.append(AgentEvent.organization_id == uuid.UUID(str(organization_id)))
        except (ValueError, AttributeError, TypeError):
            pass

    try:
        async with async_session() as session:
            query = select(AgentEvent).order_by(desc(AgentEvent.created_at)).limit(limit)
            if scopes:
                # Platform-wide events (no owner) are relevant to everyone.
                query = query.where(or_(AgentEvent.user_id.is_(None), *scopes))
            rows = (await session.execute(query)).scalars().all()
    except Exception as exc:  # history is a nicety, never a reason to fail
        logger.debug("Could not load persisted agent events: %s", exc)
        return []

    return [_row_to_event(row) for row in reversed(rows)]


@router.get("/stream")
async def stream_events(
    organization_id: Optional[str] = Query(
        None, description="Also include this organization's events"
    ),
    history: int = Query(25, ge=0, le=100, description="Stored events to replay first"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events feed of agent activity for the authenticated user."""
    user_id = await resolve_user_id(current_user, db)
    # An org filter is only honoured for a caller who belongs to that org.
    org_filter = (
        organization_id
        if organization_id
        and (
            organization_id == str(current_user.organization_id)
            or current_user.is_superuser
        )
        else (str(current_user.organization_id) if current_user.organization_id else None)
    )

    async def event_generator():
        replayed = await _load_history(
            user_id=user_id, organization_id=org_filter, limit=history
        )
        for past in replayed:
            yield f"data: {json.dumps(past)}\n\n"

        init_payload = json.dumps(
            {
                "id": str(uuid.uuid4()),
                "event_type": "system.connected",
                "severity": "info",
                "message": (
                    f"Live feed connected - replayed {len(replayed)} stored "
                    f"event{'' if len(replayed) == 1 else 's'}."
                ),
                "payload": {"history_replayed": len(replayed)},
                "timestamp": None,
            }
        )
        yield f"data: {init_payload}\n\n"

        seen = {event["id"] for event in replayed}
        subscriber = event_bus.subscribe(user_id=str(user_id), organization_id=org_filter)
        try:
            async for event in subscriber:
                # The bus replays its own in-memory tail, which can overlap what
                # was just read from the table.
                if event.get("id") in seen:
                    continue
                seen.add(event.get("id"))
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def get_recent_events(
    limit: int = Query(30, ge=1, le=100),
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Recent events for this user, merging stored history with the live buffer."""
    user_id = await resolve_user_id(current_user, db)
    org_filter = organization_id or (
        str(current_user.organization_id) if current_user.organization_id else None
    )

    stored = await _load_history(user_id=user_id, organization_id=org_filter, limit=limit)
    live = event_bus.get_recent(limit=limit, user_id=str(user_id), organization_id=org_filter)

    merged: Dict[str, Dict[str, Any]] = {event["id"]: event for event in stored}
    for event in live:
        merged.setdefault(event["id"], event)

    events = sorted(merged.values(), key=lambda e: e.get("timestamp") or "")
    return {"events": events[-limit:], "count": min(len(events), limit)}


@router.post("/emit")
async def emit_event(
    body: EmitEventRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish an event. Attributed to the caller unless they are a superuser."""
    user_id = body.user_id
    if not current_user.is_superuser:
        user_id = str(await resolve_user_id(current_user, db))

    event = await event_bus.publish(
        event_type=body.event_type,
        message=body.message,
        payload=body.payload,
        severity=body.severity,
        user_id=user_id,
        organization_id=body.organization_id,
    )
    return {"status": "emitted", "event": event}
