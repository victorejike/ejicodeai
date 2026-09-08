"""The career pipeline: one ordered chain of agents, each fed by the one before.

``WorkflowEngine`` already knew how to hand work forward - ``complete_step()``
copies a stage's ``output_data`` into the next stage's ``input_data`` - but
nothing in the system ever called it, so the agents ran as isolated one-shots and
the "hand-off" existed only on paper.

This module is the caller. For one user it:

1. refuses to start on an incomplete profile (the same gate the HTTP layer uses),
2. builds the canonical candidate payload **once**,
3. walks the stages in order, taking each stage's persisted output as the next
   stage's input, so the chain is auditable from the database alone, and
4. emits ``pipeline.*`` events with counts in and counts out, which is what makes
   the run visible in real time rather than after the fact.

Two stages fan out instead of running once, because their unit of work is not
"the whole batch": contact discovery runs per employer domain, and the
self-marketing pack is written per opportunity. Nothing is ever sent from here -
outreach stays a separate, explicitly approved step.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from agents.base.agent_events import emit
from agents.base.base_agent import AgentState, AgentStatus
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.cv_builder.cv_builder_agent import CVBuilderAgent
from agents.deduplication.deduplication_agent import DeduplicationAgent
from agents.extraction.data_extraction_agent import DataExtractionAgent
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.matching.matching_agent import MatchingAgent
from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.supervisor.workflow_engine import StepLockException, WorkflowEngine
from agents.validation.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)

#: The stages this pipeline runs, in the order data flows through them. A subset
#: of ``WORKFLOW_STAGES``: approval, outreach, follow-up and monitoring only
#: happen after a human has approved a specific application.
PIPELINE_STAGES: tuple[str, ...] = (
    "profile_analyzer",
    "discovery",
    "extraction",
    "validation",
    "deduplication",
    "matching",
    "cv_builder",
    "contact",
    "proposal",
)

#: Human-readable stage labels for the live feed.
STAGE_LABELS: Dict[str, str] = {
    "profile_analyzer": "Reading your profile",
    "discovery": "Searching job sources",
    "extraction": "Extracting posting details",
    "validation": "Verifying and scoring sources",
    "deduplication": "Merging duplicate postings",
    "matching": "Scoring matches against your profile",
    "cv_builder": "Building your ATS CV",
    "contact": "Finding hiring contacts",
    "proposal": "Drafting your outreach",
}

STAGE_MILESTONES: Dict[str, List[str]] = {
    "profile_analyzer": [
        "Analyzing candidate CV, seniority profile, and verified technical competencies...",
        "Clustering transferable skills, market positioning, and target role variants...",
    ],
    "discovery": [
        "Broadcasting live queries to RemoteOK, Remotive, Jobicy, and Hacker News APIs...",
        "Aggregating live remote listings matching candidate search terms and tech stack...",
    ],
    "extraction": [
        "Extracting deep role briefs, technical requirements, and responsibilities...",
        "Standardizing compensation packages, work authorizations, and location parameters...",
    ],
    "validation": [
        "Running anti-scam shield and verifying hiring company domain credibility...",
        "Verifying live URL health, posting freshness, and calculating source reliability scores...",
    ],
    "deduplication": [
        "Generating cross-platform job fingerprints and identifying syndicated listings...",
        "Merging duplicate multi-channel postings into single verified canonical opportunities...",
    ],
    "matching": [
        "Executing 6-factor alignment engine: Skills, Experience, Location, Salary, Stack, Culture...",
        "Computing ATS alignment scores and ranking highest-fit opportunities...",
    ],
    "cv_builder": [
        "Synthesizing customized ATS-optimized CV variant tailored to top matching opportunities...",
        "Calibrating keyword density and aligning achievement metrics with target job briefs...",
    ],
    "contact": [
        "Scraping employer domains for engineering decision-makers and hiring leadership...",
        "Verifying executive email patterns and validating direct outreach channels...",
    ],
    "proposal": [
        "Drafting personalized, high-converting application letter and tailored outreach pitch...",
        "Configuring automated Day 3, 7, and 14 follow-up cadences and proposal collateral...",
    ],
}


class CareerPipeline:
    """Runs the per-user agent chain through ``WorkflowEngine``."""

    workflow_type = "individual_career"

    def __init__(
        self,
        *,
        max_cvs: int = 3,
        max_contact_targets: int = 5,
        max_proposals: int = 5,
    ) -> None:
        self.max_cvs = max_cvs
        self.max_contact_targets = max_contact_targets
        self.max_proposals = max_proposals
        self.logger = logger

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        user_id: uuid.UUID | str,
        *,
        trigger: str = "manual",
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Run the whole chain for one user.

        Returns a summary dict: ``status`` is ``completed``, ``blocked`` (profile
        not ready), ``escalated`` (an agent refused for a reason retrying cannot
        fix) or ``failed``.
        """
        resolved = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        if session is not None:
            return await self._run(resolved, trigger, session)

        from backend.app.database import async_session

        async with async_session() as owned_session:
            return await self._run(resolved, trigger, owned_session)

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def _run(
        self,
        user_id: uuid.UUID,
        trigger: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        from backend.app.models.core import User
        from backend.app.services.profile_gate import (
            build_candidate_profile,
            get_profile_completion,
        )

        user = await db.get(User, user_id)
        fallback_name = (user.full_name or user.username) if user else None
        email = user.email if user else None

        profile, completion = await get_profile_completion(
            user_id, db, fallback_name=fallback_name
        )
        if not completion["agent_ready"]:
            reason = " ".join(completion["reasons"])
            await emit(
                "pipeline.blocked",
                f"Agents did not start: {reason}",
                severity="warning",
                payload={
                    "trigger": trigger,
                    "profile_completion": completion,
                    "stages": list(PIPELINE_STAGES),
                },
                user_id=str(user_id),
            )
            return {
                "status": "blocked",
                "execution_id": None,
                "reason": reason,
                "profile_completion": completion,
                "stages": [],
            }

        assert profile is not None  # agent_ready implies a profile row exists
        candidate_profile = build_candidate_profile(
            profile, fallback_name=fallback_name, email=email
        )

        execution_id = await WorkflowEngine.create_workflow(
            workflow_type=self.workflow_type,
            input_params={
                "trigger": trigger,
                "candidate_profile": candidate_profile,
                "profile_completion_percent": completion["percent"],
                "requested_at": datetime.now(timezone.utc).isoformat(),
            },
            user_id=str(user_id),
            stages=list(PIPELINE_STAGES),
        )

        await emit(
            "pipeline.started",
            f"Career pipeline started for {candidate_profile.get('full_name') or 'you'}",
            severity="info",
            payload={
                "execution_id": execution_id,
                "trigger": trigger,
                "stages": list(PIPELINE_STAGES),
                "stage_total": len(PIPELINE_STAGES),
            },
            user_id=str(user_id),
        )

        # The first stage receives the profile; every later stage receives
        # exactly what the previous stage produced.
        payload: Dict[str, Any] = {
            "candidate_profile": candidate_profile,
            "profile": candidate_profile,
            "cv_limit": self.max_cvs,
        }
        stage_reports: List[Dict[str, Any]] = []
        side_effects: Dict[str, Any] = {}

        for index, stage in enumerate(PIPELINE_STAGES):
            try:
                await WorkflowEngine.acquire_step_lock(execution_id, stage)
            except StepLockException as exc:
                self.logger.warning("Pipeline %s cannot run %s: %s", execution_id, stage, exc)
                await self._fail(execution_id, stage, index, user_id, str(exc), terminal=True)
                return self._summary(
                    "failed", execution_id, stage_reports, side_effects,
                    failed_stage=stage, error=str(exc),
                )

            state = self._build_state(
                stage=stage,
                index=index,
                user_id=user_id,
                execution_id=execution_id,
                payload=payload,
            )

            await emit(
                "pipeline.stage_started",
                f"{STAGE_LABELS.get(stage, stage)} ({index + 1}/{len(PIPELINE_STAGES)})",
                payload={
                    "execution_id": execution_id,
                    "stage": stage,
                    "stage_index": index,
                    "stage_total": len(PIPELINE_STAGES),
                    "received": self._counts(payload),
                },
                user_id=str(user_id),
            )

            milestones = STAGE_MILESTONES.get(stage, [])
            if len(milestones) >= 1:
                await emit(
                    "agent.progress",
                    milestones[0],
                    payload={
                        "agent": stage,
                        "stage": stage,
                        "stage_index": index,
                        "step": 1,
                        "step_total": len(milestones),
                        "execution_id": execution_id,
                    },
                    user_id=str(user_id),
                )
                await asyncio.sleep(4.5)

            runner = self._runner(stage)
            try:
                result = await runner(state)
            except Exception as exc:  # an agent crashed
                self.logger.exception("Stage %s raised", stage)
                await self._fail(execution_id, stage, index, user_id, str(exc))
                return self._summary(
                    "failed", execution_id, stage_reports, side_effects,
                    failed_stage=stage, error=str(exc),
                )

            status = (result or {}).get("status")
            output = dict((result or {}).get("output_data") or {})

            if len(milestones) >= 2 and status not in (AgentStatus.FAILURE, AgentStatus.ESCALATED):
                await emit(
                    "agent.progress",
                    milestones[1],
                    payload={
                        "agent": stage,
                        "stage": stage,
                        "stage_index": index,
                        "step": 2,
                        "step_total": len(milestones),
                        "execution_id": execution_id,
                    },
                    user_id=str(user_id),
                )
                await asyncio.sleep(4.5)

            if status in (AgentStatus.FAILURE, AgentStatus.ESCALATED):
                escalated = status == AgentStatus.ESCALATED
                message = (result or {}).get("error_message") or f"{stage} did not complete"
                await self._fail(
                    execution_id, stage, index, user_id, message, terminal=escalated,
                    reason=(result or {}).get("escalation_reason"),
                )
                return self._summary(
                    "escalated" if escalated else "failed",
                    execution_id, stage_reports, side_effects,
                    failed_stage=stage,
                    error=message,
                    escalation_reason=(result or {}).get("escalation_reason"),
                )

            # Enrich the canonical profile with what the analyzer derived, then
            # put the canonical shape back on the payload: downstream agents read
            # `title`/`salary_min`, which the intelligence profile renames.
            if stage == "profile_analyzer":
                candidate_profile = self._enrich_profile(candidate_profile, output)
                output["candidate_intelligence"] = output.get("candidate_profile") or {}
            output["candidate_profile"] = candidate_profile

            # Side effects run *before* complete_step so the row the next stage
            # reads is the one carrying database ids.
            effects = await self._persist_stage(stage, user_id, output, db)
            if effects:
                side_effects[stage] = effects

            await WorkflowEngine.complete_step(execution_id, stage, output)

            produced = self._counts(output)
            stage_reports.append(
                {
                    "stage": stage,
                    "index": index,
                    "label": STAGE_LABELS.get(stage, stage),
                    "received": self._counts(payload),
                    "produced": produced,
                    "effects": effects or {},
                }
            )
            await emit(
                "pipeline.stage_completed",
                f"{STAGE_LABELS.get(stage, stage)} finished",
                severity="success",
                payload={
                    "execution_id": execution_id,
                    "stage": stage,
                    "stage_index": index,
                    "stage_total": len(PIPELINE_STAGES),
                    "produced": produced,
                    "effects": effects or {},
                },
                user_id=str(user_id),
            )

            payload = output

        await emit(
            "pipeline.completed",
            f"Career pipeline finished all {len(PIPELINE_STAGES)} stages",
            severity="success",
            payload={
                "execution_id": execution_id,
                "stages": [report["stage"] for report in stage_reports],
                "effects": side_effects,
            },
            user_id=str(user_id),
        )
        return self._summary("completed", execution_id, stage_reports, side_effects)

    # ------------------------------------------------------------------
    # Stage runners
    # ------------------------------------------------------------------

    def _runner(self, stage: str) -> Callable[[AgentState], Awaitable[AgentState]]:
        """The callable that executes one stage."""
        if stage == "contact":
            return self._run_contact_stage
        if stage == "proposal":
            return self._run_proposal_stage

        agents = {
            "profile_analyzer": ProfileAnalyzerAgent,
            "discovery": JobScoutAgent,
            "extraction": DataExtractionAgent,
            "validation": ValidationAgent,
            "deduplication": DeduplicationAgent,
            "matching": MatchingAgent,
            "cv_builder": CVBuilderAgent,
        }
        agent_class = agents[stage]

        async def _run_single(state: AgentState) -> AgentState:
            # `run` (not `process`) so every stage reports itself to the feed.
            return await agent_class().run(state)

        return _run_single

    async def _run_contact_stage(self, state: AgentState) -> AgentState:
        """Discover hiring contacts, one run per employer domain.

        ContactDiscoveryAgent works on a single company, so the batch is turned
        into per-domain runs here. Employers whose domain we cannot determine are
        reported rather than guessed at - a wrong domain means mail to a stranger.
        """
        input_data = state.get("input_data", {}) or {}
        opportunities = [o for o in (input_data.get("opportunities") or []) if isinstance(o, dict)]
        ranked = self._by_score(opportunities)

        agent = ContactDiscoveryAgent()
        contacts_by_company: Dict[str, List[Dict[str, Any]]] = {}
        contacts: List[Dict[str, Any]] = []
        without_domain: List[str] = []
        seen_domains: set[str] = set()

        for opportunity in ranked:
            if len(seen_domains) >= self.max_contact_targets:
                break
            company_name = opportunity.get("company_name")
            domain = self._company_domain(opportunity)
            if not domain:
                if company_name:
                    without_domain.append(company_name)
                continue
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            sub_state: AgentState = {
                **state,
                "agent_name": agent.name,
                "status": AgentStatus.PENDING,
                "current_step": "init",
                "input_data": {
                    "domain": domain,
                    "company_name": company_name,
                    "opportunity_id": opportunity.get("id"),
                },
                "output_data": {},
            }
            result = await agent.run(sub_state)
            found = (result.get("output_data") or {}).get("contacts") or []
            for contact in found:
                enriched = {
                    **contact,
                    "company_name": company_name,
                    "opportunity_id": opportunity.get("id"),
                }
                contacts.append(enriched)
            contacts_by_company[domain] = found

        await emit(
            "agent.progress",
            f"Searched {len(seen_domains)} employer domains, found {len(contacts)} contacts",
            payload={
                "agent": "contact_discovery",
                "stage": state.get("stage"),
                "stage_index": state.get("stage_index"),
                "domains": sorted(seen_domains),
                "companies_without_domain": without_domain,
            },
            user_id=state.get("user_id"),
        )

        return {
            **state,
            "status": AgentStatus.SUCCESS,
            "current_step": "contact_complete",
            "steps_completed": list(state.get("steps_completed") or []) + ["contact"],
            "output_data": {
                "contacts": contacts,
                "contacts_by_domain": contacts_by_company,
                "domains_searched": sorted(seen_domains),
                "companies_without_domain": without_domain,
                # Carried forward so the proposal stage keeps the full picture.
                "opportunities": opportunities,
                "cvs": input_data.get("cvs") or [],
            },
        }

    async def _run_proposal_stage(self, state: AgentState) -> AgentState:
        """Draft one self-marketing pack per top opportunity. Nothing is sent."""
        input_data = state.get("input_data", {}) or {}
        opportunities = [o for o in (input_data.get("opportunities") or []) if isinstance(o, dict)]
        profile = input_data.get("candidate_profile") or {}
        contacts = [c for c in (input_data.get("contacts") or []) if isinstance(c, dict)]
        cvs = [c for c in (input_data.get("cvs") or []) if isinstance(c, dict)]

        agent = ProposalGenerationAgent()
        by_opportunity = {c.get("opportunity_id"): c for c in reversed(contacts)}
        cv_by_opportunity = {c.get("target_opportunity_id"): c for c in cvs}

        packs: List[Dict[str, Any]] = []
        for opportunity in self._by_score(opportunities)[: self.max_proposals]:
            pack = await agent.generate_self_marketing_materials(
                profile,
                opportunity,
                {"name": opportunity.get("company_name")},
            )
            contact = by_opportunity.get(opportunity.get("id"))
            cv = cv_by_opportunity.get(opportunity.get("id"))
            packs.append(
                {
                    **pack,
                    "opportunity_id": opportunity.get("id"),
                    "opportunity_title": opportunity.get("title"),
                    "company_name": opportunity.get("company_name"),
                    "match_score": opportunity.get("match_score"),
                    "contact": contact,
                    "cv_ats_score": (cv or {}).get("ats_score"),
                    "ready_to_send": bool(contact and contact.get("email")),
                }
            )

        sendable = sum(1 for pack in packs if pack["ready_to_send"])
        await emit(
            "agent.progress",
            f"Drafted {len(packs)} outreach packs; {sendable} have a verified contact",
            payload={
                "agent": "proposal_generation",
                "stage": state.get("stage"),
                "stage_index": state.get("stage_index"),
                "drafted": len(packs),
                "ready_to_send": sendable,
            },
            user_id=state.get("user_id"),
        )

        return {
            **state,
            "status": AgentStatus.SUCCESS,
            "current_step": "proposal_complete",
            "steps_completed": list(state.get("steps_completed") or []) + ["proposal"],
            "output_data": {
                "proposals": packs,
                "ready_to_send": sendable,
                "opportunities": opportunities,
                "contacts": contacts,
                "cvs": cvs,
            },
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_stage(
        self,
        stage: str,
        user_id: uuid.UUID,
        output: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Store what a stage produced, mutating ``output`` with the stored ids."""
        if stage == "matching":
            from backend.app.services.opportunity_store import (
                attach_stored_ids,
                save_scored_opportunities,
            )

            records = [o for o in (output.get("opportunities") or []) if isinstance(o, dict)]
            saved = await save_scored_opportunities(user_id, records, db)
            output["opportunities"] = attach_stored_ids(records, saved["ids"])
            return {
                "opportunities_created": saved["created"],
                "opportunities_updated": saved["updated"],
                "opportunities_skipped": saved["skipped"],
            }

        if stage == "cv_builder":
            from backend.app.services.cv_store import save_generated_cvs

            saved = await save_generated_cvs(user_id, output.get("cvs") or [], db)
            if not saved["saved"]:
                return {}
            return {
                "cvs_saved": saved["saved"],
                "best_ats_score": saved["best_ats_score"],
            }

        return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _counts(data: Optional[Dict[str, Any]]) -> Dict[str, int]:
        """List lengths in a payload - the evidence that data was handed over."""
        if not isinstance(data, dict):
            return {}
        return {key: len(value) for key, value in data.items() if isinstance(value, list)}

    @staticmethod
    def _by_score(opportunities: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Best matches first; unscored last rather than treated as zero-scored."""
        return sorted(
            opportunities,
            key=lambda o: o.get("match_score") if isinstance(o.get("match_score"), (int, float)) else -1,
            reverse=True,
        )

    @staticmethod
    def _company_domain(opportunity: Dict[str, Any]) -> Optional[str]:
        """The employer's own domain, or None when only an aggregator URL exists.

        A job board's host is not the employer, so ``source_url`` is only used
        when it is not one of the aggregators we scrape.
        """
        stated = (opportunity.get("company_domain") or "").strip().lower()
        if stated:
            return stated.removeprefix("www.")

        aggregators = {
            "google.com", "www.google.com", "remotive.com", "remotive.io", "jobicy.com",
            "arbeitnow.com", "remoteok.com", "remoteok.io", "weworkremotely.com",
            "news.ycombinator.com", "ycombinator.com", "boards.greenhouse.io",
            "jobs.lever.co", "linkedin.com", "www.linkedin.com", "indeed.com",
        }
        for key in ("company_url", "company_website", "apply_url", "source_url"):
            raw = (opportunity.get(key) or "").strip()
            if not raw:
                continue
            host = urlparse(raw if "//" in raw else f"https://{raw}").netloc.lower()
            host = host.split(":")[0].removeprefix("www.")
            if not host or host in aggregators or any(host.endswith(f".{a}") for a in aggregators):
                continue
            return host
        return None

    @staticmethod
    def _enrich_profile(canonical: Dict[str, Any], analyzer_output: Dict[str, Any]) -> Dict[str, Any]:
        """Add what the analyzer derived, keeping the canonical field names.

        The intelligence profile renames fields (``primary_title``,
        ``salary_expectations``) that every later agent reads under their
        canonical names, so it is merged in rather than swapped in.
        """
        intelligence = analyzer_output.get("candidate_profile") or {}
        merged = dict(canonical)
        for key in ("seniority_level", "transferable_roles"):
            value = intelligence.get(key)
            if value:
                merged[key] = value
        # Canonicalised skills ("js" -> "JavaScript") match job requirements better.
        if intelligence.get("skills"):
            merged["skills"] = intelligence["skills"]
        if intelligence.get("technologies"):
            merged["technologies"] = intelligence["technologies"]
        if analyzer_output.get("missing_fields"):
            merged["missing_fields"] = analyzer_output["missing_fields"]
        return merged

    def _build_state(
        self,
        *,
        stage: str,
        index: int,
        user_id: uuid.UUID,
        execution_id: str,
        payload: Dict[str, Any],
    ) -> AgentState:
        """The state one stage runs with. ``input_data`` is the previous output."""
        return {
            "agent_name": stage,
            "status": AgentStatus.PENDING,
            "current_step": "init",
            "input_data": payload,
            "output_data": {},
            "steps_completed": [],
            "error_count": 0,
            "user_id": str(user_id),
            "workflow_execution_id": execution_id,
            "stage": stage,
            "stage_index": index,
            "stage_total": len(PIPELINE_STAGES),
        }

    async def _fail(
        self,
        execution_id: str,
        stage: str,
        index: int,
        user_id: uuid.UUID,
        message: str,
        *,
        terminal: bool = False,
        reason: Optional[str] = None,
    ) -> None:
        """Record a stage failure and say so on the feed."""
        await WorkflowEngine.fail_step(execution_id, stage, message, terminal=terminal)
        await emit(
            "pipeline.stage_failed",
            f"{STAGE_LABELS.get(stage, stage)} stopped: {message}",
            severity="error",
            payload={
                "execution_id": execution_id,
                "stage": stage,
                "stage_index": index,
                "stage_total": len(PIPELINE_STAGES),
                "escalation_reason": reason,
                "terminal": terminal,
            },
            user_id=str(user_id),
        )

    @staticmethod
    def _summary(
        status: str,
        execution_id: Optional[str],
        stage_reports: List[Dict[str, Any]],
        side_effects: Dict[str, Any],
        *,
        failed_stage: Optional[str] = None,
        error: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "status": status,
            "execution_id": execution_id,
            "stages_completed": [report["stage"] for report in stage_reports],
            "stages": stage_reports,
            "stage_total": len(PIPELINE_STAGES),
            "effects": side_effects,
        }
        if failed_stage:
            summary["failed_stage"] = failed_stage
        if error:
            summary["error"] = error
        if escalation_reason:
            summary["escalation_reason"] = escalation_reason
        return summary


career_pipeline = CareerPipeline()
