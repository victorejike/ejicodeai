"""Who the agents may run for, and how to run discovery for one candidate.

Discovery used to be a single global scrape, which is why every user saw the same
list. Now that search terms come from a candidate's own profile, "run the job
scout" only means something *per user* - so the enumeration of eligible users and
the single-user discovery step both live here, shared by the Celery beat fan-out
and the operator-facing agent trigger.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import User, UserProfile
from backend.app.services.profile_gate import build_candidate_profile, describe_completion

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EligibleUser:
    """A user whose profile is complete enough for the agents to work from."""

    user_id: uuid.UUID
    fallback_name: Optional[str]
    email: Optional[str]
    completion_percent: int


async def list_agent_ready_users(
    db: AsyncSession,
    *,
    require_continuous: bool = False,
) -> List[EligibleUser]:
    """Every user the agents may run for, judged by the same gate the API uses.

    ``require_continuous`` additionally honours the user's own
    ``continuous_search_active`` switch - scheduled runs respect it, an operator
    triggering a run by hand does not need to.
    """
    rows = (
        await db.execute(
            select(UserProfile, User)
            .join(User, User.id == UserProfile.user_id)
            .where(User.is_active.is_(True))
        )
    ).all()

    eligible: List[EligibleUser] = []
    for profile, user in rows:
        if require_continuous and not profile.continuous_search_active:
            continue
        fallback_name = user.full_name or user.username
        completion = describe_completion(profile, fallback_name=fallback_name)
        if not completion["agent_ready"]:
            continue
        eligible.append(
            EligibleUser(
                user_id=profile.user_id,
                fallback_name=fallback_name,
                email=user.email,
                completion_percent=completion["percent"],
            )
        )

    logger.info("Pipeline dispatch: %d agent-ready users", len(eligible))
    return eligible


async def discover_for_user(candidate: EligibleUser, db: AsyncSession) -> Dict[str, Any]:
    """Run discovery for one candidate and store their own copy of the results.

    Scores are deliberately left untouched: matching is a separate stage, and a
    row that has not been scored yet must not look scored.
    """
    from agents.base.base_agent import AgentStatus
    from agents.job_scout.job_scout_agent import JobScoutAgent
    from backend.app.services.opportunity_store import save_scored_opportunities

    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == candidate.user_id))
    ).scalars().first()
    if not profile:
        return {"user_id": str(candidate.user_id), "status": "no_profile", "found": 0, "created": 0}

    candidate_profile = build_candidate_profile(
        profile, fallback_name=candidate.fallback_name, email=candidate.email
    )

    scout = JobScoutAgent()
    state: Dict[str, Any] = {
        "agent_name": scout.name,
        "status": AgentStatus.PENDING,
        "current_step": "init",
        "input_data": {"candidate_profile": candidate_profile},
        "output_data": {},
        "steps_completed": [],
        "error_count": 0,
        "user_id": str(candidate.user_id),
        "stage": "discovery",
    }
    result = await scout.run(state)  # type: ignore[arg-type]
    output = result.get("output_data") or {}
    opportunities = output.get("opportunities") or []

    if result.get("status") in (AgentStatus.FAILURE, AgentStatus.ESCALATED):
        return {
            "user_id": str(candidate.user_id),
            "status": str(result.get("escalation_reason") or "failed"),
            "message": result.get("error_message"),
            "found": len(opportunities),
            "created": 0,
        }

    saved = await save_scored_opportunities(candidate.user_id, opportunities, db)
    return {
        "user_id": str(candidate.user_id),
        "status": "success",
        "found": len(opportunities),
        "created": saved["created"],
        "updated": saved["updated"],
        "queries": output.get("search_queries") or [],
        "sources_used": output.get("sources_used") or [],
    }
