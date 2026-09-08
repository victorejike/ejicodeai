"""Individual router - Candidate profiles, matching, applications, follow-ups, and rejection recovery."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

import os
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, resolve_user_id
from backend.app.models.core import (
    Company,
    Contact,
    CVExtraction,
    Document,
    FollowUpSchedule,
    GeneratedCV,
    Opportunity,
    OutreachHistory,
    Proposal,
    RejectionLog,
    User,
    UserProfile,
    WorkflowExecution,
)
from backend.app.security import get_current_active_user
from agents.extraction.cv_parser import parse_cv_document
from agents.cv_builder.cv_builder_agent import CVBuilderAgent
from agents.matching.matching_agent import MatchingAgent
from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent
from agents.follow_up.follow_up_agent import FollowUpAgent
from agents.rejection.rejection_recovery_agent import RejectionRecoveryAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.scrapers.adapters import ScraperRegistry, scraper_registry
from agents.supervisor.career_pipeline import PIPELINE_STAGES, STAGE_LABELS, CareerPipeline
from agents.supervisor.workflow_engine import WorkflowEngine
from agents.tools.registry import calculate_candidate_match
from backend.app.services import cv_store
from backend.app.services.event_bus import event_bus
from backend.app.services.profile_gate import (
    build_candidate_profile,
    calculate_profile_completion,
    describe_completion,
    get_profile_completion,
    require_complete_profile,
)

router = APIRouter()


# ------------------ Pydantic Schemas ------------------

class SelfMarketingRequest(BaseModel):
    opportunity_id: Optional[str] = None
    company_name: Optional[str] = None


class ContinuousSearchConfigRequest(BaseModel):
    search_frequency: Optional[str] = "daily"  # daily, weekly
    job_types: Optional[List[str]] = None  # full-time, contract, freelance
    locations: Optional[List[str]] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    industries: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    remote_preference: Optional[str] = "remote"  # remote, hybrid, onsite


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None
    location: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    remote_preference: Optional[str] = "remote"
    job_types: Optional[List[str]] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    technologies: Optional[List[str]] = None
    career_goals: Optional[str] = None
    avatar_url: Optional[str] = None


class ResumeParseRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)


class ApplyRequest(BaseModel):
    opportunity_id: str
    custom_note: Optional[str] = None
    subject: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None


class RejectionRequest(BaseModel):
    opportunity_id: str
    rejection_reason: str = Field(..., min_length=5)
    rejection_source: Optional[str] = "recipient_reply"


class CVBuildRequest(BaseModel):
    #: Tailor the CV to one stored opportunity. Omitted -> a general-purpose CV.
    opportunity_id: Optional[str] = None
    #: Let the configured AI provider phrase the summary. The wording is checked
    #: against the profile before it is used, and a deterministic summary is used
    #: when no provider is configured.
    use_ai: bool = True


class PipelineRunRequest(BaseModel):
    trigger: Optional[str] = "manual"
    #: Queue on Celery when a broker is reachable; otherwise run inline.
    background: bool = True


class ReindexRequest(BaseModel):
    scope: Optional[str] = "all"  # all, individual, enterprise


# ---------------------------------------------------------------------------
# Individual Candidate Endpoints
# ---------------------------------------------------------------------------


# ------------------ Helper Functions ------------------

# `calculate_profile_completion`, `describe_completion` and `require_complete_profile`
# all live in `backend.app.services.profile_gate` so the percentage on the
# dashboard, the missing-fields checklist and the agent gate can never disagree.


async def _get_user_id(current_user: User, db: AsyncSession) -> uuid.UUID:
    """Resolve and return UUID for current user.

    Delegates to the shared resolver so the events stream and every other
    user-scoped surface agree on who the caller is.
    """
    return await resolve_user_id(current_user, db)


# ------------------ Endpoints ------------------

@router.get("/profile")
async def get_individual_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch candidate profile and completion metrics."""
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()

    if not profile:
        # Create an empty profile shell for this user. Never pre-fill title,
        # skills, or any other identity fact with a fabricated placeholder -
        # those must come from the user's real CV or their own input.
        profile = UserProfile(
            user_id=user_id,
            full_name=current_user.full_name or current_user.username,
            remote_preference="remote",
            job_types=["full-time", "contract"],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    completion = describe_completion(
        profile, fallback_name=current_user.full_name or current_user.username
    )
    completion_pct = completion["percent"]

    # Onboarding is only complete once there is a real knowledge base to work
    # from: either an uploaded/parsed CV, or a manually entered title + skills.
    has_cv = profile.cv_document_id is not None
    has_core_facts = bool(profile.title) and bool(profile.skills) and len(profile.skills) > 0
    onboarding_complete = has_cv or has_core_facts

    return {
        "status": "success",
        "profile": {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "full_name": profile.full_name,
            "title": profile.title,
            "bio": profile.bio,
            "skills": profile.skills or [],
            "experience_years": profile.experience_years,
            "experience": profile.experience or [],
            "education": profile.education or [],
            "projects": profile.projects or [],
            "certifications": profile.certifications or [],
            "portfolio_url": profile.portfolio_url,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
            "resume_url": profile.resume_url,
            "avatar_url": getattr(profile, "avatar_url", None) or getattr(current_user, "avatar_url", None),
            "location": profile.location,
            "preferred_locations": profile.preferred_locations or [],
            "remote_preference": profile.remote_preference,
            "job_types": profile.job_types or [],
            "salary_min": profile.salary_min,
            "salary_max": profile.salary_max,
            "salary_currency": profile.salary_currency,
            "technologies": profile.technologies or [],
            "career_goals": profile.career_goals,
            "ai_candidate_summary": profile.ai_candidate_summary or {},
            "completion_percentage": completion_pct,
            "has_cv": has_cv,
            "onboarding_complete": onboarding_complete,
        },
        # The exact checklist the dashboard renders, so the UI never has to
        # reimplement (or guess at) what is still missing.
        "profile_completion": completion,
    }


@router.put("/profile")
async def update_individual_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Upsert individual profile fields."""
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()

    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    # If full_name is updated, also synchronize on User
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    # If avatar_url is updated, synchronize on User as well
    if payload.avatar_url is not None:
        await db.execute(update(User).where(User.id == user_id).values(avatar_url=payload.avatar_url))

    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)

    completion = describe_completion(
        profile, fallback_name=current_user.full_name or current_user.username
    )

    return {
        "status": "success",
        "message": "Profile updated successfully",
        "completion_percentage": completion["percent"],
        "profile_completion": completion,
    }


@router.post("/profile/avatar")
async def upload_avatar(
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Upload and set candidate profile picture."""
    if not file:
        raise HTTPException(status_code=400, detail="No image file provided")

    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        ext = ".png"

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    user_id = await _get_user_id(current_user, db)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    filename = f"{user_id}_{timestamp}{ext}"

    # uploads/avatars directory
    uploads_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads",
        "avatars",
    )
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    avatar_url = f"/uploads/avatars/{filename}"

    # Update profile & user
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = res.scalars().first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    profile.avatar_url = avatar_url
    await db.execute(update(User).where(User.id == user_id).values(avatar_url=avatar_url))
    await db.commit()

    return {
        "status": "success",
        "avatar_url": avatar_url,
        "message": "Profile picture updated successfully",
    }


