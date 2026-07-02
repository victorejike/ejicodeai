from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.app.services.ai.schemas import AIRequest, AIResponse


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def health_check(self) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError

    def supports(self, request: AIRequest) -> bool:
        return True
