"""Agent-side event emission: one call, two destinations.

Before this module the only things publishing to the event bus were HTTP
handlers, so the dashboard's "LIVE FEED" stayed empty for the entire duration of
an agent run - the work was invisible while it happened. And because nothing
ever wrote the ``agent_events`` table, whatever the user did see was lost on the
next restart.

``emit()`` fixes both: it broadcasts to the in-memory bus for live SSE *and*
persists a row for history. It is deliberately best-effort - telemetry must never
be the reason an agent run fails.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: Severities understood by the frontend feed.
SEVERITIES = ("info", "success", "warning", "error")


async def emit(
    event_type: str,
    message: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
    severity: str = "info",
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    persist: bool = True,
) -> Optional[Dict[str, Any]]:
    """Publish a live event and (by default) store it for history.

    Returns the published event, or None if the bus was unreachable.
    """
    if severity not in SEVERITIES:
        severity = "info"

    event: Optional[Dict[str, Any]] = None
    try:
        from backend.app.services.event_bus import event_bus

        event = await event_bus.publish(
            event_type=event_type,
            message=message,
            payload=payload or {},
            severity=severity,
            user_id=str(user_id) if user_id else None,
            organization_id=str(organization_id) if organization_id else None,
        )
    except Exception as exc:  # pragma: no cover - telemetry must not break a run
        logger.debug("Event bus publish failed for %s: %s", event_type, exc)

    if persist:
        await _persist(
            event_type=event_type,
            message=message,
            payload=payload or {},
            severity=severity,
            user_id=user_id,
            organization_id=organization_id,
        )

    return event


async def _persist(
    *,
    event_type: str,
    message: str,
    payload: Dict[str, Any],
    severity: str,
    user_id: Optional[str],
    organization_id: Optional[str],
) -> None:
    """Write one AgentEvent row on its own short-lived session.

    A dedicated session keeps event history independent of whatever transaction
    the caller is in: a rolled-back pipeline still leaves its audit trail.
    """
    try:
        import uuid as _uuid

        from backend.app.database import async_session
        from backend.app.models.core import AgentEvent

        def _as_uuid(value: Optional[str]):
            if not value:
                return None
            try:
                return _uuid.UUID(str(value))
            except (ValueError, AttributeError, TypeError):
                return None

        async with async_session() as session:
            session.add(
                AgentEvent(
                    user_id=_as_uuid(user_id),
                    organization_id=_as_uuid(organization_id),
                    event_type=event_type,
                    severity=severity,
                    message=message,
                    payload=payload,
                )
            )
            await session.commit()
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not persist agent event %s: %s", event_type, exc)
