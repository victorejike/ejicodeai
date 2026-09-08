"""Profile completeness: the single source of truth for how ready a candidate is.

Everything the agents produce is bounded by the data the user actually gave us.
A half-empty profile yields generic matches and a generic CV, so this module both
*scores* completeness and *gates* the agent pipeline on it.

The same rules drive three surfaces, so they can never disagree:
  - the completion percentage shown on the dashboard,
  - the "here is what is still missing" checklist,
  - the 428 that stops discovery from running on an unusable profile.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.core import UserProfile


@dataclass(frozen=True)
class ProfileField:
    """One scored element of a candidate profile."""

    key: str
    label: str
    weight: int
    #: Full credit when this returns True.
    is_complete: Callable[[UserProfile], bool]
    #: Partial credit (half weight) when this returns True but is_complete does not.
    is_partial: Optional[Callable[[UserProfile], bool]] = None
    #: Agents cannot do useful work without this.
    required_for_agents: bool = False
    #: What the user should do about it, shown verbatim in the UI.
    hint: str = ""


def _has_any_link(p: UserProfile) -> bool:
    return bool(p.portfolio_url or p.github_url or p.linkedin_url)


#: Ordered so the UI checklist reads in the order a user would fill the form.
PROFILE_FIELDS: tuple[ProfileField, ...] = (
    ProfileField(
        key="full_name",
        label="Full name",
        weight=10,
        is_complete=lambda p: bool(p.full_name),
        required_for_agents=True,
        hint="Used on every CV and outreach message we generate.",
    ),
    ProfileField(
        key="title",
        label="Professional title",
        weight=15,
        is_complete=lambda p: bool(p.title),
        required_for_agents=True,
        hint="Drives which roles we search for on Google and the job boards.",
    ),
    ProfileField(
        key="skills",
        label="Skills (at least 3)",
        weight=20,
        is_complete=lambda p: bool(p.skills) and len(p.skills) >= 3,
        is_partial=lambda p: bool(p.skills),
        required_for_agents=True,
        hint="Matched against every job's requirements and your CV keywords.",
    ),
    ProfileField(
        key="experience_years",
        label="Years of experience",
        weight=10,
        is_complete=lambda p: bool(p.experience_years) and p.experience_years > 0,
        required_for_agents=True,
        hint="Filters out roles at the wrong seniority.",
    ),
    ProfileField(
        key="experience",
        label="Work history",
        weight=10,
        is_complete=lambda p: bool(p.experience),
        required_for_agents=True,
        hint="Becomes the Experience section of your ATS CV.",
    ),
    ProfileField(
        key="bio",
        label="Professional bio",
        weight=10,
        is_complete=lambda p: bool(p.bio),
        hint="Seeds your professional summary.",
    ),
    ProfileField(
        key="career_goals",
        label="Career goals",
        weight=10,
        is_complete=lambda p: bool(p.career_goals),
        hint="Worth 15% of every match score.",
    ),
    ProfileField(
        key="links",
        label="Portfolio, GitHub or LinkedIn",
        weight=10,
        is_complete=_has_any_link,
        hint="Recruiters open these first; ATS parsers index them.",
    ),
    ProfileField(
        key="location",
        label="Location or remote preference",
        weight=5,
        is_complete=lambda p: bool(p.location or p.remote_preference),
        required_for_agents=True,
        hint="Scopes the location of the jobs we bring back.",
    ),
    ProfileField(
        key="education",
        label="Education",
        weight=5,
        is_complete=lambda p: bool(p.education),
        hint="Completes the Education section of your ATS CV.",
    ),
)

#: Percentage reported for a user who has no profile row at all.
EMPTY_PROFILE_SCORE = 10


def calculate_profile_completion(profile: Optional[UserProfile]) -> int:
    """Completion percentage from 0-100, scored off PROFILE_FIELDS."""
    if not profile:
        return EMPTY_PROFILE_SCORE
    score = 0
    for field in PROFILE_FIELDS:
        if field.is_complete(profile):
            score += field.weight
        elif field.is_partial and field.is_partial(profile):
            score += field.weight // 2
    return min(score, 100)


def describe_completion(
    profile: Optional[UserProfile],
    *,
    fallback_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Full completeness picture for the dashboard and the gate.

    Returns the percentage, the concrete list of what is missing (so the UI never
    has to guess), whether a CV exists, and whether the agents may run.
    """
    settings = get_settings()
    percent = calculate_profile_completion(profile)
    has_cv = bool(profile and profile.cv_document_id)

    missing: List[Dict[str, Any]] = []
    if profile is not None:
        for field in PROFILE_FIELDS:
            if field.is_complete(profile):
                continue
            missing.append(
                {
                    "key": field.key,
                    "label": field.label,
                    "weight": field.weight,
                    "hint": field.hint,
                    "required_for_agents": field.required_for_agents,
                    "partially_complete": bool(field.is_partial and field.is_partial(profile)),
                }
            )
    else:
        missing = [
            {
                "key": f.key,
                "label": f.label,
                "weight": f.weight,
                "hint": f.hint,
                "required_for_agents": f.required_for_agents,
                "partially_complete": False,
            }
            for f in PROFILE_FIELDS
        ]

    blocking = [m for m in missing if m["required_for_agents"]]
    cv_required = settings.require_cv_for_agents
    threshold = settings.min_profile_completion_for_agents

    reasons: List[str] = []
    if cv_required and not has_cv:
        reasons.append("Upload your CV so the agents work from your real experience.")
    if blocking:
        labels = ", ".join(m["label"] for m in blocking)
        reasons.append(f"Add: {labels}.")
    if percent < threshold:
        reasons.append(f"Profile is {percent}% complete; {threshold}% is needed to run the agents.")

    display_name = (profile.full_name if profile and profile.full_name else None) or fallback_name

    return {
        "percent": percent,
        "threshold": threshold,
        "has_cv": has_cv,
        "cv_required": cv_required,
        "is_complete": not missing,
        "agent_ready": not reasons,
        "missing_fields": missing,
        "blocking_fields": blocking,
        "reasons": reasons,
        "display_name": display_name,
        "first_name": (display_name or "").strip().split(" ")[0] or None,
    }