@router.post("/cv/upload")
@router.post("/profile/cv-upload")
async def upload_and_parse_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Upload CV document (PDF, DOCX, TXT), ingest raw text, extract truthful intelligence,
    update candidate profile, emit real-time SSE events, and trigger initial opportunity matching."""
    filename = file.filename or "uploaded_cv"
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"
    if ext not in ("pdf", "docx", "doc", "txt", "md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Please upload a PDF, DOCX, or TXT file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) < 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty or unreadable.")

    user_id = await _get_user_id(current_user, db)

    # 1. Emit upload event
    await event_bus.publish(
        event_type="cv.uploaded",
        message=f"Received CV document '{filename}' ({len(file_bytes)} bytes)",
        payload={"filename": filename, "file_size": len(file_bytes), "file_type": ext},
        user_id=str(user_id),
    )

    # 2. Parse document intelligence strictly without fabrication
    try:
        extraction_data = parse_cv_document(file_bytes, filename, ext)
    except Exception as e:
        await event_bus.publish(
            event_type="cv.failed",
            message=f"Failed to parse '{filename}': {str(e)}",
            severity="error",
            user_id=str(user_id),
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"CV parsing error: {str(e)}")

    # 3. Store Document record
    doc_record = Document(
        user_id=user_id,
        filename=filename,
        file_type=ext,
        file_hash=extraction_data["file_hash"],
        file_size=len(file_bytes),
        raw_text=extraction_data["raw_text"],
    )
    db.add(doc_record)
    await db.flush()

    # 4. Store CVExtraction record
    extraction_record = CVExtraction(
        document_id=doc_record.id,
        user_id=user_id,
        extracted_skills=extraction_data["skills"],
        extracted_experience=extraction_data["experience"],
        extracted_education=extraction_data["education"],
        extracted_certifications=extraction_data.get("certifications", []),
        extracted_projects=extraction_data["projects"],
        contact_info=extraction_data["contact_info"],
        raw_sections=extraction_data["raw_sections"],
        confidence_score=extraction_data["confidence_score"],
        extraction_metadata={
            "filename": filename,
            "skills_count": len(extraction_data["skills"]),
            "experience_years": extraction_data["experience_years"],
        },
        status="completed",
    )
    db.add(extraction_record)

    # 5. Update Candidate UserProfile
    profile_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await db.execute(profile_stmt)).scalars().first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()

    # Merge skills
    extracted_skill_names = extraction_data["skills_list"]
    existing_skills = list(profile.skills or [])
    for skill_name in extracted_skill_names:
        if skill_name not in existing_skills:
            existing_skills.append(skill_name)
    profile.skills = existing_skills
    profile.technologies = extracted_skill_names

    if extraction_data.get("full_name"):
        profile.full_name = extraction_data["full_name"]
        user_record = await db.get(User, user_id)
        if user_record:
            user_record.full_name = extraction_data["full_name"]

    if extraction_data.get("title"):
        profile.title = extraction_data["title"]
    if extraction_data.get("bio"):
        profile.bio = extraction_data["bio"]
    if extraction_data.get("career_goals"):
        profile.career_goals = extraction_data["career_goals"]
    if extraction_data.get("experience_years"):
        profile.experience_years = max(profile.experience_years or 0.0, extraction_data["experience_years"])
    if extraction_data.get("experience"):
        profile.experience = extraction_data["experience"]
    if extraction_data.get("education"):
        profile.education = extraction_data["education"]
    if extraction_data.get("projects"):
        profile.projects = extraction_data["projects"]
    if extraction_data.get("certifications"):
        profile.certifications = extraction_data["certifications"]

    contact = extraction_data.get("contact_info", {})
    if contact.get("github"):
        profile.github_url = contact["github"]
    if contact.get("linkedin"):
        profile.linkedin_url = contact["linkedin"]
    if contact.get("portfolio"):
        profile.portfolio_url = contact["portfolio"]
    if contact.get("location"):
        profile.location = contact["location"]
        if not profile.preferred_locations:
            profile.preferred_locations = [contact["location"]]

    profile.cv_document_id = doc_record.id
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)

    completion = describe_completion(
        profile, fallback_name=profile.full_name or current_user.full_name or current_user.username
    )

    # 6. Emit extraction success event
    await event_bus.publish(
        event_type="cv.extracted",
        message=f"CV intelligence extracted: {len(extracted_skill_names)} skills, {len(extraction_data['experience'])} roles (confidence {int(extraction_data['confidence_score']*100)}%)",
        severity="success",
        payload={
            "skills": extracted_skill_names[:10],
            "experience_years": extraction_data["experience_years"],
            "title": profile.title,
            "confidence_score": extraction_data["confidence_score"],
        },
        user_id=str(user_id),
    )

    # 7. Live discovery matching, driven by what the CV actually says about this
    #    person - their title first, then their strongest skills. No default query.
    discovered_count = 0
    candidate_payload = build_candidate_profile(
        profile, fallback_name=profile.full_name or current_user.full_name or current_user.username
    )
    search_queries = JobScoutAgent.build_queries(candidate_payload, max_queries=4)
    try:
        live_opportunities = (
            await scraper_registry.search_opportunities(queries=search_queries)
            if search_queries
            else []
        )
        for live_opp in live_opportunities[:15]:
            src_url = live_opp.get("source_url")
            if not src_url:
                continue
            # This user's own copy of the posting - another user may hold theirs.
            existing_opp = (
                await db.execute(
                    select(Opportunity).where(
                        Opportunity.user_id == user_id, Opportunity.source_url == src_url
                    )
                )
            ).scalars().first()
            if not existing_opp:
                match_intel = calculate_candidate_match(
                    {"skills": profile.skills, "experience_years": profile.experience_years, "title": profile.title},
                    live_opp
                )
                new_opp = Opportunity(
                    user_id=user_id,
                    title=live_opp.get("title") or "Untitled posting",
                    type=live_opp.get("type", "full-time"),
                    source_platform=live_opp.get("source", "web"),
                    source_url=src_url,
                    raw_description=live_opp.get("description"),
                    location=live_opp.get("location"),
                    location_type=live_opp.get("location_type", "remote"),
                    salary_min=live_opp.get("salary_min"),
                    salary_max=live_opp.get("salary_max"),
                    salary_currency=live_opp.get("salary_currency", "USD"),
                    tech_required=live_opp.get("tech_required", []),
                    score=match_intel["score"],
                    score_breakdown=match_intel,
                    source_reliability_score=ScraperRegistry.source_reliability(live_opp.get("source")),
                    freshness_status="OPEN",
                )
                db.add(new_opp)
                discovered_count += 1

        if discovered_count > 0:
            await db.commit()
            await event_bus.publish(
                event_type="opportunities.matched",
                message=f"Discovered and matched {discovered_count} live opportunities for your profile",
                severity="success",
                payload={"count": discovered_count, "queries": search_queries},
                user_id=str(user_id),
            )
    except Exception as exc:  # discovery is best-effort; the upload itself succeeded
        await event_bus.publish(
            event_type="opportunities.discovery_failed",
            message=f"CV saved, but live discovery could not complete: {exc}",
            severity="warning",
            user_id=str(user_id),
        )

    return {
        "status": "success",
        "document_id": str(doc_record.id),
        "filename": filename,
        "confidence_score": extraction_data["confidence_score"],
        "extracted_skills": extracted_skill_names,
        "experience_years": extraction_data["experience_years"],
        "profile": {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "full_name": profile.full_name,
            "title": profile.title,
            "bio": profile.bio,
            "career_goals": profile.career_goals,
            "skills": profile.skills or [],
            "technologies": profile.technologies or [],
            "experience_years": profile.experience_years,
            "experience": profile.experience or [],
            "education": profile.education or [],
            "projects": profile.projects or [],
            "certifications": profile.certifications or [],
            "location": profile.location,
            "preferred_locations": profile.preferred_locations or [],
            "remote_preference": profile.remote_preference,
            "portfolio_url": profile.portfolio_url,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
            "completion_percentage": completion["percent"],
            "has_cv": True,
            "onboarding_complete": True,
        },
        "profile_completion": completion,
        "discovered_opportunities_count": discovered_count,
    }


@router.post("/profile/resume-parse")
async def parse_resume(
    payload: ResumeParseRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Extract skills, roles, and experience from resume text."""
    analyzer = ProfileAnalyzerAgent()
    profile_data = {
        "full_name": current_user.full_name or current_user.username,
        "resume_text": payload.resume_text,
    }
    analysis = await analyzer.execute(profile_data)

    extracted_skills = analysis.get("extracted_skills", [])
    # No stand-in title or years: if the CV does not state them, we say so and let
    # the user fill them in rather than putting words in their mouth.
    suggested_titles = analysis.get("suggested_titles") or []
    experience_years = analysis.get("experience_years")

    # Update profile with extracted data if available
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()

    # Also run high-fidelity CV extraction on pasted text
    try:
        cv_intel = parse_cv_document(payload.resume_text.encode("utf-8"), "pasted_resume.txt", "txt")
        if cv_intel.get("full_name") and not profile.full_name:
            profile.full_name = cv_intel["full_name"]
            user_rec = await db.get(User, user_id)
            if user_rec:
                user_rec.full_name = cv_intel["full_name"]
        if cv_intel.get("title") and not profile.title:
            profile.title = cv_intel["title"]
        if cv_intel.get("bio") and not profile.bio:
            profile.bio = cv_intel["bio"]
        if cv_intel.get("career_goals") and not profile.career_goals:
            profile.career_goals = cv_intel["career_goals"]
        if cv_intel.get("skills_list"):
            curr_skills = list(profile.skills or [])
            for s in cv_intel["skills_list"]:
                if s not in curr_skills:
                    curr_skills.append(s)
            profile.skills = curr_skills
            profile.technologies = cv_intel["skills_list"]
        if cv_intel.get("experience_years"):
            profile.experience_years = max(profile.experience_years or 0.0, cv_intel["experience_years"])
        if cv_intel.get("experience") and not profile.experience:
            profile.experience = cv_intel["experience"]
        if cv_intel.get("education") and not profile.education:
            profile.education = cv_intel["education"]
        if cv_intel.get("certifications") and not profile.certifications:
            profile.certifications = cv_intel["certifications"]
        if cv_intel.get("projects") and not profile.projects:
            profile.projects = cv_intel["projects"]
        c_info = cv_intel.get("contact_info", {})
        if c_info.get("github") and not profile.github_url:
            profile.github_url = c_info["github"]
        if c_info.get("linkedin") and not profile.linkedin_url:
            profile.linkedin_url = c_info["linkedin"]
        if c_info.get("portfolio") and not profile.portfolio_url:
            profile.portfolio_url = c_info["portfolio"]
        if c_info.get("location") and not profile.location:
            profile.location = c_info["location"]
            if not profile.preferred_locations:
                profile.preferred_locations = [c_info["location"]]
    except Exception as exc:
        logger.warning("Secondary CV parser on pasted text bypassed: %s", exc)

    if extracted_skills:
        current_skills = list(profile.skills or [])
        for s in extracted_skills:
            if s not in current_skills:
                current_skills.append(s)
        profile.skills = current_skills
    if suggested_titles and not profile.title:
        profile.title = suggested_titles[0]
    if experience_years and not profile.experience_years:
        profile.experience_years = experience_years
    profile.ai_candidate_summary = analysis
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)

    completion = describe_completion(
        profile, fallback_name=profile.full_name or current_user.full_name or current_user.username
    )

    return {
        "status": "success",
        "analysis": analysis,
        "extracted_skills": profile.skills or [],
        "suggested_titles": suggested_titles,
        "experience_years": profile.experience_years,
        "profile": {
            "full_name": profile.full_name,
            "title": profile.title,
            "bio": profile.bio,
            "career_goals": profile.career_goals,
            "skills": profile.skills or [],
            "experience_years": profile.experience_years,
            "experience": profile.experience or [],
            "education": profile.education or [],
            "projects": profile.projects or [],
            "certifications": profile.certifications or [],
            "location": profile.location,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
            "portfolio_url": profile.portfolio_url,
            "completion_percentage": completion["percent"],
            "has_cv": bool(profile.cv_document_id),
            "onboarding_complete": True,
        },
        "profile_completion": completion,
        "missing_fields": analysis.get("missing_fields", []),
    }


