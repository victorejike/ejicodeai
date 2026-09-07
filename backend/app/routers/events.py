"""Real-time SSE event streaming router."""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


@router.get("/stream")
async def stream_events(
    user_id: Optional[str] = Query(None, description="Optional user ID filter"),
    organization_id: Optional[str] = Query(None, description="Optional organization ID filter"),
):
    """Server-Sent Events (SSE) endpoint providing a real-time reactive feed of agent actions."""
    async def event_generator():
        # Send initial connected message
        init_payload = json.dumps({
            "event_type": "system.connected",
            "severity": "info",
            "message": "Connected to EJICODE AI real-time event stream",
            "timestamp": None,
        })
        yield f"data: {init_payload}\n\n"

        subscriber = event_bus.subscribe(user_id=user_id, organization_id=organization_id)
        try:
            async for event in subscriber:
                data_str = json.dumps(event)
                yield f"data: {data_str}\n\n"
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
    user_id: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
):
    """Retrieve recent agent events from the in-memory circular buffer."""
    events = event_bus.get_recent(limit=limit, user_id=user_id, organization_id=organization_id)
    return {"events": events, "count": len(events)}


@router.post("/emit")
async def emit_event(body: EmitEventRequest):
    """Publish an agent event manually or from an external workflow."""
    event = await event_bus.publish(
        event_type=body.event_type,
        message=body.message,
        payload=body.payload,
        severity=body.severity,
        user_id=body.user_id,
        organization_id=body.organization_id,
    )
    return {"status": "emitted", "event": event}
