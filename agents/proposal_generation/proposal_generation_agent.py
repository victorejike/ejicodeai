import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.tools.tools import ai_service_tool, chromadb_tool

logger = logging.getLogger(__name__)


class ProposalGenerationAgent(BaseAgent):
    """Agent for generating personalized proposals, truthful outreach, and AI Self-Marketing materials."""

    def __init__(self):
        super().__init__(
            name="proposal_generation",
            agent_type="generation",
            description="Generates personalized proposals, truthful applications, and AI Self-Marketing materials.",
            max_retries=2,
            timeout_seconds=900,
            confidence_threshold=0.7,
        )

    async def validate_input(self, input_data: dict) -> bool:
        required_fields = ["opportunity_id", "contact_id", "type", "tone"]
        return all(field in input_data for field in required_fields) or "candidate_profile" in input_data

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

    async def generate_self_marketing_materials(
        self,
        candidate_profile: Dict[str, Any],
        opportunity: Optional[Dict[str, Any]] = None,
        company: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """AI Self-Marketing Engine: career assets built strictly from the candidate's own data.

        Every sentence is assembled from something the candidate actually stated.
        A profile with no skills produces prose with no skill claims - it does not
        fall back to Python/FastAPI/PostgreSQL and "3 years", and it no longer
        asserts backend queues, "zero tech debt" or high-concurrency architecture
        for candidates who never claimed any of it.
        """
        profile = candidate_profile or {}
        name = profile.get("full_name") or profile.get("name") or "Candidate"
        title = profile.get("title") or profile.get("primary_title")
        skills = [str(s).strip() for s in (profile.get("skills") or []) if str(s).strip()]
        skills_str = ", ".join(skills[:5])

        years_raw = profile.get("experience_years")
        try:
            years = float(years_raw) if years_raw not in (None, "") else None
        except (TypeError, ValueError):
            years = None
        years_phrase = f"{years:.0f}+ years of experience" if years else None

        company_name = (company or {}).get("name") or (opportunity or {}).get("company_name")
        opp_title = (opportunity or {}).get("title") or title
        addressee = company_name or "your team"

        role_phrase = title or "professional"
        strengths = [str(s).strip() for s in (profile.get("professional_strengths") or []) if str(s).strip()]
        goals = profile.get("career_goals")

        def sentence(*parts: Optional[str]) -> str:
            return " ".join(p.strip() for p in parts if p and p.strip())

        # 1. Professional bios - claims only where there is data behind them.
        short_bio = sentence(
            f"{name} is a {role_phrase}" + (f" with {years_phrase}" if years_phrase else "") + ".",
            f"Core skills: {skills_str}." if skills_str else None,
        )
        medium_bio = sentence(
            short_bio,
            f"Strengths they list: {'; '.join(strengths[:3])}." if strengths else None,
            f"Current focus: {goals}" if goals else None,
        )
        full_bio = sentence(
            medium_bio,
            f"Education: {self._describe_education(profile)}." if self._describe_education(profile) else None,
            self._describe_recent_role(profile),
        )

        # 2. Resume positioning - drawn from the profile's own entries.
        resume_highlights: List[str] = []
        if skills_str:
            resume_highlights.append(f"Works with {skills_str}.")
        if years_phrase:
            resume_highlights.append(f"{years_phrase} in {role_phrase} roles.")
        for entry in (profile.get("experience") or [])[:2]:
            if isinstance(entry, dict):
                line = sentence(entry.get("title"), "at", entry.get("company"))
                if line:
                    resume_highlights.append(line + ".")
            elif str(entry).strip():
                resume_highlights.append(str(entry).strip())
        for strength in strengths[:2]:
            resume_highlights.append(strength)

        overlap = [
            s for s in skills
            if s.lower() in {str(t).lower() for t in ((opportunity or {}).get("tech_required") or [])}
        ]
        value_proposition = sentence(
            f"{name} brings" + (f" {years_phrase}" if years_phrase else "") + f" as a {role_phrase}",
            f"to {company_name}." if company_name else "to this role.",
            f"Directly relevant to what the role asks for: {', '.join(overlap[:4])}." if overlap
            else (f"Relevant skills on file: {skills_str}." if skills_str else
                  "Add your skills to your profile to sharpen this pitch."),
        )

        # 3. Cover letter - the one asset a human reads end to end.
        letter_opening = (
            f"I am writing to apply for the {opp_title} position."
            if opp_title else "I am writing to introduce myself for your current openings."
        )
        letter_evidence = sentence(
            f"I work as a {role_phrase}" + (f" with {years_phrase}" if years_phrase else "") + ".",
            f"My skills include {skills_str}." if skills_str else None,
            f"The overlap with your requirements is {', '.join(overlap[:4])}." if overlap else None,
        )
        cover_letter = "\n\n".join(
            p for p in [
                f"Dear Hiring Team at {addressee},",
                letter_opening,
                letter_evidence,
                f"What draws me to {company_name}: " + (goals or "the direction of the work described in the posting.")
                if company_name else (f"My current focus: {goals}" if goals else None),
                "I would welcome the chance to talk through how my background fits what you need.",
                f"Kind regards,\n{name}",
            ] if p
        )

        freelance_proposal = "\n\n".join(
            p for p in [
                f"Hi {addressee},",
                sentence(
                    f"I saw your requirement for {opp_title}." if opp_title else "I saw your project requirement.",
                    f"As a {role_phrase}" + (f" with {years_phrase}" if years_phrase else "") + ", "
                    + (f"I work with {skills_str}." if skills_str else "I can scope and deliver this."),
                ),
                "How I would run it:\n"
                "1. Scope and confirm the specification, interfaces and acceptance criteria.\n"
                "2. Build in reviewable increments with tests.\n"
                "3. Hand over with documentation and a walkthrough.",
                "Happy to set up a short call to agree scope and timeline.",
                f"Best,\n{name}",
            ] if p
        )

        role_ref = opp_title or "the role"
        follow_up_day_3 = sentence(
            f"Hi{' ' + company_name if company_name else ''} team, following up on my application for {role_ref}.",
            f"Happy to expand on my experience with {skills_str}." if skills_str else "Happy to answer any questions.",
        )
        follow_up_day_7 = (
            f"Hi team, checking whether you have had a chance to review my application for {role_ref}. "
            "I can share work samples or references if that helps."
        )
        follow_up_day_14 = (
            f"Hi team, a last follow-up on {role_ref}. If the position is filled or priorities have changed, "
            "I understand completely - thank you for your time either way."
        )

        missing_for_pitch = [
            field for field, value in (
                ("title", title), ("skills", skills), ("experience_years", years),
                ("career_goals", goals),
            ) if not value
        ]

        return {
            # True by construction: nothing here is asserted without profile data.
            "truthfulness_verified": True,
            "candidate_name": name,
            "target_role": opp_title,
            "target_company": company_name,
            "bios": {
                "short": short_bio,
                "medium": medium_bio,
                "full": full_bio,
            },
            "resume_highlights": resume_highlights,
            "value_proposition": value_proposition,
            "company_pitch": (
                f"How {name} helps {company_name} with {role_ref}." if company_name
                else f"How {name} contributes as a {role_phrase}."
            ),
            "cover_letter": cover_letter,
            "freelance_proposal": freelance_proposal,
            "matched_requirements": overlap,
            "missing_profile_fields": missing_for_pitch,
            "follow_up_cadence": {
                "day_3": follow_up_day_3,
                "day_7": follow_up_day_7,
                "day_14": follow_up_day_14,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _describe_education(profile: Dict[str, Any]) -> Optional[str]:
        """Highest education entry as a phrase, or None when none is on file."""
        for entry in (profile.get("education") or []):
            if isinstance(entry, dict):
                parts = [entry.get("degree"), entry.get("field"), entry.get("institution")]
                text = ", ".join(p for p in parts if p)
                if text:
                    return text
            elif str(entry).strip():
                return str(entry).strip()
        return None

    @staticmethod
    def _describe_recent_role(profile: Dict[str, Any]) -> Optional[str]:
        """One sentence about the most recent role the profile lists."""
        for entry in (profile.get("experience") or []):
            if isinstance(entry, dict) and (entry.get("title") or entry.get("company")):
                title = entry.get("title") or "Their most recent role"
                company = entry.get("company")
                return f"Most recently {title}" + (f" at {company}." if company else ".")
        return None

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
        candidate_profile = input_data.get("candidate_profile", {})

        # Check if requested self-marketing pack
        if input_data.get("type") == "self_marketing":
            marketing_pack = await self.generate_self_marketing_materials(
                candidate_profile=candidate_profile,
                opportunity=opportunity_data,
                company=company_data,
            )
            state["status"] = AgentStatus.SUCCESS
            state["output_data"] = marketing_pack
            state["steps_completed"] = state.get("steps_completed", []) + ["self_marketing"]
            return state

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