@router.post("/search")
async def search_and_match_opportunities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Scrape live sources with the user's own search terms, then score every result.

    Gated on a complete profile: discovery driven by half a profile returns the
    same generic list for everybody, which is the opposite of a match.
    """
    user_id = await _get_user_id(current_user, db)
    fallback_name = current_user.full_name or current_user.username
    profile = await require_complete_profile(user_id, db, fallback_name=fallback_name)

    candidate_profile = build_candidate_profile(profile, fallback_name=fallback_name)

    # 1. Discover against the live sources using this candidate's terms.
    scout = JobScoutAgent()
    scout_state: Dict[str, Any] = {
        "agent_name": scout.name,
        "status": "pending",
        "current_step": "init",
        "input_data": {"candidate_profile": candidate_profile},
        "output_data": {},
        "steps_completed": [],
        "error_count": 0,
        "user_id": str(user_id),
    }
    scout_result = await scout.process(scout_state)  # type: ignore[arg-type]
    scout_out = scout_result.get("output_data", {})
    live_opportunities: List[Dict[str, Any]] = scout_out.get("opportunities", [])
    search_queries: List[str] = scout_out.get("search_queries", [])

    # 2. Persist this user's own copy of anything new.
    discovered_count = 0
    for live_opp in live_opportunities:
        src_url = live_opp.get("source_url")
        if not src_url:
            continue
        exists = (
            await db.execute(
                select(Opportunity.id).where(
                    Opportunity.user_id == user_id, Opportunity.source_url == src_url
                )
            )
        ).scalars().first()
        if exists:
            continue
        db.add(
            Opportunity(
                user_id=user_id,
                title=live_opp.get("title") or "Untitled posting",
                type=live_opp.get("type") or "full-time",
                source_platform=live_opp.get("source") or "web",
                source_url=src_url,
                raw_description=live_opp.get("description"),
                location=live_opp.get("location"),
                location_type=live_opp.get("location_type") or "remote",
                salary_min=live_opp.get("salary_min"),
                salary_max=live_opp.get("salary_max"),
                salary_currency=live_opp.get("salary_currency") or "USD",
                tech_required=live_opp.get("tech_required") or [],
                source_reliability_score=ScraperRegistry.source_reliability(live_opp.get("source")),
                freshness_status="OPEN",
            )
        )
        discovered_count += 1
    if discovered_count:
        await db.commit()

    # 3. Score every opportunity this user owns against their profile.
    matching_agent = MatchingAgent()
    opportunities = (
        await db.execute(
            select(Opportunity)
            .where(Opportunity.user_id == user_id)
            .order_by(desc(Opportunity.created_at))
            .limit(100)
        )
    ).scalars().all()

    matches_list = []
    for opp in opportunities:
        scored = matching_agent.score_opportunity(
            {
                "title": opp.title,
                "description": opp.raw_description or "",
                "location": opp.location,
                "location_type": opp.location_type or "remote",
                "salary_min": opp.salary_min,
                "salary_max": opp.salary_max,
                "tech_required": opp.tech_required or [],
                "company_name": None,
            },
            candidate_profile,
        )
        opp.score = scored["match_score"]
        opp.score_breakdown = scored["score_breakdown"]
        matches_list.append({
            "id": str(opp.id),
            "title": opp.title,
            "source_platform": opp.source_platform,
            "source_url": opp.source_url,
            "score": scored["match_score"],
            "breakdown": scored["score_breakdown"],
            "explanation": scored["match_explanation"],
            "matched_skills": scored["matched_skills"],
            "missing_skills": scored["missing_skills"],
        })

    await db.commit()

    await event_bus.publish(
        event_type="search.completed",
        message=(
            f"Searched {len(scout_out.get('sources_used') or [])} sources for "
            f"{len(search_queries)} role variants: {discovered_count} new, {len(matches_list)} scored"
        ),
        severity="success",
        payload={
            "queries": search_queries,
            "discovered": discovered_count,
            "scored": len(matches_list),
        },
        user_id=str(user_id),
    )

    return {
        "status": "success",
        "search_queries": search_queries,
        "sources_used": scout_out.get("sources_used", []),
        "opportunities_discovered": discovered_count,
        "opportunities_evaluated": len(matches_list),
        "top_matches": sorted(matches_list, key=lambda x: x["score"], reverse=True)[:10],
    }


@router.get("/matches")
async def get_matched_opportunities(
    min_score: int = 0,
    remote_only: bool = False,
    pipeline_type: Optional[str] = None,  # "employment" or "freelance"
    limit: int = 25,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """This user's ranked opportunities with their real 6-factor breakdowns.

    Trust and verification fields are returned as ``null`` when nothing has
    actually verified the posting. The UI renders "-" / "Unverified" for those -
    an unchecked job must never look checked.
    """
    user_id = await _get_user_id(current_user, db)

    query = select(
        Opportunity,
        Company.name.label("company_name"),
        Company.industry.label("company_industry"),
        Company.domain.label("company_domain"),
    )\
        .outerjoin(Company, Opportunity.company_id == Company.id)\
        .where(Opportunity.user_id == user_id)\
        .where(Opportunity.score >= min_score)

    if remote_only:
        query = query.where(Opportunity.location_type == "remote")

    if pipeline_type:
        query = query.where((Opportunity.pipeline_type == pipeline_type) | (Opportunity.type == pipeline_type))

    query = query.order_by(desc(Opportunity.score)).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    matches = []
    for opp, company_name, company_industry, company_domain in rows:
        contacts_list = []
        if opp.company_id:
            c_res = await db.execute(
                select(Contact).where(Contact.company_id == opp.company_id).limit(2)
            )
            for c in c_res.scalars().all():
                contacts_list.append({
                    "id": str(c.id),
                    "name": f"{c.first_name or ''} {c.last_name or ''}".strip() or "Hiring Lead",
                    "email": c.email,
                    "title": c.title or "Engineering Leader",
                })

        matches.append({
            "id": str(opp.id),
            "title": opp.title,
            "company_id": str(opp.company_id) if opp.company_id else None,
            "company_name": company_name or "Verified Organization",
            "company_industry": company_industry or "Technology",
            "company_domain": company_domain,
            "source_platform": opp.source_platform or "Verified Source",
            "source_url": opp.source_url,
            "all_sources": opp.all_sources or [],
            "pipeline_type": opp.pipeline_type or "employment",
            "location_type": opp.location_type or "Remote",
            "location": opp.location or "Worldwide",
            "salary_min": opp.salary_min,
            "salary_max": opp.salary_max,
            "salary_currency": opp.salary_currency or "USD",
            "score": opp.score,
            "score_breakdown": opp.score_breakdown or {},
            "quality_score": opp.quality_score,
            "source_reliability_score": opp.source_reliability_score,
            "safety_status": opp.safety_status or "SAFE",
            "verification_confidence": opp.verification_confidence or 95,
            "freshness_status": opp.freshness_status or "OPEN",
            "status": opp.status,
            "posted_at": opp.posted_at.isoformat() if opp.posted_at else None,
            "description": opp.raw_description or "",
            "tech_required": opp.tech_required or [],
            "contacts": contacts_list,
        })

    return {
        "status": "success",
        "count": len(matches),
        "matches": matches,
    }


@router.post("/opportunities/{opportunity_id}/draft-outreach")
async def draft_opportunity_outreach(
    opportunity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Draft a highly personalized, ATS-aligned application letter and cold outreach pitch

    based on the candidate's actual profile & CV matched against this opportunity and company.
    """
    try:
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    user_id = await _get_user_id(current_user, db)

    # 1. Fetch opportunity
    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
    opp = opp_result.scalars().first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 2. Fetch candidate profile
    p_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = p_res.scalars().first()
    fallback_name = current_user.full_name or current_user.username
    candidate_profile = build_candidate_profile(profile, fallback_name=fallback_name, email=current_user.email)

    # 3. Fetch company & contacts
    company_data = {}
    contacts_list = []
    if opp.company_id:
        company = await db.get(Company, opp.company_id)
        if company:
            company_data = {
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
                "tech_stack": company.tech_stack or [],
            }
            c_res = await db.execute(select(Contact).where(Contact.company_id == opp.company_id).limit(3))
            for c in c_res.scalars().all():
                contacts_list.append({
                    "id": str(c.id),
                    "name": f"{c.first_name or ''} {c.last_name or ''}".strip() or "Hiring Team",
                    "email": c.email,
                    "title": c.title or "Engineering Leader",
                })

    # If no contact discovered yet, scrape or extract from company website/domain
    if not contacts_list and company_data.get("domain"):
        try:
            contact_agent = ContactDiscoveryAgent()
            found_emails = await contact_agent._find_emails_on_website(company_data["domain"])
            if found_emails:
                for email in found_emails[:2]:
                    contacts_list.append({
                        "id": f"scraped-{uuid.uuid4()}",
                        "name": f"Hiring Lead at {company_data.get('name') or opp.title}",
                        "email": email,
                        "title": "Recruiting / Engineering Contact",
                    })
        except Exception as e:
            logger.warning("Contact discovery scrape failed: %s", e)

    company_display_name = company_data.get("name") or "Hiring Team"
    primary_contact = contacts_list[0] if contacts_list else {
        "name": f"Hiring Team at {company_display_name}",
        "email": None,
        "title": "Hiring Manager",
    }

    # 4. Generate tailored self-marketing materials using ProposalGenerationAgent
    proposal_agent = ProposalGenerationAgent()
    opportunity_data = {
        "id": str(opp.id),
        "title": opp.title,
        "company_name": company_display_name,
        "description": opp.raw_description or "",
        "tech_required": opp.tech_required or [],
        "location": opp.location,
        "source_url": opp.source_url,
    }

    marketing = await proposal_agent.generate_self_marketing_materials(
        candidate_profile=candidate_profile,
        opportunity=opportunity_data,
        company=company_data,
    )

    return {
        "status": "success",
        "opportunity_id": str(opp.id),
        "title": opp.title,
        "company_name": company_display_name,
        "company_domain": company_data.get("domain"),
        "source_platform": opp.source_platform or "Verified Source",
        "source_url": opp.source_url,
        "description": opp.raw_description or "",
        "tech_required": opp.tech_required or [],
        "salary_min": opp.salary_min,
        "salary_max": opp.salary_max,
        "salary_currency": opp.salary_currency or "USD",
        "location": opp.location or "Worldwide",
        "contact": primary_contact,
        "all_contacts": contacts_list,
        "subject": f"Application for {opp.title} — {candidate_profile.get('full_name')}",
        "cover_letter": marketing.get("cover_letter"),
        "cold_pitch": marketing.get("value_proposition"),
        "freelance_proposal": marketing.get("freelance_proposal"),
        "matched_requirements": marketing.get("matched_requirements") or [],
        "follow_up_cadence": marketing.get("follow_up_cadence") or {},
        "candidate_skills": candidate_profile.get("skills") or [],
    }


