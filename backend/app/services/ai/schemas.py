from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    gemini = "gemini"
    nvidia = "nvidia"
    ollama = "ollama"
    openrouter = "openrouter"


class AIRequest(BaseModel):
    provider: ProviderName
    model: str
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout_seconds: int = 60
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIResponse(BaseModel):
    provider: ProviderName
    model: str
    output: str
    structured_output: Optional[Dict[str, Any]] = None
    tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None
    elapsed_seconds: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


class ProviderHealth(BaseModel):
    provider: ProviderName
    healthy: bool
    last_checked: Optional[str] = None
    last_error: Optional[str] = None
    request_count: int = 0
    failure_count: int = 0
    average_latency: Optional[float] = None
