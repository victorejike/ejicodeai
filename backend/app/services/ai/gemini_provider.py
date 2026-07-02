from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from backend.app.config import get_settings
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName
from backend.app.services.ai.monitoring import provider_monitor


class GeminiProvider(AIProvider):
    """Google Gemini provider implementation."""

    def __init__(self):
        self.settings = get_settings()

    async def health_check(self) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://gemini.google.com/v1/models")
                resp.raise_for_status()
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.gemini, elapsed)
            return AIResponse(
                provider=ProviderName.gemini,
                model=self.settings.gemini_model,
                output="healthy",
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.gemini, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.gemini,
                model=self.settings.gemini_model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                headers = {}
                if self.settings.gemini_api_key:
                    headers["Authorization"] = f"Bearer {self.settings.gemini_api_key}"
                body: Dict[str, Any] = {
                    "model": request.model,
                    "prompt": request.prompt,
                    "temperature": request.temperature,
                    "max_output_tokens": request.max_tokens,
                }
                resp = await client.post(
                    "https://gemini.google.com/v1/engines/" + request.model + "/completions",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
            data = resp.json()
            output = data.get("output", {}).get("text", "") if isinstance(data, dict) else str(data)
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.gemini, elapsed)
            return AIResponse(
                provider=ProviderName.gemini,
                model=request.model,
                output=output,
                raw_response=data,
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.gemini, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.gemini,
                model=request.model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )
