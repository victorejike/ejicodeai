"""Google Gemini Provider using official Generative Language API with Free-Tier fallback hierarchy."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import get_settings
from backend.app.services.ai.monitoring import provider_monitor
from backend.app.services.ai.provider import AIProvider
from backend.app.services.ai.schemas import AIRequest, AIResponse, ProviderName

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]


class GeminiProvider(AIProvider):
    """Production Google Gemini Provider connecting to official Google Generative Language API."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def health_check(self) -> AIResponse:
        """Check Google Gemini API availability."""
        start = time.monotonic()
        api_key = self.settings.gemini_api_key
        if not api_key:
            return AIResponse(
                provider=ProviderName.gemini,
                model=self.settings.gemini_model,
                output="unconfigured",
                elapsed_seconds=0.0,
                success=False,
                error_message="GEMINI_API_KEY is not set",
            )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"{self.base_url}/models?key={api_key}"
                resp = await client.get(url)
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
        """Execute generation with automatic model fallback and rate-limit backoff."""
        models_to_try = [request.model]
        for m in GEMINI_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = "No API key configured"
        api_key = self.settings.gemini_api_key

        if not api_key:
            logger.warning("Gemini API key missing, skipping to fallback providers")
            return AIResponse(
                provider=ProviderName.gemini,
                model=request.model,
                output="",
                success=False,
                error_message="GEMINI_API_KEY not configured",
            )

        for model_name in models_to_try:
            for attempt in range(3):
                start = time.monotonic()
                try:
                    payload: Dict[str, Any] = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": request.prompt}],
                            }
                        ],
                        "generationConfig": {
                            "temperature": request.temperature,
                            "maxOutputTokens": request.max_tokens,
                        },
                    }

                    if request.system_prompt:
                        payload["systemInstruction"] = {
                            "parts": [{"text": request.system_prompt}]
                        }

                    # Check if JSON mode requested
                    if request.metadata.get("json_mode"):
                        payload["generationConfig"]["responseMimeType"] = "application/json"

                    url = f"{self.base_url}/models/{model_name}:generateContent?key={api_key}"

                    async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                        resp = await client.post(url, json=payload)

                    if resp.status_code == 429:
                        # Rate limit hit: exponential backoff
                        wait_sec = (2 ** attempt) + 0.5
                        logger.warning(f"Gemini 429 rate limit on {model_name}. Retrying in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                    output_text = ""
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        output_text = "".join(p.get("text", "") for p in parts)

                    # Extract usage metadata
                    usage = data.get("usageMetadata", {})
                    total_tokens = usage.get("totalTokenCount", 0)

                    # Parse structured output if requested
                    structured_data = None
                    if request.metadata.get("json_mode") or "```json" in output_text:
                        structured_data = self._extract_json(output_text)

                    elapsed = time.monotonic() - start
                    provider_monitor.record_success(ProviderName.gemini, elapsed)

                    return AIResponse(
                        provider=ProviderName.gemini,
                        model=model_name,
                        output=output_text,
                        structured_output=structured_data,
                        tokens=total_tokens,
                        cost_usd=0.0,  # Free tier
                        raw_response=data,
                        elapsed_seconds=elapsed,
                        success=True,
                    )

                except Exception as exc:
                    elapsed = time.monotonic() - start
                    last_error = str(exc)
                    logger.warning(f"Gemini attempt {attempt + 1} for {model_name} failed: {exc}")
                    if attempt == 2:
                        provider_monitor.record_failure(ProviderName.gemini, str(exc), elapsed)

        return AIResponse(
            provider=ProviderName.gemini,
            model=request.model,
            output="",
            elapsed_seconds=0.0,
            success=False,
            error_message=f"Gemini failed across models: {last_error}",
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM markdown response."""
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        match_arr = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match_arr:
            try:
                return {"items": json.loads(match_arr.group(1))}
            except Exception:
                pass

        return None
