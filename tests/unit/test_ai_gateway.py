import pytest

from backend.app.services.ai.manager import AIManager
from backend.app.services.ai.schemas import AIRequest, ProviderName


@pytest.mark.asyncio
async def test_ai_manager_returns_failed_response_when_all_providers_fail(monkeypatch):
    manager = AIManager()

    async def fake_generate(self, request):
        return type(
            "Resp",
            (),
            {"success": False, "output": "", "error_message": "boom"},
        )

    monkeypatch.setattr(manager.providers[0], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[1], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[2], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[3], "generate", fake_generate)

    response = await manager.generate("hello")
    assert response.success is False
    assert response.error_message == "All providers failed"


@pytest.mark.asyncio
async def test_ai_manager_returns_helpful_fallback_message_when_all_providers_fail(monkeypatch):
    manager = AIManager()

    async def fake_generate(self, request):
        return type(
            "Resp",
            (),
            {"success": False, "output": "", "error_message": "boom"},
        )

    monkeypatch.setattr(manager.providers[0], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[1], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[2], "generate", fake_generate)
    monkeypatch.setattr(manager.providers[3], "generate", fake_generate)

    response = await manager.generate("Summarize this")
    assert response.success is False
    assert "provider" in response.output.lower()


@pytest.mark.asyncio
async def test_ai_request_schema_defaults():
    request = AIRequest(provider=ProviderName.gemini, model="gemini-2.5-flash", prompt="hi")
    assert request.provider == ProviderName.gemini
    assert request.prompt == "hi"
