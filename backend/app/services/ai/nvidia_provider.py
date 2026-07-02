from __future__ import annotations

import time
from typing import Any, Dict

import httpx

from backend.app.config import get_settings
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName
from backend.app.services.ai.monitoring import provider_monitor


class NvidiaProvider(AIProvider):
    """NVIDIA NIM provider implementation."""

    def __init__(self):
        self.settings = get_settings()

    async def health_check(self) -> AIResponse:
        start = time.monotonic()
        
        if not self.settings.nvidia_api_key:
            return AIResponse(
                provider=ProviderName.nvidia,
                model=self.settings.nvidia_model,
                output="",
                elapsed_seconds=0,
                success=False,
                error_message="NVIDIA API key not configured",
            )
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {
                    "Authorization": f"Bearer {self.settings.nvidia_api_key}",
                    "Content-Type": "application/json",
                }
                # Simple health check via a minimal request
                body = {
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10,
                }
                resp = await client.post(
                    self.settings.nvidia_base_url,
                    headers=headers,
                    json=body,
                    timeout=5,
                )
                resp.raise_for_status()
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.nvidia, elapsed)
            return AIResponse(
                provider=ProviderName.nvidia,
                model=self.settings.nvidia_model,
                output="healthy",
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.nvidia, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.nvidia,
                model=self.settings.nvidia_model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        try:
            if not self.settings.nvidia_api_key:
                return AIResponse(
                    provider=ProviderName.nvidia,
                    model=request.model,
                    output="",
                    elapsed_seconds=0,
                    success=False,
                    error_message="NVIDIA API key not configured",
                )

            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                headers = {
                    "Authorization": f"Bearer {self.settings.nvidia_api_key}",
                    "Content-Type": "application/json",
                }
                
                # NVCF API format
                body: Dict[str, Any] = {
                    "messages": [
                        {
                            "role": "system",
                            "content": request.system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": request.prompt},
                    ],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "top_p": 0.7,
                }
                
                # Try NVCF endpoint
                resp = await client.post(
                    self.settings.nvidia_base_url,
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                
            data = resp.json()
            
            # Extract output from NVCF response format
            if isinstance(data, dict):
                if "choices" in data:
                    output = data["choices"][0].get("message", {}).get("content", "")
                elif "result" in data and "output" in data["result"]:
                    output = data["result"]["output"].get("message", {}).get("content", "")
                else:
                    output = str(data)
            else:
                output = str(data)
            
            elapsed = time.monotonic() - start
            provider_monitor.record_success(ProviderName.nvidia, elapsed)
            return AIResponse(
                provider=ProviderName.nvidia,
                model=request.model,
                output=output or "No output generated",
                raw_response=data,
                elapsed_seconds=elapsed,
                success=bool(output),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            provider_monitor.record_failure(ProviderName.nvidia, str(exc), elapsed)
            return AIResponse(
                provider=ProviderName.nvidia,
                model=request.model,
                output="",
                elapsed_seconds=elapsed,
                success=False,
                error_message=str(exc),
            )
