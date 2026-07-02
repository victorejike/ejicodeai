import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.tools.tools import ai_service_tool, chromadb_tool

logger = logging.getLogger(__name__)


class ProposalGenerationAgent(BaseAgent):
    """Agent for generating personalized proposals and outreach content."""

    def __init__(self):
        super().__init__(
            name="proposal_generation",
            agent_type="generation",
            description="Generates proposals and outreach content for opportunities.",
            max_retries=2,
            timeout_seconds=900,
            confidence_threshold=0.7,
        )

    async def validate_input(self, input_data: dict) -> bool:
        required_fields = ["opportunity_id", "contact_id", "type", "tone"]
        return all(field in input_data for field in required_fields)

    async def _retrieve_rag_context(self, company_name: str, domain: str, opportunity_title: str) -> List[Dict[str, Any]]:
        query = f"Proposal context for {company_name} {domain} {opportunity_title}"
        results = await chromadb_tool.query("proposals", query, n_results=3)
        return results

    async def _run_reasoning_pass(self, company_data: dict, contact_data: dict, opportunity_data: dict) -> str:
        prompt = (
            "Analyze the following company and opportunity, then recommend the strongest outreach angle.\n"
            f"Company: {company_data.get('name', '')} ({company_data.get('domain', '')})\n"
            f"Opportunity: {opportunity_data.get('title', '')}\n"
            f"Contact: {contact_data.get('email', '')}, title={contact_data.get('title', '')}\n"
            "\n\nProvide:\n1. Key pain points\n2. Ejicode service fit\n3. Best email angle\n"
        )
        result = await ai_service_tool.reason(prompt)
        return result.get("reasoning", "")

    async def _run_refinement_pass(self, reasoning: str, rag_context: List[Dict[str, Any]], tone: str, proposal_type: str) -> Dict[str, Any]:
        subject_prompt = (
            "Create three concise subject line variants for an outreach email."
            f" Tone: {tone}. Use the following reasoning and context:\n{reasoning}\n\n"
            f"Proposal Type: {proposal_type}\n"
            "Return subject lines as JSON list."
        )

        body_prompt = (
            "Draft a personalized outreach message using the reasoning below."
            f" Tone: {tone}. Context: {reasoning}\n\n"
            f"RAG context: {rag_context}\n"
            "The email should be 150-300 words, avoid generic phrases, and focus on Ejicode's fit."
        )

        subject_text = await ai_service_tool.generate(subject_prompt, system="You are a concise outreach copywriter.")
        body_text = await ai_service_tool.generate(body_prompt, system="You are a professional business development writer.")

        subject_lines = [line.strip() for line in subject_text.splitlines() if line.strip()]
        subject = subject_lines[0] if subject_lines else "Opportunity for collaboration"

        return {
            "subject": subject,
            "subject_variants": subject_lines,
            "body": body_text,
            "generation_model": ai_service_tool.model,
            "generation_prompt": body_prompt,
        }

    async def validate_output(self, output_data: dict) -> bool:
        return bool(output_data.get("subject")) and bool(output_data.get("body"))

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        if not await self.validate_input(input_data):
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = "Invalid input for proposal generation"
            return state

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "rag_retrieval"

        opportunity_data = input_data.get("opportunity_data", {})
        contact_data = input_data.get("contact_data", {})
        company_data = input_data.get("company_data", {})

        rag_context = await self._retrieve_rag_context(
            company_name=company_data.get("name", ""),
            domain=company_data.get("domain", ""),
            opportunity_title=opportunity_data.get("title", ""),
        )

        reasoning = await self._run_reasoning_pass(company_data, contact_data, opportunity_data)
        state["steps_completed"] = ["rag_retrieval", "reasoning_pass"]

        refined = await self._run_refinement_pass(
            reasoning=reasoning,
            rag_context=rag_context,
            tone=input_data.get("tone", "professional"),
            proposal_type=input_data.get("type", "cold_email"),
        )

        proposal_body = refined.get("body", "")
        proposal_subject = refined.get("subject", "")
        word_count = len(proposal_body.split())

        output = {
            "subject": proposal_subject,
            "body": proposal_body,
            "subject_variants": refined.get("subject_variants", []),
            "word_count": word_count,
            "generation_model": refined.get("generation_model"),
            "generation_prompt": refined.get("generation_prompt"),
            "rag_context": rag_context,
            "reasoning": reasoning,
        }

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = output
        state["confidence_score"] = 0.8 if word_count >= 150 else 0.6
        state["steps_completed"].append("refinement_pass")
        return state