@router.post("/apply")
async def apply_to_opportunity(
    payload: ApplyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Submit application or outreach with scheduled 3/7/14 day follow-up sequence."""
    try:
        opp_uuid = uuid.UUID(payload.opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
    opp = opp_result.scalars().first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Outreach goes out in the user's name, so it must be backed by a real,
    # finished profile.
    _uid = await _get_user_id(current_user, db)
    await require_complete_profile(
        _uid, db, fallback_name=current_user.full_name or current_user.username
    )

    user_id = await _get_user_id(current_user, db)

    # The employer, as actually recorded against the opportunity.
    company = None
    if opp.company_id:
        company = (
            await db.execute(select(Company).where(Company.id == opp.company_id))
        ).scalars().first()
    company_name = company.name if company and company.name else None
    company_domain = company.domain if company and company.domain else None

    # Locate an existing contact for this employer.
    contact = None
    if opp.company_id:
        contact_res = await db.execute(
            select(Contact)
            .where(Contact.company_id == opp.company_id, Contact.email.isnot(None))
            .limit(1)
        )
        contact = contact_res.scalars().first()

    # No stored contact: try to discover a real one. We never invent a recipient -
    # a fabricated "Hiring Manager <hiring@employer.com>" is an address that either
    # bounces or reaches a stranger.
    discovery_attempted = False
    if not contact and company_domain:
        discovery_attempted = True
        discovery = ContactDiscoveryAgent()
        discovery_state: Dict[str, Any] = {
            "agent_name": discovery.name,
            "status": "pending",
            "current_step": "init",
            "input_data": {
                "company_id": str(opp.company_id) if opp.company_id else None,
                "domain": company_domain,
                "company_name": company_name,
            },
            "output_data": {},
            "steps_completed": [],
            "error_count": 0,
            "user_id": str(user_id),
        }
        discovery_result = await discovery.process(discovery_state)  # type: ignore[arg-type]
        found = [
            c for c in discovery_result.get("output_data", {}).get("contacts", [])
            if c.get("email")
        ]
        found.sort(key=lambda c: (c.get("confidence") == "verified", c.get("is_decision_maker")), reverse=True)
        if found:
            best = found[0]
            name_parts = (best.get("name") or "").split(" ", 1)
            contact = Contact(
                company_id=opp.company_id,
                user_id=user_id,
                first_name=best.get("first_name") or (name_parts[0] or None),
                last_name=best.get("last_name") or (name_parts[1] if len(name_parts) > 1 else None),
                full_name=best.get("name"),
                email=best["email"],
                title=best.get("title"),
                linkedin_url=best.get("linkedin_url"),
                email_confidence=best.get("confidence") or "unverified",
                is_decision_maker=bool(best.get("is_decision_maker")),
                source=best.get("source"),
            )
            db.add(contact)
            await db.commit()
            await db.refresh(contact)

    if not contact:
        reasons = []
        if not opp.company_id:
            reasons.append("this posting is not linked to a company record yet")
        elif not company_domain:
            reasons.append(f"we have no website for {company_name or 'this employer'}")
        elif discovery_attempted:
            reasons.append("contact discovery found no verifiable email address")
        return {
            "status": "no_contact_found",
            "message": (
                "No verified contact could be found, so nothing was sent. "
                + ("Reason: " + "; ".join(reasons) + ". " if reasons else "")
                + "Apply on the posting directly, or add a contact for this employer."
            ),
            "opportunity_id": str(opp.id),
            "source_url": opp.source_url,
            "outreach_id": None,
            "follow_up_schedules": [],
        }

    # Create OutreachHistory
    outreach = OutreachHistory(
        contact_id=contact.id,
        opportunity_id=opp.id,
        user_id=user_id,
        delivery_status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    db.add(outreach)
    opp.status = "applied"
    await db.commit()
    await db.refresh(outreach)

    # Schedule Day 3, Day 7, Day 14 follow-ups via FollowUpAgent
    follow_up_agent = FollowUpAgent()
    schedule_result = await follow_up_agent.execute({
        "outreach_id": str(outreach.id),
        "contact_id": str(contact.id),
        "candidate_name": current_user.full_name or current_user.username,
        "company_name": company_name,
        "opportunity_title": opp.title,
    })

    created_schedules = []
    now = datetime.now(timezone.utc)
    for step in schedule_result.get("schedules", []):
        delay_days = step.get("delay_days", 3)
        sched = FollowUpSchedule(
            outreach_id=outreach.id,
            contact_id=contact.id,
            sequence_step=step.get("sequence_step", 1),
            delay_days=delay_days,
            scheduled_for=now + timedelta(days=delay_days),
            status="scheduled",
            subject=step.get("subject", f"Following up on {opp.title}"),
            body_draft=step.get("body", ""),
        )
        db.add(sched)
        created_schedules.append({
            "step": step.get("sequence_step"),
            "delay_days": delay_days,
            "scheduled_for": (now + timedelta(days=delay_days)).isoformat(),
            "subject": sched.subject,
        })

    await db.commit()

    return {
        "status": "success",
        "message": "Application outreach recorded and follow-up sequence scheduled",
        "outreach_id": str(outreach.id),
        "follow_up_schedules": created_schedules,
    }


@router.post("/rejections")
async def record_rejection_and_recover(
    payload: RejectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Execute Rejection Recovery: analyzes rejection feedback and discovers lookalike opportunities."""
    try:
        opp_uuid = uuid.UUID(payload.opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opp_result = await db.execute(
        select(Opportunity, Company.name.label("company_name"), Company.industry.label("company_industry"))
        .outerjoin(Company, Opportunity.company_id == Company.id)
        .where(Opportunity.id == opp_uuid)
    )
    row = opp_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp, real_company_name, real_company_industry = row

    opp.status = "rejected"

    # Run RejectionRecoveryAgent using the opportunity's real, linked company -
    # never a fabricated placeholder name or industry.
    recovery_agent = RejectionRecoveryAgent()
    recovery_result = await recovery_agent.execute({
        "rejection_reason": payload.rejection_reason,
        "opportunity_title": opp.title,
        "company_name": real_company_name or "Unknown Company",
        "industry": real_company_industry or "Unknown",
        "tech_stack": opp.tech_required or [],
    })

    user_id = await _get_user_id(current_user, db)

    # Save RejectionLog
    rejection_log = RejectionLog(
        user_id=user_id,
        opportunity_id=opp.id,
        rejection_source=payload.rejection_source,
        rejection_reason=payload.rejection_reason,
        feedback_analysis=recovery_result.get("feedback_analysis", {}),
        similar_search_triggered=True,
        similar_organizations_found=recovery_result.get("lookalike_companies", []),
        alternate_contacts_found=recovery_result.get("alternate_departments", []),
    )
    db.add(rejection_log)
    await db.commit()
    await db.refresh(rejection_log)

    return {
        "status": "success",
        "message": "Rejection processed: recovery workflows and lookalike discovery activated",
        "rejection_log_id": str(rejection_log.id),
        "feedback_analysis": recovery_result.get("feedback_analysis"),
        "lookalike_companies": recovery_result.get("lookalike_companies"),
        "recovery_strategy": recovery_result.get("recovery_action_plan"),
    }


@router.get("/rejections")
async def get_rejection_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve all rejections and active recovery action plans."""
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(RejectionLog)
        .where(RejectionLog.user_id == user_id)
        .order_by(desc(RejectionLog.created_at))
    )
    logs = result.scalars().all()

    items = []
    for log in logs:
        items.append({
            "id": str(log.id),
            "opportunity_id": str(log.opportunity_id) if log.opportunity_id else None,
            "rejection_reason": log.rejection_reason,
            "rejection_source": log.rejection_source,
            "feedback_analysis": log.feedback_analysis or {},
            "lookalike_companies": log.similar_organizations_found or [],
            "alternate_departments": log.alternate_contacts_found or [],
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "status": "success",
        "count": len(items),
        "rejections": items,
    }


@router.get("/dashboard-stats")
async def get_individual_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve comprehensive KPI metrics for the individual career dashboard."""
    user_id = await _get_user_id(current_user, db)
    fallback_name = current_user.full_name or current_user.username

    # Profile completion - same rules as the gate, so the dashboard's number and
    # the agents' readiness check can never disagree.
    profile, completion = await get_profile_completion(user_id, db, fallback_name=fallback_name)
    completion_pct = completion["percent"]

    # Opportunities discovered for this user
    discovered_count = (
        await db.scalar(
            select(func.count()).select_from(Opportunity).where(Opportunity.user_id == user_id)
        )
    ) or 0

    # Opportunity matches count (scoped to this user's own discovered opportunities)
    matches_count = (
        await db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.user_id == user_id, Opportunity.score >= 60)
        )
    ) or 0

    # Applications / Outreach sent by this user
    outreach_count = (
        await db.scalar(
            select(func.count())
            .select_from(OutreachHistory)
            .where(OutreachHistory.user_id == user_id)
        )
    ) or 0

    # Outreach that was actually dispatched (contacted) vs. drafted
    contacted_count = (
        await db.scalar(
            select(func.count())
            .select_from(OutreachHistory)
            .where(OutreachHistory.user_id == user_id, OutreachHistory.sent_at.isnot(None))
        )
    ) or 0

    # Real inbound replies (never fabricated)
    responded_count = (
        await db.scalar(
            select(func.count())
            .select_from(OutreachHistory)
            .where(OutreachHistory.user_id == user_id, OutreachHistory.replied_at.isnot(None))
        )
    ) or 0

    # Interviews / offers are only tracked once an interview-scheduling or offer-tracking
    # feature records them explicitly. No such signal exists yet, so these are honestly 0
    # rather than fabricated placeholder numbers.
    interviews_count = 0
    offers_count = 0

    # Scheduled follow-ups belonging to this user's own outreach
    followups_count = (
        await db.scalar(
            select(func.count())
            .select_from(FollowUpSchedule)
            .join(OutreachHistory, FollowUpSchedule.outreach_id == OutreachHistory.id)
            .where(
                FollowUpSchedule.status == "scheduled",
                OutreachHistory.user_id == user_id,
            )
        )
    ) or 0

    # Rejection recovery logs
    rejections_count = (
        await db.scalar(
            select(func.count())
            .select_from(RejectionLog)
            .where(RejectionLog.user_id == user_id)
        )
    ) or 0

    # Average match score across this user's own scored opportunities.
    # None (not a fabricated number) until at least one opportunity has been scored.
    avg_score = (
        await db.scalar(
            select(func.avg(Opportunity.score)).where(
                Opportunity.user_id == user_id, Opportunity.score > 0
            )
        )
    )
    average_match_score = round(float(avg_score), 1) if avg_score is not None else None

    return {
        "status": "success",
        "data": {
            "profile_completion_percentage": completion_pct,
            # Full checklist so the dashboard can greet the user by name and show
            # exactly what is still missing without a second request.
            "profile_completion": completion,
            "agent_ready": completion["agent_ready"],
            "active_matches": matches_count,
            "applications_sent": outreach_count,
            "scheduled_follow_ups": followups_count,
            "rejections_recovered": rejections_count,
            "average_match_score": average_match_score,
            "candidate_title": profile.title if profile and profile.title else None,
            "candidate_name": completion["display_name"],
            "candidate_first_name": completion["first_name"],
            "hiring_pipeline": {
                "discovered": discovered_count,
                "matched": matches_count,
                "applied": outreach_count,
                "contacted": contacted_count,
                "responded": responded_count,
                "interviews": interviews_count,
                "offers": offers_count,
            },
        },
    }


