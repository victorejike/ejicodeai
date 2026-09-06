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


class FastEmbeddingFunction:
    """Fast, deterministic vector embedding function for ChromaDB with zero network overhead."""

    def __call__(self, input: List[str]) -> List[List[float]]:
        import hashlib
        embeddings = []
        for text in input:
            tokens = text.lower().split()
            vec = [0.0] * 64
            for t in tokens:
                h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
                for i in range(64):
                    vec[i] += ((h >> i) & 1) * 2 - 1
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings


class ChromaDBTool:
    """Production ChromaDB vector store supporting chunking, named collections, and metadata filtering."""

    def __init__(self):
        self._client = None
        self._initialized = False
        self._embed_fn = FastEmbeddingFunction()

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                self._client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
            except Exception as e:
                logger.warning(f"ChromaDB local client unavailable: {e}")
        return self._client

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks by words."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += (chunk_size - overlap)
        return chunks

    async def add_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        chunk: bool = False,
    ) -> int:
        """Add documents with optional text chunking."""
        try:
            client = self._get_client()
            if not client:
                return 0

            def _sync():
                col = client.get_or_create_collection(collection, embedding_function=self._embed_fn)
                ids = []
                texts = []
                metadatas = []

                for i, doc in enumerate(documents):
                    raw_text = doc.get("text", "")
                    meta = doc.get("metadata", {})
                    base_id = str(doc.get("id", f"{collection}_{i}_{int(time.time())}"))

                    if chunk and len(raw_text.split()) > 200:
                        chunks = self.chunk_text(raw_text)
                        for c_idx, ch in enumerate(chunks):
                            ids.append(f"{base_id}_chunk_{c_idx}")
                            texts.append(ch)
                            chunk_meta = meta.copy()
                            chunk_meta["chunk_index"] = c_idx
                            metadatas.append(chunk_meta)
                    else:
                        ids.append(base_id)
                        texts.append(raw_text)
                        metadatas.append(meta)

                if ids:
                    col.upsert(documents=texts, ids=ids, metadatas=metadatas)
                return len(ids)

            import time
            return await asyncio.to_thread(_sync)
        except Exception as e:
            logger.error(f"ChromaDB add error: {e}")
            return 0

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 3,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query documents with optional metadata filtering."""
        try:
            client = self._get_client()
            if not client:
                return []

            def _sync():
                col = client.get_or_create_collection(collection, embedding_function=self._embed_fn)
                kwargs: Dict[str, Any] = {"query_texts": [query_text], "n_results": n_results}
                if where:
                    kwargs["where"] = where

                results = col.query(**kwargs)
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0] if results.get("distances") else []

                return [
                    {
                        "text": d,
                        "metadata": m,
                        "distance": distances[idx] if idx < len(distances) else 0.0,
                    }
                    for idx, (d, m) in enumerate(zip(docs, metas))
                ]

            return await asyncio.to_thread(_sync)
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            return []

    async def reindex_knowledge_base(self) -> Dict[str, int]:
        """Re-seed core company capabilities and case studies for proposal generation."""
        counts = {}
        # Core Ejicode profile & value propositions
        profile_docs = [
            {
                "id": "ejicode_capabilities",
                "text": "Ejicode specializes in autonomous AI agents, high-performance FastAPI backends, PostgreSQL distributed databases, LangGraph workflows, and enterprise full-stack software development. Tagline: empathy and engineering, inseparable.",
                "metadata": {"topic": "company_profile", "author": "Ejicode"},
            },
            {
                "id": "ejicode_case_healthtech",
                "text": "Case Study: Scaled an AI clinical documentation assistant using FastAPI and vLLM, reducing latency by 45% while adhering to HIPAA compliance.",
                "metadata": {"industry": "Healthcare AI", "service": "FastAPI & AI Engineering"},
            },
            {
                "id": "ejicode_case_fintech",
                "text": "Case Study: Designed distributed Go and Kafka payment ledger reconciling $10M+ daily transactions with zero ledger drift.",
                "metadata": {"industry": "Fintech", "service": "Distributed Systems & Go"},
            },
        ]
        counts["ejicode_profile"] = await self.add_documents("ejicode_profile", profile_docs)
        return counts


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