async def get_profile_completion(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    fallback_name: Optional[str] = None,
) -> tuple[Optional[UserProfile], Dict[str, Any]]:
    """Load the profile and its completion summary in one round trip."""
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalars().first()
    return profile, describe_completion(profile, fallback_name=fallback_name)


async def require_complete_profile(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    fallback_name: Optional[str] = None,
) -> UserProfile:
    """Return the profile, or refuse the request with 428 and say exactly why.

    412/422 would read as "your request was malformed"; 428 Precondition Required
    is the honest answer here - the request is fine, the account is not ready.
    """
    profile, completion = await get_profile_completion(user_id, db, fallback_name=fallback_name)
    if not completion["agent_ready"]:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error": "profile_incomplete",
                "message": " ".join(completion["reasons"]),
                "profile_completion": completion,
            },
        )
    assert profile is not None  # agent_ready implies a profile exists
    return profile


def build_candidate_profile(
    profile: UserProfile,
    *,
    fallback_name: Optional[str] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """The canonical candidate payload handed to every agent in the pipeline.

    One shape, built in one place, so no agent has to invent a default for a
    field it did not receive. ``email`` comes from the account rather than the
    profile table, and the CV builder needs it for a reply-able contact block.
    """
    return {
        "user_id": str(profile.user_id),
        "full_name": (profile.full_name or fallback_name),
        "email": email,
        "title": profile.title,
        "bio": profile.bio,
        "skills": list(profile.skills or []),
        "technologies": list(profile.technologies or []),
        "experience_years": profile.experience_years,
        "experience": list(profile.experience or []),
        "education": list(profile.education or []),
        "projects": list(profile.projects or []),
        "certifications": list(profile.certifications or []),
        "location": profile.location,
        "preferred_locations": list(profile.preferred_locations or []),
        "remote_preference": profile.remote_preference,
        "job_types": list(profile.job_types or []),
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "salary_currency": profile.salary_currency,
        "preferred_industries": list(profile.preferred_industries or []),
        "preferred_companies": list(profile.preferred_companies or []),
        "career_goals": profile.career_goals,
        "portfolio_url": profile.portfolio_url,
        "github_url": profile.github_url,
        "linkedin_url": profile.linkedin_url,
    }
