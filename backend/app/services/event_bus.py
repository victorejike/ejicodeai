"""Asynchronous Event Bus for real-time Agent Event Broadcasting and SSE streaming."""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory pub/sub event bus supporting user/org filtered SSE streaming and persistent history."""

    def __init__(self, max_history: int = 200):
        self._subscribers: Set[asyncio.Queue] = set()
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    async def publish(
        self,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Broadcast an event to all active SSE subscribers and store in history."""
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "payload": payload or {},
            "user_id": str(user_id) if user_id else None,
            "organization_id": str(organization_id) if organization_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        # Notify active queues
        dead_queues = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(q)
            except Exception as e:
                logger.debug("Failed to push to subscriber queue: %s", e)
                dead_queues.append(q)

        for q in dead_queues:
            self._subscribers.discard(q)

        return event

    async def subscribe(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield real-time events filtered by user or organization."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)

        try:
            # First send recent history for instant context
            async with self._lock:
                recent_copy = list(self._history[-60:])

            for past_event in recent_copy:
                if self._matches_filter(past_event, user_id, organization_id):
                    yield past_event

            # Then stream new live events as they arrive
            while True:
                event = await q.get()
                if self._matches_filter(event, user_id, organization_id):
                    yield event
        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.discard(q)

    @staticmethod
    def _matches_filter(
        event: Dict[str, Any],
        user_id: Optional[str],
        organization_id: Optional[str],
    ) -> bool:
        """Check if an event matches the subscriber's filter."""
        # Global events with no user/org match everyone
        if not event.get("user_id") and not event.get("organization_id"):
            return True
        if user_id and event.get("user_id") == str(user_id):
            return True
        if organization_id and event.get("organization_id") == str(organization_id):
            return True
        return False

    def get_recent(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent events from memory."""
        filtered = [
            e for e in self._history
            if self._matches_filter(e, user_id, organization_id)
        ]
        return filtered[-limit:]


# Global singleton event bus
event_bus = EventBus()
