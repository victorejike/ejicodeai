from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from backend.app.services.ai.schemas import ProviderHealth, ProviderName


class ProviderMonitor:
    """Tracks health and performance of AI providers."""

    def __init__(self):
        self._states: Dict[ProviderName, ProviderHealth] = {
            provider: ProviderHealth(provider=provider, healthy=False)
            for provider in ProviderName
        }

    def record_success(self, provider: ProviderName, latency: float) -> None:
        state = self._states[provider]
        state.healthy = True
        state.request_count += 1
        state.average_latency = ((state.average_latency or 0.0) * (state.request_count - 1) + latency) / state.request_count
        state.last_checked = datetime.utcnow().isoformat()
        self._states[provider] = state

    def record_failure(self, provider: ProviderName, error_message: str, latency: Optional[float] = None) -> None:
        state = self._states[provider]
        state.healthy = False
        state.failure_count += 1
        state.request_count += 1
        if latency is not None:
            state.average_latency = ((state.average_latency or 0.0) * (state.request_count - 1) + latency) / state.request_count
        state.last_error = error_message[:500]
        state.last_checked = datetime.utcnow().isoformat()
        self._states[provider] = state

    def get_health(self, provider: ProviderName) -> ProviderHealth:
        return self._states[provider]

    def get_all_health(self) -> Dict[ProviderName, ProviderHealth]:
        return dict(self._states)


provider_monitor = ProviderMonitor()
