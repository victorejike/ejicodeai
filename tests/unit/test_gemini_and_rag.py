"""Test official Gemini API provider and RAG Knowledge Base tools."""
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.ai.gemini_provider import GeminiProvider
from backend.app.services.ai.schemas import AIRequest, ProviderName
from agents.tools.tools import ChromaDBTool


@pytest.mark.asyncio
async def test_gemini_provider_json_extraction():
    provider = GeminiProvider()
    
    # Test JSON markdown parser
    text_with_json = 'Here is the response:\n```json\n{"fit_score": 95, "reasoning": "Strong match"}\n```'
    parsed = provider._extract_json(text_with_json)
    assert parsed is not None
    assert parsed["fit_score"] == 95

    # Test raw JSON
    raw_json = '{"decision_maker": true, "email": "test@domain.com"}'
    parsed_raw = provider._extract_json(raw_json)
    assert parsed_raw is not None
    assert parsed_raw["decision_maker"] is True


@pytest.mark.asyncio
async def test_chromadb_tool_chunking_and_query():
    tool = ChromaDBTool()
    
    long_text = " ".join([f"Word{i}" for i in range(300)])
    chunks = tool.chunk_text(long_text, chunk_size=100, overlap=10)
    assert len(chunks) >= 3

    # Test adding documents and querying in-memory ChromaDB
    docs = [
        {"id": "doc1", "text": "Ejicode builds autonomous AI agents and FastAPI systems.", "metadata": {"tech": "python"}},
        {"id": "doc2", "text": "Acme Corp needs a distributed Kafka payment gateway.", "metadata": {"tech": "go"}},
    ]
    added = await tool.add_documents("test_collection", docs)
    assert added == 2

    # Query semantic match
    results = await tool.query("test_collection", "FastAPI AI agents", n_results=1)
    assert len(results) == 1
    assert "Ejicode" in results[0]["text"]
