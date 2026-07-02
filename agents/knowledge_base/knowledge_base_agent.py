"""Knowledge Base Agent — manages ChromaDB embeddings and RAG context."""
import logging
from typing import List, Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.tools.tools import chromadb_tool

logger = logging.getLogger(__name__)


class KnowledgeBaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="knowledge_base",
            agent_type="memory",
            description="Maintains knowledge base and RAG infrastructure via ChromaDB",
            max_retries=1,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return True

    async def process(self, state: AgentState) -> AgentState:
        operation = state.get("input_data", {}).get("operation", "sync")
        self.logger.info(f"Knowledge Base Agent: '{operation}'")
        state["status"] = AgentStatus.RUNNING

        if operation == "sync":
            documents = state.get("input_data", {}).get("documents", [])
            stored = await chromadb_tool.add_documents("proposals", documents) if documents else 0
            return self._update_state(state, {
                "current_step": "sync_complete",
                "output_data": {"stored_documents": stored},
                "status": AgentStatus.SUCCESS,
            })

        elif operation == "retrieve":
            query = state.get("input_data", {}).get("query", "")
            collection = state.get("input_data", {}).get("collection", "proposals")
            results = await chromadb_tool.query(collection, query)
            return self._update_state(state, {
                "current_step": "retrieval_complete",
                "output_data": {"results": results},
                "status": AgentStatus.SUCCESS,
            })

        return self._update_state(state, {
            "status": AgentStatus.FAILURE,
            "error_message": f"Unknown operation: {operation}",
        })

    async def validate_output(self, output_data: dict) -> bool:
        return bool(output_data)