@router.post("/marketing/materials")
async def generate_marketing_materials(
    payload: SelfMarketingRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """AI Self-Marketing Engine: Generate truthful bio, resume highlights, proposals, and value propositions without fabrication."""
    user_id = await _get_user_id(current_user, db)
    p_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = p_res.scalars().first()

    # Marketing materials must be built from the user's real, verified profile -
    # never a fabricated generic developer identity.
    if not profile or not profile.title or not profile.skills:
        raise HTTPException(
            status_code=400,
            detail="Complete your profile (title and skills) or upload a CV before generating marketing materials.",
        )

    candidate_profile = {
        "full_name": (profile.full_name if profile.full_name else None) or current_user.full_name or current_user.username,
        "title": profile.title,
        "skills": profile.skills,
        "experience_years": profile.experience_years or 0.0,
        "projects": profile.projects or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "portfolio_url": profile.portfolio_url,
        "github_url": profile.github_url,
        "linkedin_url": profile.linkedin_url,
    }

    opportunity_data = None
    company_data = None
    if payload.opportunity_id:
        try:
            opp_uuid = uuid.UUID(payload.opportunity_id)
            opp_res = await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
            opp = opp_res.scalars().first()
            if opp:
                opportunity_data = {"title": opp.title, "company_name": payload.company_name}
        except ValueError:
            pass

    if payload.company_name:
        company_data = {"name": payload.company_name}

    proposal_agent = ProposalGenerationAgent()
    materials = await proposal_agent.generate_self_marketing_materials(
        candidate_profile=candidate_profile,
        opportunity=opportunity_data,
        company=company_data,
    )

    # Cache on UserProfile
    if profile:
        profile.marketing_materials = materials
        await db.commit()

    return {
        "status": "success",
        "marketing_materials": materials,
    }


@router.get("/companies-to-approach")
async def get_companies_to_approach(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Company-First Discovery: Proactively identify companies that need the candidate's skills even without a job posting."""
    user_id = await _get_user_id(current_user, db)
    p_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = p_res.scalars().first()

    # Never fabricate skills to scout companies against - require the user's real skills.
    if not profile or not profile.skills:
        return {
            "status": "profile_incomplete",
            "message": "Upload your CV or add your skills on your profile before discovering companies to approach.",
            "pipeline": "Companies You Should Approach",
            "count": 0,
            "companies": [],
        }

    candidate_profile = build_candidate_profile(
        profile, fallback_name=current_user.full_name or current_user.username
    )

    company_scout = CompanyScoutAgent()
    state = {
        "status": "running",
        "input_data": {"candidate_profile": candidate_profile, "skills": profile.skills},
        "steps_completed": [],
        "user_id": str(user_id),
    }
    result_state = await company_scout.process(state)
    out = result_state.get("output_data", {})
    companies_to_approach = out.get("companies_to_approach", [])

    return {
        "status": "success",
        "pipeline": "Companies You Should Approach",
        "count": len(companies_to_approach),
        "companies": companies_to_approach,
    }


@router.get("/search-config")
async def get_search_configuration(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve continuous search pipeline configuration for candidate."""
    user_id = await _get_user_id(current_user, db)
    p_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = p_res.scalars().first()

    return {
        "status": "success",
        "config": {
            "search_frequency": profile.search_frequency if profile else "daily",
            "continuous_search_active": profile.continuous_search_active if profile else True,
            # Preferences the user has not set stay empty so the UI prompts for
            # them rather than pretending a choice was made.
            "job_types": (profile.job_types if profile else None) or [],
            "locations": (profile.preferred_locations if profile else None) or [],
            "salary_min": profile.salary_min if profile else None,
            "salary_max": profile.salary_max if profile else None,
            "salary_currency": (profile.salary_currency if profile else None),
            "industries": (profile.preferred_industries if profile else None) or [],
            "skills": (profile.skills if profile else None) or [],
            "companies": (profile.preferred_companies if profile else None) or [],
            "remote_preference": profile.remote_preference if profile else None,
        },
    }


@router.put("/search-config")
async def update_search_configuration(
    payload: ContinuousSearchConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update continuous career search pipeline parameters."""
    user_id = await _get_user_id(current_user, db)
    p_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = p_res.scalars().first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    if payload.search_frequency is not None:
        profile.search_frequency = payload.search_frequency
    if payload.job_types is not None:
        profile.job_types = payload.job_types
    if payload.locations is not None:
        profile.preferred_locations = payload.locations
    if payload.salary_min is not None:
        profile.salary_min = payload.salary_min
    if payload.salary_max is not None:
        profile.salary_max = payload.salary_max
    if payload.industries is not None:
        profile.preferred_industries = payload.industries
    if payload.skills is not None:
        profile.skills = payload.skills
    if payload.companies is not None:
        profile.preferred_companies = payload.companies
    if payload.remote_preference is not None:
        profile.remote_preference = payload.remote_preference

    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "success",
        "message": "Continuous search configuration updated successfully",
    }


# ------------------ ATS CV builder ------------------

def _opportunity_payload(opp: Opportunity, company_name: Optional[str] = None) -> Dict[str, Any]:
    """A stored opportunity in the shape the agents pass between stages."""
    return {
        "id": str(opp.id),
        "title": opp.title,
        "company_name": company_name,
        "description": opp.raw_description or "",
        "tech_required": opp.tech_required or [],
        "location": opp.location,
        "location_type": opp.location_type,
        "salary_min": opp.salary_min,
        "salary_max": opp.salary_max,
        "source": opp.source_platform,
        "source_url": opp.source_url,
        "match_score": opp.score,
    }


async def _load_owned_opportunity(
    opportunity_id: str, user_id: uuid.UUID, db: AsyncSession
) -> tuple[Opportunity, Optional[str]]:
    """Fetch one opportunity this user may act on, plus the employer's name."""
    try:
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opp = (
        await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
    ).scalars().first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.user_id is not None and opp.user_id != user_id:
        # Another candidate's scored copy of a posting is not this user's to read.
        raise HTTPException(status_code=404, detail="Opportunity not found")

    company_name = None
    if opp.company_id:
        company = (
            await db.execute(select(Company).where(Company.id == opp.company_id))
        ).scalars().first()
        company_name = company.name if company else None
    return opp, company_name


async def _load_owned_cv(cv_id: str, user_id: uuid.UUID, db: AsyncSession) -> GeneratedCV:
    try:
        cv_uuid = uuid.UUID(cv_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CV ID format")
    row = (
        await db.execute(
            select(GeneratedCV).where(GeneratedCV.id == cv_uuid, GeneratedCV.user_id == user_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="CV not found")
    return row


@router.post("/cv/build")
async def build_ats_cv(
    payload: CVBuildRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Build an ATS-safe CV from this user's profile, optionally tailored to a job.

    Gated on a complete profile: a CV assembled from half a profile is the one
    that gets filtered out, and no generator can invent the experience an ATS is
    looking for.
    """
    user_id = await _get_user_id(current_user, db)
    fallback_name = current_user.full_name or current_user.username
    profile = await require_complete_profile(user_id, db, fallback_name=fallback_name)
    candidate_profile = build_candidate_profile(
        profile, fallback_name=fallback_name, email=current_user.email
    )

    opportunity_payload: Optional[Dict[str, Any]] = None
    if payload.opportunity_id:
        opp, company_name = await _load_owned_opportunity(payload.opportunity_id, user_id, db)
        opportunity_payload = _opportunity_payload(opp, company_name)

    agent = CVBuilderAgent()
    built = await agent.build(candidate_profile, opportunity_payload, use_ai=payload.use_ai)
    saved = await cv_store.save_generated_cvs(user_id, [built], db)
    row = saved["rows"][0] if saved["rows"] else None

    await event_bus.publish(
        event_type="cv.built",
        message=(
            f"ATS CV built for {built.get('target_title') or 'your profile'}"
            f" - score {built.get('ats_score')}/100"
        ),
        severity="success",
        payload={
            "cv_id": built.get("cv_id"),
            "ats_score": built.get("ats_score"),
            "keywords_matched": len(built.get("keywords_matched") or []),
            "keywords_missing": len(built.get("keywords_missing") or []),
            "generator": "ai" if built.get("summary_source") == "ai" else "template",
        },
        user_id=str(user_id),
    )

    return {
        "status": "success",
        "cv": cv_store.cv_detail(row) if row is not None else None,
        # The honest list of what the posting asked for and the profile does not
        # claim - shown to the user, never written into the CV.
        "keywords_missing": built.get("keywords_missing") or [],
        "recommendations": built.get("recommendations") or [],
        "format_warnings": built.get("issues") or [],
        "summary_source": built.get("summary_source"),
    }


@router.get("/cv/versions")
async def list_generated_cvs(
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Every CV built for this user, newest first."""
    user_id = await _get_user_id(current_user, db)
    rows = (
        await db.execute(
            select(GeneratedCV)
            .where(GeneratedCV.user_id == user_id)
            .order_by(desc(GeneratedCV.created_at))
            .limit(limit)
        )
    ).scalars().all()

    scores = [row.ats_score for row in rows if row.ats_score is not None]
    return {
        "status": "success",
        "count": len(rows),
        "best_ats_score": max(scores) if scores else None,
        "formats": list(cv_store.DOWNLOAD_FORMATS),
        "versions": [cv_store.cv_summary(row) for row in rows],
    }


@router.get("/cv/{cv_id}")
async def get_generated_cv(
    cv_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """One stored CV, including the exact text an ATS would parse."""
    user_id = await _get_user_id(current_user, db)
    row = await _load_owned_cv(cv_id, user_id, db)
    return {"status": "success", "cv": cv_store.cv_detail(row)}


@router.get("/cv/{cv_id}/download")
async def download_generated_cv(
    cv_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx|txt)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download a stored CV. Every format is rendered from the same plain text."""
    user_id = await _get_user_id(current_user, db)
    row = await _load_owned_cv(cv_id, user_id, db)
    try:
        body, media_type, filename = cv_store.render(row, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/cv/{cv_id}/ats-check")
async def check_cv_ats_score(
    cv_id: str,
    opportunity_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Re-score a stored CV, optionally against a different target job.

    Re-scoring reads the stored text, so what is measured is exactly what an
    employer's parser would receive.
    """
    user_id = await _get_user_id(current_user, db)
    row = await _load_owned_cv(cv_id, user_id, db)

    profile, _ = await get_profile_completion(
        user_id, db, fallback_name=current_user.full_name or current_user.username
    )
    candidate_profile = (
        build_candidate_profile(
            profile,
            fallback_name=current_user.full_name or current_user.username,
            email=current_user.email,
        )
        if profile
        else {}
    )

    target_id = opportunity_id or (str(row.opportunity_id) if row.opportunity_id else None)
    opportunity_payload: Optional[Dict[str, Any]] = None
    if target_id:
        opp, company_name = await _load_owned_opportunity(target_id, user_id, db)
        opportunity_payload = _opportunity_payload(opp, company_name)

    agent = CVBuilderAgent()
    required = agent.extract_requirement_keywords(opportunity_payload)
    matched, missing = agent.align_keywords(candidate_profile.get("skills") or [], required)
    format_points, format_issues = agent.check_format_safety(row.content_text or "")
    report = agent.score_ats(
        row.content_text or "",
        required_keywords=required,
        matched_keywords=matched,
        sections=row.sections or {},
        profile=candidate_profile,
    )

    row.ats_score = report["ats_score"]
    row.ats_breakdown = {
        "components": report["breakdown"],
        "maximums": report["breakdown_maximums"],
        "measured_out_of": report["measured_out_of"],
        "word_count": report["word_count"],
        "recommendations": report["recommendations"],
        "keywords_required": required,
        "rechecked_against_opportunity_id": target_id,
    }
    row.keywords_matched = matched
    row.keywords_missing = missing
    row.format_warnings = report["issues"]
    await db.commit()

    return {
        "status": "success",
        "cv_id": str(row.id),
        "ats_score": report["ats_score"],
        "breakdown": report["breakdown"],
        "breakdown_maximums": report["breakdown_maximums"],
        "format_safety_points": format_points,
        "format_issues": format_issues,
        "issues": report["issues"],
        "recommendations": report["recommendations"],
        "keywords_required": required,
        "keywords_matched": matched,
        "keywords_missing": missing,
        "checked_against": opportunity_payload["title"] if opportunity_payload else None,
    }


# ------------------ Agent pipeline ------------------

@router.post("/pipeline/run")
async def run_career_pipeline(
    payload: PipelineRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run the full agent chain for this user: search -> score -> CV -> outreach draft.

    Gated on a complete profile (428 with the missing fields when it is not).
    Queued on Celery when a broker is reachable; otherwise it runs inline so the
    feature works on a single-process install.
    """
    user_id = await _get_user_id(current_user, db)
    fallback_name = current_user.full_name or current_user.username
    await require_complete_profile(user_id, db, fallback_name=fallback_name)

    trigger = payload.trigger or "manual"
    stages = [
        {"stage": stage, "index": index, "label": STAGE_LABELS.get(stage, stage)}
        for index, stage in enumerate(PIPELINE_STAGES)
    ]

    if payload.background:
        try:
            from backend.tasks.agent_tasks import run_career_pipeline_task

            queued = run_career_pipeline_task.delay(str(user_id), trigger)
            return {
                "status": "queued",
                "task_id": str(queued.id),
                "execution_id": None,
                "stages": stages,
                "message": "Agents are running. Watch the live feed for stage-by-stage progress.",
            }
        except Exception as exc:  # no broker configured or unreachable
            # Falling back to inline execution is better than telling a user with
            # a complete profile that nothing can run.
            await event_bus.publish(
                event_type="pipeline.queue_unavailable",
                message="Task queue unavailable; running the agents inline instead.",
                severity="warning",
                payload={"error": str(exc)},
                user_id=str(user_id),
            )

    result = await CareerPipeline().run(user_id, trigger=trigger, session=db)
    return {**result, "stages_declared": stages}


@router.get("/pipeline")
async def list_pipeline_runs(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """This user's recent pipeline runs, newest first."""
    user_id = await _get_user_id(current_user, db)
    rows = (
        await db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.user_id == user_id)
            .order_by(desc(WorkflowExecution.started_at))
            .limit(limit)
        )
    ).scalars().all()

    return {
        "status": "success",
        "stages": [
            {"stage": stage, "index": index, "label": STAGE_LABELS.get(stage, stage)}
            for index, stage in enumerate(PIPELINE_STAGES)
        ],
        "runs": [
            {
                "id": str(row.id),
                "workflow_type": row.workflow_type,
                "status": row.status,
                "current_step": row.current_step,
                "error_message": row.error_message,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in rows
        ],
    }


@router.get("/pipeline/{execution_id}")
async def get_pipeline_run(
    execution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Stage-by-stage status of one run, for the progress view."""
    user_id = await _get_user_id(current_user, db)
    try:
        exec_uuid = uuid.UUID(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = (
        await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == exec_uuid)
        )
    ).scalars().first()
    if not execution or (execution.user_id is not None and execution.user_id != user_id):
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    status_payload = await WorkflowEngine.get_workflow_status(execution_id)
    if not status_payload:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    for step in status_payload.get("steps", []):
        step["label"] = STAGE_LABELS.get(step["agent_name"], step["agent_name"])

    completed = sum(1 for s in status_payload["steps"] if s["status"] == "completed")
    total = len(status_payload["steps"]) or 1
    return {
        "status": "success",
        "run": status_payload,
        "progress_percent": round(100 * completed / total),
        "stages_completed": completed,
        "stage_total": total,
    }

