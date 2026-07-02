from __future__ import annotations

import time
from typing import Optional

import httpx

from backend.app.config import get_settings
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName
from backend.app.services.ai.monitoring import provider_monitor


class OllamaProvider(AIProvider):
    """Local Ollama provider implementation."""

    def __init__(self):
        self.settings = get_settings()

    async def health_check(self) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.settings.ollama_base_url}/api/version")
                resp.raise_for_status()
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.ollama, elapsed)
            return AIResponse(
                provider=ProviderName.ollama,
                model=self.settings.ollama_model,
                output="healthy",
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.ollama, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.ollama,
                model=self.settings.ollama_model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.settings.ollama_base_url}/api/generate",
                    json={
                        "model": request.model,
                        "prompt": request.prompt,
                        "max_tokens": request.max_tokens,
                        "temperature": request.temperature,
                    },
                )
                resp.raise_for_status()
            response = resp.json()
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.ollama, elapsed)
            return AIResponse(
                provider=ProviderName.ollama,
                model=request.model,
                output=response.get("generated_text", ""),
                raw_response=response,
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.ollama, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.ollama,
                model=request.model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )
