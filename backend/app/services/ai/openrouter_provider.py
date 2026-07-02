from __future__ import annotations

import time
from typing import Any

import httpx

from backend.app.config import get_settings
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName
from backend.app.services.ai.monitoring import provider_monitor


class OpenRouterProvider(AIProvider):
    """OpenRouter provider implementation."""

    def __init__(self):
        self.settings = get_settings()

    async def health_check(self) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.settings.openrouter_base_url}/models")
                resp.raise_for_status()
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.openrouter, elapsed)
            return AIResponse(
                provider=ProviderName.openrouter,
                model=self.settings.openrouter_model,
                output="healthy",
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.openrouter, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.openrouter,
                model=self.settings.openrouter_model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                body = {
                    "model": request.model,
                    "messages": [
                        {"role": "system", "content": request.system_prompt or ""},
                        {"role": "user", "content": request.prompt},
                    ],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                }
                if self.settings.openrouter_api_key:
                    headers = {"Authorization": f"Bearer {self.settings.openrouter_api_key}"}
                else:
                    headers = {}
                resp = await client.post(
                    f"{self.settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
            data = resp.json()
            output = ""
            try:
                output = data["choices"][0]["message"]["content"]
            except Exception:
                output = str(data)
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.openrouter, elapsed)
            return AIResponse(
                provider=ProviderName.openrouter,
                model=request.model,
                output=output,
                raw_response=data,
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.openrouter, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.openrouter,
                model=request.model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )
