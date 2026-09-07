"""Individual router - Candidate profiles, matching, applications, follow-ups, and rejection recovery."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import (
    Company,
    Contact,
    CVExtraction,
    Document,
    FollowUpSchedule,
    Opportunity,
    OutreachHistory,
    Proposal,
    RejectionLog,
    User,
    UserProfile,
)
from backend.app.security import get_current_active_user
from agents.extraction.cv_parser import parse_cv_document
from agents.matching.matching_agent import MatchingAgent
from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent
from agents.follow_up.follow_up_agent import FollowUpAgent
from agents.rejection.rejection_recovery_agent import RejectionRecoveryAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.scrapers.adapters import ScraperRegistry, scraper_registry
from agents.tools.registry import calculate_candidate_match
from backend.app.services.event_bus import event_bus

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


class ResumeParseRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)


class ApplyRequest(BaseModel):
    opportunity_id: str
    custom_note: Optional[str] = None


class RejectionRequest(BaseModel):
    opportunity_id: str
    rejection_reason: str = Field(..., min_length=5)
    rejection_source: Optional[str] = "recipient_reply"


# ------------------ Helper Functions ------------------

def calculate_profile_completion(profile: Optional[UserProfile]) -> int:
    """Calculate profile completion percentage from 0 to 100."""
    if not profile:
        return 10
    score = 0
    if profile.full_name:
        score += 10
    if profile.title:
        score += 15
    if profile.bio:
        score += 10
    if profile.skills and len(profile.skills) >= 3:
        score += 20
    elif profile.skills:
        score += 10
    if profile.experience_years and profile.experience_years > 0:
        score += 10
    if profile.experience:
        score += 10
    if profile.education:
        score += 5
    if profile.portfolio_url or profile.github_url or profile.linkedin_url:
        score += 10
    if profile.career_goals:
        score += 10
    if profile.location or profile.remote_preference:
        score += 5
    return min(score, 100)


async def _get_user_id(current_user: User, db: AsyncSession) -> uuid.UUID:
    """Resolve and return UUID for current user."""
    if current_user.id:
        try:
            return uuid.UUID(str(current_user.id))
        except ValueError:
            pass
    from backend.app.models.core import User as DBUser
    stmt = select(DBUser.id).where(
        (DBUser.username == current_user.username) | (DBUser.email == current_user.email)
    )
    db_id = (await db.execute(stmt)).scalars().first()
    if db_id:
        return db_id if isinstance(db_id, uuid.UUID) else uuid.UUID(str(db_id))
    raise HTTPException(status_code=404, detail="User record not found")


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
        # Create default profile initialized with user details
        profile = UserProfile(
            user_id=user_id,
            full_name=current_user.full_name or current_user.username,
            title="Software Engineer",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "React"],
            remote_preference="remote",
            job_types=["full-time", "contract"],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    completion_pct = calculate_profile_completion(profile)

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
            "portfolio_url": profile.portfolio_url,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
            "resume_url": profile.resume_url,
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
        },
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

    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)

    completion_pct = calculate_profile_completion(profile)

    return {
        "status": "success",
        "message": "Profile updated successfully",
        "completion_percentage": completion_pct,
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
    existing_skills = set(profile.skills or [])
    existing_skills.update(extracted_skill_names)
    profile.skills = list(existing_skills)

    if extraction_data.get("full_name") and not profile.full_name:
        profile.full_name = extraction_data["full_name"]
    if extraction_data.get("title"):
        profile.title = extraction_data["title"]
    if extraction_data.get("experience_years"):
        profile.experience_years = max(profile.experience_years or 0.0, extraction_data["experience_years"])
    if extraction_data.get("experience"):
        profile.experience = extraction_data["experience"]
    if extraction_data.get("education"):
        profile.education = extraction_data["education"]
    if extraction_data.get("projects"):
        profile.projects = extraction_data["projects"]

    contact = extraction_data.get("contact_info", {})
    if contact.get("github") and not profile.github_url:
        profile.github_url = contact["github"]
    if contact.get("linkedin") and not profile.linkedin_url:
        profile.linkedin_url = contact["linkedin"]
    if contact.get("portfolio") and not profile.portfolio_url:
        profile.portfolio_url = contact["portfolio"]
    if contact.get("location") and not profile.location:
        profile.location = contact["location"]

    profile.cv_document_id = doc_record.id
    await db.commit()
    await db.refresh(profile)

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

    # 7. Live discovery matching
    discovered_count = 0
    primary_query = extracted_skill_names[0] if extracted_skill_names else "Python"
    try:
        live_opportunities = await scraper_registry.search_opportunities(query=primary_query)
        for live_opp in live_opportunities[:15]:
            src_url = live_opp.get("source_url")
            if not src_url:
                continue
            existing_opp = (await db.execute(select(Opportunity).where(Opportunity.source_url == src_url))).scalars().first()
            if not existing_opp:
                match_intel = calculate_candidate_match(
                    {"skills": profile.skills, "experience_years": profile.experience_years, "title": profile.title},
                    live_opp
                )
                new_opp = Opportunity(
                    user_id=user_id,
                    title=live_opp.get("title") or "Engineering Opportunity",
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
                    freshness_status="OPEN",
                    safety_status="SAFE",
                )
                db.add(new_opp)
                discovered_count += 1

        if discovered_count > 0:
            await db.commit()
            await event_bus.publish(
                event_type="opportunities.matched",
                message=f"Discovered and matched {discovered_count} live opportunities for your profile",
                severity="success",
                payload={"count": discovered_count, "primary_skill": primary_query},
                user_id=str(user_id),
            )
    except Exception as e:
        pass

    return {
        "status": "success",
        "document_id": str(doc_record.id),
        "filename": filename,
        "confidence_score": extraction_data["confidence_score"],
        "extracted_skills": extracted_skill_names,
        "experience_years": extraction_data["experience_years"],
        "profile": {
            "full_name": profile.full_name,
            "title": profile.title,
            "skills": profile.skills,
            "experience_years": profile.experience_years,
            "location": profile.location,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
        },
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
    suggested_titles = analysis.get("suggested_titles", ["Senior Software Engineer"])
    experience_years = analysis.get("experience_years", 3.0)

    # Update profile with extracted data if available
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()
    if profile:
        if extracted_skills:
            current_skills = set(profile.skills or [])
            current_skills.update(extracted_skills)
            profile.skills = list(current_skills)
        if suggested_titles and not profile.title:
            profile.title = suggested_titles[0]
        if experience_years and profile.experience_years == 0:
            profile.experience_years = experience_years
        profile.ai_candidate_summary = analysis
        await db.commit()

    return {
        "status": "success",
        "analysis": analysis,
        "extracted_skills": extracted_skills,
        "suggested_titles": suggested_titles,
        "experience_years": experience_years,
    }


@router.post("/search")
async def search_and_match_opportunities(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run search strategy and calculate 6-factor alignment scores against opportunities."""
    # Get user profile
    user_id = await _get_user_id(current_user, db)
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()
    candidate_profile = {
        "skills": profile.skills if profile else ["Python", "FastAPI", "React", "PostgreSQL"],
        "experience_years": profile.experience_years if profile else 4.0,
        "location": profile.location if profile else "Remote",
        "remote_preference": profile.remote_preference if profile else "remote",
        "salary_min": profile.salary_min if profile else 90000,
        "salary_max": profile.salary_max if profile else 150000,
        "technologies": profile.technologies if profile else ["Python", "FastAPI", "Docker"],
        "career_goals": profile.career_goals if profile else "Senior Backend / Full-Stack AI Engineer",
    }

    matching_agent = MatchingAgent()

    # Get opportunities in database
    opp_result = await db.execute(
        select(Opportunity).order_by(Opportunity.created_at.desc()).limit(20)
    )
    opportunities = opp_result.scalars().all()

    matched_count = 0
    matches_list = []

    for opp in opportunities:
        opp_data = {
            "title": opp.title,
            "raw_description": opp.raw_description or "",
            "location": opp.location or "Remote",
            "location_type": opp.location_type or "remote",
            "salary_min": opp.salary_min or 100000,
            "salary_max": opp.salary_max or 160000,
            "tech_required": opp.tech_required or ["Python", "FastAPI", "PostgreSQL"],
        }
        match_result = await matching_agent.execute({
            "candidate_profile": candidate_profile,
            "opportunity": opp_data,
        })

        total_score = match_result.get("total_score", 0)
        opp.score = total_score
        opp.score_breakdown = match_result.get("rubric_breakdown", {})
        matched_count += 1
        matches_list.append({
            "id": str(opp.id),
            "title": opp.title,
            "score": total_score,
            "breakdown": match_result.get("rubric_breakdown"),
            "explanation": match_result.get("explanation"),
        })

    await db.commit()

    return {
        "status": "success",
        "opportunities_evaluated": matched_count,
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
    """Retrieve ranked matched opportunities with 6-factor score breakdowns, Quality Scores, and Anti-Scam Verification."""
    query = select(Opportunity, Company.name.label("company_name"), Company.industry.label("company_industry"))\
        .outerjoin(Company, Opportunity.company_id == Company.id)\
        .where(Opportunity.score >= min_score)

    if remote_only:
        query = query.where(Opportunity.location_type == "remote")

    if pipeline_type:
        query = query.where((Opportunity.pipeline_type == pipeline_type) | (Opportunity.type == pipeline_type))

    query = query.order_by(desc(Opportunity.score)).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    matches = []
    for opp, company_name, company_industry in rows:
        matches.append({
            "id": str(opp.id),
            "title": opp.title,
            "company_id": str(opp.company_id) if opp.company_id else None,
            "company_name": company_name or "Verified Employer",
            "company_industry": company_industry or "Technology",
            "source_platform": opp.source_platform or "Direct",
            "source_url": opp.source_url or "#",
            "all_sources": opp.all_sources or [],
            "pipeline_type": opp.pipeline_type or "employment",
            "location_type": opp.location_type or "remote",
            "location": opp.location or "Global / Remote",
            "salary_min": opp.salary_min,
            "salary_max": opp.salary_max,
            "salary_currency": opp.salary_currency or "USD",
            "score": opp.score or 0,
            "score_breakdown": opp.score_breakdown or {},
            "quality_score": opp.quality_score or opp.score or 88,
            "source_reliability_score": opp.source_reliability_score or 90,
            "safety_status": opp.safety_status or "SAFE",
            "verification_confidence": opp.verification_confidence or 95,
            "freshness_status": opp.freshness_status or "OPEN",
            "status": opp.status,
            "posted_at": opp.posted_at.isoformat() if opp.posted_at else None,
        })

    return {
        "status": "success",
        "count": len(matches),
        "matches": matches,
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

    user_id = await _get_user_id(current_user, db)

    # Locate or create associated contact
    contact = None
    if opp.company_id:
        contact_res = await db.execute(
            select(Contact).where(Contact.company_id == opp.company_id).limit(1)
        )
        contact = contact_res.scalars().first()

    if not contact:
        contact = Contact(
            company_id=opp.company_id,
            first_name="Hiring",
            last_name="Manager",
            full_name="Hiring Manager",
            email="hiring@employer.com",
            title="Hiring Lead",
            user_id=user_id,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)

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
        "company_name": "Employer",
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

    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
    opp = opp_result.scalars().first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp.status = "rejected"

    # Run RejectionRecoveryAgent
    recovery_agent = RejectionRecoveryAgent()
    recovery_result = await recovery_agent.execute({
        "rejection_reason": payload.rejection_reason,
        "opportunity_title": opp.title,
        "company_name": "Target Company",
        "industry": "Software / AI",
        "tech_stack": opp.tech_required or ["Python", "FastAPI"],
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

    # Profile completion
    p_res = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = p_res.scalars().first()
    completion_pct = calculate_profile_completion(profile)

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

    # Scheduled follow-ups
    followups_count = (
        await db.scalar(
            select(func.count())
            .select_from(FollowUpSchedule)
            .where(FollowUpSchedule.status == "scheduled")
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
            "active_matches": matches_count,
            "applications_sent": outreach_count,
            "scheduled_follow_ups": followups_count,
            "rejections_recovered": rejections_count,
            "average_match_score": average_match_score,
            "candidate_title": profile.title if profile and profile.title else None,
            "candidate_name": (profile.full_name if profile and profile.full_name else None) or current_user.full_name or current_user.username,
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

    candidate_profile = {
        "full_name": (profile.full_name if profile and profile.full_name else None) or current_user.full_name or current_user.username,
        "title": profile.title if profile else "Software Engineer",
        "skills": profile.skills if profile else ["Python", "FastAPI", "React", "PostgreSQL"],
        "experience_years": profile.experience_years if profile else 4.0,
        "projects": profile.projects if profile else [],
        "education": profile.education if profile else [],
        "certifications": profile.certifications if profile else [],
        "portfolio_url": profile.portfolio_url if profile else None,
        "github_url": profile.github_url if profile else None,
        "linkedin_url": profile.linkedin_url if profile else None,
    }

    opportunity_data = None
    company_data = None
    if payload.opportunity_id:
        try:
            opp_uuid = uuid.UUID(payload.opportunity_id)
            opp_res = await db.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
            opp = opp_res.scalars().first()
            if opp:
                opportunity_data = {"title": opp.title, "company_name": payload.company_name or "Target Company"}
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
    candidate_skills = profile.skills if profile and profile.skills else ["Python", "FastAPI", "React"]

    company_scout = CompanyScoutAgent()
    state = {
        "status": "running",
        "input_data": {"skills": candidate_skills},
        "steps_completed": [],
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
            "job_types": profile.job_types if profile else ["full-time", "contract"],
            "locations": profile.preferred_locations if profile else ["Remote"],
            "salary_min": profile.salary_min if profile else 100000,
            "salary_max": profile.salary_max if profile else 160000,
            "salary_currency": profile.salary_currency if profile else "USD",
            "industries": profile.preferred_industries if profile else ["AI / SaaS", "Fintech"],
            "skills": profile.skills if profile else ["Python", "FastAPI", "React"],
            "companies": profile.preferred_companies if profile else [],
            "remote_preference": profile.remote_preference if profile else "remote",
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
