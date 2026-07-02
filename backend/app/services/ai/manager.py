from __future__ import annotations

import time
from typing import List, Optional

from backend.app.config import get_settings
from backend.app.services.ai.gemini_provider import GeminiProvider
from backend.app.services.ai.monitoring import provider_monitor
from backend.app.services.ai.nvidia_provider import NvidiaProvider
from backend.app.services.ai.openrouter_provider import OpenRouterProvider
from backend.app.services.ai.ollama_provider import OllamaProvider
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.retry import execute_with_retry
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName


class AIManager:
    """Provider-agnostic AI gateway with automatic failover."""

    def __init__(self):
        self.settings = get_settings()
        self.providers: List[AIProvider] = [
            GeminiProvider(),
            NvidiaProvider(),
            OllamaProvider(),
            OpenRouterProvider(),
        ]
        self.primary_model = self.settings.gemini_model
        self.secondary_model = self.settings.nvidia_model
        self.local_model = self.settings.ollama_model
        self.emergency_model = self.settings.openrouter_model

    async def _get_provider_sequence(self) -> List[AIProvider]:
        return self.providers

    async def health(self) -> List[AIResponse]:
        healths = []
        for provider in await self._get_provider_sequence():
            healths.append(await provider.health_check())
        return healths

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.7, timeout_seconds: int = 60) -> AIResponse:
        request = AIRequest(
            provider=ProviderName.gemini,
            model=self.primary_model,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )

        for provider in await self._get_provider_sequence():
            request.provider = ProviderName(provider.__class__.__name__.replace("Provider", "").lower())
            request.model = self._get_model_for_provider(request.provider)
            try:
                response = await execute_with_retry(provider.generate, request)
                if response.success and response.output:
                    return response
                continue
            except Exception as exc:
                provider_monitor.record_failure(request.provider, str(exc))
                continue

        fallback_message = (
            "No AI provider is currently available. Configure a provider API key or run a local model "
            "to enable AI-powered responses."
        )
        return AIResponse(
            provider=ProviderName.openrouter,
            model=self.emergency_model,
            output=fallback_message,
            elapsed_seconds=0.0,
            success=False,
            error_message="All providers failed",
        )

    def _get_model_for_provider(self, provider: ProviderName) -> str:
        if provider == ProviderName.nvidia:
            return self.secondary_model
        if provider == ProviderName.ollama:
            return self.local_model
        if provider == ProviderName.openrouter:
            return self.emergency_model
        return self.primary_model


ai_manager = AIManager()
