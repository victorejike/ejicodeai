"""Agent tools — centralized AI gateway, ChromaDB, email validation, utilities."""
import asyncio
import logging
from typing import Dict, Any, List, Optional

from backend.app.services.ai.manager import ai_manager

logger = logging.getLogger(__name__)


class AIServiceTool:
    """Agent-facing AI tool wrapper that delegates to the centralized AIManager."""

    @property
    def model(self) -> str:
        return ai_manager.primary_model

    async def generate(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.7, timeout_seconds: int = 60) -> str:
        response = await ai_manager.generate(
            prompt=prompt,
            system_prompt=system,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
        return response.output or ""

    async def reason(self, problem: str, system: Optional[str] = None, max_tokens: int = 2048, temperature: float = 0.3, timeout_seconds: int = 120) -> Dict[str, Any]:
        response = await ai_manager.generate(
            prompt=problem,
            system_prompt=system,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
        return {"reasoning": response.output or "", "model": response.model, "error": response.error_message}


class ChromaDBTool:
    """ChromaDB vector store — in-memory fallback if server unavailable."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.Client()
            except Exception as e:
                logger.warning(f"ChromaDB unavailable: {e}")
        return self._client

    async def add_documents(self, collection: str, documents: List[Dict[str, Any]]) -> int:
        try:
            client = self._get_client()
            if not client:
                return 0

            def _sync():
                col = client.get_or_create_collection(collection)
                ids = [str(doc.get("id", i)) for i, doc in enumerate(documents)]
                texts = [doc.get("text", "") for doc in documents]
                metadatas = [doc.get("metadata", {}) for doc in documents]
                col.add(documents=texts, ids=ids, metadatas=metadatas)
                return len(documents)

            return await asyncio.to_thread(_sync)
        except Exception as e:
            logger.error(f"ChromaDB add error: {e}")
            return 0

    async def query(self, collection: str, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            if not client:
                return []

            def _sync():
                col = client.get_or_create_collection(collection)
                results = col.query(query_texts=[query_text], n_results=n_results)
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                return [{"text": d, "metadata": m} for d, m in zip(docs, metas)]

            return await asyncio.to_thread(_sync)
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            return []


class EmailValidationTool:
    async def validate_syntax(self, email: str) -> bool:
        import re
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

    async def verify_smtp(self, email: str) -> bool:
        try:
            import smtplib
            import dns.resolver

            if not await self.validate_syntax(email):
                return False

            domain = email.split("@")[1]

            def _check():
                try:
                    records = dns.resolver.resolve(domain, "MX")
                    mx_host = str(records[0].exchange)
                    with smtplib.SMTP(mx_host, 25, timeout=10) as s:
                        s.helo()
                        s.mail("verify@ejicode.com")
                        code, _ = s.rcpt(email)
                        return code == 250
                except Exception:
                    return False

            return await asyncio.to_thread(_check)
        except Exception:
            return await self.validate_syntax(email)


class DataExtractionTool:
    async def extract_tech_stack(self, content: str) -> List[str]:
        technologies = [
            "Python", "Go", "JavaScript", "TypeScript", "React", "Vue",
            "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "FastAPI", "Django", "Flask", "AWS", "GCP", "Azure",
            "GraphQL", "REST API", "Microservices", "AI", "ML", "LLM",
        ]
        content_lower = content.lower()
        return [t for t in technologies if t.lower() in content_lower]

    async def extract_company_size(self, content: str) -> Optional[str]:
        content_lower = content.lower()
        if any(w in content_lower for w in ["startup", "early stage", "bootstrapped"]):
            return "startup"
        elif any(w in content_lower for w in ["series a", "series b", "growing"]):
            return "small"
        elif any(w in content_lower for w in ["series c", "series d", "scaling"]):
            return "mid"
        elif any(w in content_lower for w in ["enterprise", "public", "large"]):
            return "enterprise"
        return None


# Singletons
ai_service_tool = AIServiceTool()
chromadb_tool = ChromaDBTool()
email_tool = EmailValidationTool()
extraction_tool = DataExtractionTool()
