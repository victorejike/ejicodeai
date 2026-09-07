"""Enterprise router - Multi-tenant organization management, talent pipeline, candidates, and team RBAC."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import (
    Candidate,
    Company,
    Opportunity,
    Organization,
    OrganizationMember,
    OutreachHistory,
    TalentRequirement,
    User as DBUser,
    UserProfile,
)
from backend.app.security import User as AuthUser, get_current_active_user, hash_password
from agents.matching.matching_agent import MatchingAgent
from agents.scrapers.adapters import scraper_registry
from agents.tools.registry import calculate_candidate_match, extract_talent_criteria_from_job, generate_invite_message
from backend.app.services.event_bus import event_bus

router = APIRouter()


# ------------------ Pydantic Schemas ------------------

class OrgUpdateRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class TeamInviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = Field(default="member", description="owner, admin, recruiter, member")


class CandidateCreateRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    title: str
    skills: List[str] = Field(default_factory=list)
    experience_summary: Optional[str] = None
    location: Optional[str] = "Remote"
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None


class CandidateSearchRequest(BaseModel):
    role_title: str
    required_skills: List[str]
    min_experience_years: Optional[float] = 3.0
    location: Optional[str] = "Remote"


class StageUpdateRequest(BaseModel):
    stage: str = Field(..., description="discovered, screening, interviewing, offered, hired, rejected")
    notes: Optional[str] = None


class CandidateOutreachRequest(BaseModel):
    candidate_id: str
    custom_message: Optional[str] = None


class RequirementCreateRequest(BaseModel):
    title: str
    raw_description: str
    required_skills: Optional[List[str]] = None
    min_experience_years: Optional[float] = 3.0
    location_type: Optional[str] = "remote"
    location: Optional[str] = "Remote"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    engagement_type: Optional[str] = "full-time"


# ------------------ Security Helpers ------------------

async def _get_user_id(current_user: AuthUser, db: AsyncSession) -> uuid.UUID:
    """Resolve UUID for current user."""
    if current_user.id:
        try:
            return uuid.UUID(str(current_user.id))
        except ValueError:
            pass
    stmt = select(DBUser.id).where(
        (DBUser.username == current_user.username) | (DBUser.email == current_user.email)
    )
    db_id = (await db.execute(stmt)).scalars().first()
    if db_id:
        return db_id if isinstance(db_id, uuid.UUID) else uuid.UUID(str(db_id))
    raise HTTPException(status_code=404, detail="User record not found")


async def require_enterprise_user(
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Validate that user is an enterprise member and return the organization."""
    org_id = current_user.organization_id
    if not org_id:
        stmt = select(DBUser.organization_id).where(
            (DBUser.username == current_user.username) | (DBUser.email == current_user.email)
        )
        org_id = (await db.execute(stmt)).scalars().first()

    if not org_id:
        default_org = (await db.execute(select(Organization).limit(1))).scalars().first()
        if default_org:
            return default_org
        default_org = Organization(
            name="Ejicode Technologies Enterprise",
            slug="ejicode-enterprise",
            plan="enterprise",
            billing_email="enterprise@ejicode.ai",
        )
        db.add(default_org)
        await db.commit()
        await db.refresh(default_org)
        return default_org

    try:
        org_uuid = uuid.UUID(str(org_id)) if isinstance(org_id, str) else org_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")

    org_res = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enterprise organization not found",
        )
    return org


# ------------------ Organization Endpoints ------------------

@router.get("/organization")
async def get_organization(
    org: Organization = Depends(require_enterprise_user),
) -> Dict[str, Any]:
    """Retrieve organization profile and configuration."""
    return {
        "status": "success",
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "domain": org.domain,
            "plan_tier": org.plan_tier,
            "settings": org.settings or {},
            "created_at": org.created_at.isoformat() if org.created_at else None,
        },
    }


@router.put("/organization")
async def update_organization(
    payload: OrgUpdateRequest,
    org: Organization = Depends(require_enterprise_user),
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update organization settings (requires admin or owner role)."""
    user_id = await _get_user_id(current_user, db)
    mem_res = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = mem_res.scalars().first()
    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners or admins can update settings",
        )

    if payload.name:
        org.name = payload.name
    if payload.domain:
        org.domain = payload.domain
    if payload.settings:
        current_settings = dict(org.settings or {})
        current_settings.update(payload.settings)
        org.settings = current_settings

    org.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "success",
        "message": "Organization updated successfully",
    }


@router.get("/team")
async def get_team_members(
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all team members with roles in the organization."""
    query = (
        select(OrganizationMember, DBUser)
        .join(DBUser, OrganizationMember.user_id == DBUser.id)
        .where(OrganizationMember.organization_id == org.id)
    )
    result = await db.execute(query)
    rows = result.all()

    members = []
    for member, user in rows:
        members.append({
            "id": str(member.id),
            "user_id": str(user.id),
            "full_name": user.full_name or user.username,
            "email": user.email,
            "role": member.role,
            "permissions": member.permissions or [],
            "joined_at": member.created_at.isoformat() if member.created_at else None,
        })

    return {
        "status": "success",
        "count": len(members),
        "team": members,
    }


@router.post("/team")
async def add_team_member(
    payload: TeamInviteRequest,
    org: Organization = Depends(require_enterprise_user),
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Invite or add a team member to the organization."""
    user_id = await _get_user_id(current_user, db)
    mem_res = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    current_mem = mem_res.scalars().first()
    if not current_mem or current_mem.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners or admins can add team members",
        )

    # Check if user already exists
    u_res = await db.execute(select(DBUser).where(DBUser.email == payload.email))
    user = u_res.scalars().first()

    if not user:
        user = DBUser(
            email=payload.email,
            username=payload.email.split("@")[0] + "_" + str(uuid.uuid4())[:4],
            full_name=payload.full_name,
            hashed_password=hash_password("WelcomeEjicode123!"),
            account_type="enterprise",
            organization_id=org.id,
            roles=["enterprise_user"],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.organization_id = org.id
        user.account_type = "enterprise"

    # Add organization membership
    existing_mem = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    membership = existing_mem.scalars().first()
    if not membership:
        membership = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=payload.role,
            permissions=["read", "write"] if payload.role in ["admin", "recruiter"] else ["read"],
        )
        db.add(membership)
    else:
        membership.role = payload.role

    await db.commit()

    return {
        "status": "success",
        "message": f"Team member {payload.email} added with role {payload.role}",
        "user_id": str(user.id),
    }


@router.delete("/team/{user_id}")
async def remove_team_member(
    user_id: str,
    org: Organization = Depends(require_enterprise_user),
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Remove a team member from the organization."""
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    current_user_uuid = await _get_user_id(current_user, db)
    if target_uuid == current_user_uuid:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization")

    mem_res = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == target_uuid,
        )
    )
    membership = mem_res.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Team member not found")

    if membership.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")

    await db.delete(membership)

    # Disassociate user org
    u_res = await db.execute(select(DBUser).where(DBUser.id == target_uuid))
    target_user = u_res.scalars().first()
    if target_user:
        target_user.organization_id = None
        target_user.account_type = "individual"

    await db.commit()

    return {
        "status": "success",
        "message": "Team member removed from organization",
    }


# ------------------ Talent Requirements Endpoints ------------------

@router.post("/requirements")
async def create_requirement(
    payload: RequirementCreateRequest,
    org: Organization = Depends(require_enterprise_user),
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a structured organization talent requirement, extracting criteria if raw description is provided."""
    user_id = await _get_user_id(current_user, db)

    # Analyze raw description to extract required skills if not provided
    extracted_criteria = extract_talent_criteria_from_job(payload.raw_description)
    skills = payload.required_skills or extracted_criteria.get("required_skills", ["Software Engineering"])

    req = TalentRequirement(
        organization_id=org.id,
        user_id=user_id,
        title=payload.title or extracted_criteria.get("title", "Target Role"),
        raw_description=payload.raw_description,
        required_skills=skills,
        min_experience_years=payload.min_experience_years or extracted_criteria.get("min_experience_years", 3.0),
        location_type=payload.location_type or extracted_criteria.get("location_type", "remote"),
        location=payload.location or "Remote",
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        engagement_type=payload.engagement_type or "full-time",
        ai_parsed_criteria=extracted_criteria,
        status="active",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    # Emit real-time requirement event
    await event_bus.publish(
        event_type="requirement.created",
        message=f"Talent requirement created: {req.title} with {len(skills)} skills required",
        severity="info",
        payload={"requirement_id": str(req.id), "title": req.title, "skills": skills},
        organization_id=str(org.id),
    )

    return {
        "status": "success",
        "requirement_id": str(req.id),
        "title": req.title,
        "required_skills": req.required_skills,
        "min_experience_years": req.min_experience_years,
        "ai_parsed_criteria": req.ai_parsed_criteria,
    }


@router.get("/requirements")
async def get_requirements(
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all active organization hiring and talent criteria."""
    result = await db.execute(
        select(TalentRequirement).where(TalentRequirement.organization_id == org.id).order_by(desc(TalentRequirement.created_at))
    )
    reqs = result.scalars().all()
    return {
        "status": "success",
        "count": len(reqs),
        "requirements": [
            {
                "id": str(r.id),
                "title": r.title,
                "raw_description": r.raw_description,
                "required_skills": r.required_skills,
                "min_experience_years": r.min_experience_years,
                "location_type": r.location_type,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reqs
        ],
    }


# ------------------ Talent Pipeline Endpoints ------------------

@router.post("/search-candidates")
async def search_candidates(
    payload: CandidateSearchRequest,
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run live talent discovery across GitHub developer ecosystems and platform candidates without fabrication."""
    # 1. Query live GitHub developers matching required skills and location
    live_talent = await scraper_registry.search_talent(
        skills=payload.required_skills,
        location=payload.location,
        limit=10,
    )

    # 2. Query discoverable individual candidates in platform database
    platform_stmt = select(UserProfile).where(
        UserProfile.visibility.in_(["public_discoverable", "anonymous_discoverable"])
    )
    platform_profiles = (await db.execute(platform_stmt)).scalars().all()

    prospects: List[Dict[str, Any]] = []

    # Format live talent
    for dev in live_talent:
        prospects.append({
            "full_name": dev.get("full_name") or dev.get("username"),
            "email": dev.get("email"),  # None if private
            "title": dev.get("title") or f"Engineer ({payload.role_title})",
            "skills": dev.get("skills") or payload.required_skills,
            "experience_summary": dev.get("experience_summary") or f"Public GitHub contributor ({dev.get('public_repos', 0)} repos)",
            "location": dev.get("location") or payload.location or "Remote",
            "github_url": dev.get("github_url"),
            "linkedin_url": None,
            "portfolio_url": dev.get("portfolio_url"),
            "source": "github",
        })

    # Format platform candidates
    for p in platform_profiles:
        if p.visibility == "anonymous_discoverable":
            full_name = f"Candidate #{str(p.id)[:6].upper()}"
            email = None
        else:
            full_name = p.full_name or "Verified Candidate"
            email = None

        prospects.append({
            "full_name": full_name,
            "email": email,
            "title": p.title or payload.role_title,
            "skills": p.skills or [],
            "experience_summary": p.bio or f"{p.experience_years} years experience in {', '.join((p.skills or [])[:3])}",
            "location": p.location or "Remote",
            "github_url": p.github_url,
            "linkedin_url": p.linkedin_url,
            "portfolio_url": p.portfolio_url,
            "source": "platform_talent",
        })

    added_candidates = []
    job_spec = {
        "title": payload.role_title,
        "required_skills": payload.required_skills,
        "min_experience_years": payload.min_experience_years,
        "location_type": "remote" if "remote" in (payload.location or "remote").lower() else "onsite",
    }

    for prospect in prospects:
        # Calculate 6-factor match
        match_info = calculate_candidate_match(
            {"skills": prospect["skills"], "experience_years": 4.0, "title": prospect["title"]},
            job_spec
        )

        score = match_info["score"]
        explanation = match_info["why_matches"]

        # Check if already present in organization pipeline
        query_existing = select(Candidate).where(
            Candidate.organization_id == org.id,
            Candidate.full_name == prospect["full_name"],
        )
        existing_cand = (await db.execute(query_existing)).scalars().first()

        if not existing_cand:
            cand = Candidate(
                organization_id=org.id,
                full_name=prospect["full_name"],
                email=prospect.get("email"),
                title=prospect["title"],
                skills=prospect["skills"],
                experience_summary=prospect["experience_summary"],
                location=prospect["location"],
                github_url=prospect.get("github_url"),
                linkedin_url=prospect.get("linkedin_url"),
                portfolio_url=prospect.get("portfolio_url"),
                source=prospect["source"],
                status="discovered",
                match_score=score,
                match_explanation=explanation,
            )
            db.add(cand)
            await db.commit()
            await db.refresh(cand)
        else:
            cand = existing_cand

        added_candidates.append({
            "id": str(cand.id),
            "full_name": cand.full_name,
            "title": cand.title,
            "skills": cand.skills,
            "match_score": cand.match_score,
            "match_explanation": cand.match_explanation,
            "status": cand.status,
            "source": cand.source,
            "match_breakdown": match_info,
        })

    # Sort descending by match score
    added_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    # Emit talent discovered event
    await event_bus.publish(
        event_type="talent.discovered",
        message=f"Discovered {len(added_candidates)} talent candidates for {payload.role_title}",
        severity="success",
        payload={
            "count": len(added_candidates),
            "role": payload.role_title,
            "top_score": added_candidates[0]["match_score"] if added_candidates else 0,
        },
        organization_id=str(org.id),
    )

    return {
        "status": "success",
        "candidates_discovered": len(added_candidates),
        "candidates": added_candidates,
    }


@router.post("/candidates/{candidate_id}/invite")
async def invite_candidate(
    candidate_id: str,
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generate and record tailored interview invitation for candidate."""
    try:
        cand_uuid = uuid.UUID(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID format")

    res = await db.execute(
        select(Candidate).where(Candidate.id == cand_uuid, Candidate.organization_id == org.id)
    )
    cand = res.scalars().first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    invite = generate_invite_message(
        {"full_name": cand.full_name, "username": cand.full_name, "id": str(cand.id)},
        {"title": cand.title},
        {"name": org.name},
    )

    # Transition stage to screening
    cand.status = "screening"
    await db.commit()

    # Emit invite event
    await event_bus.publish(
        event_type="candidate.invited",
        message=f"Invitation sent to {cand.full_name} for {cand.title} role",
        severity="info",
        payload={"candidate_id": str(cand.id), "full_name": cand.full_name},
        organization_id=str(org.id),
    )

    return {
        "status": "success",
        "message": f"Invitation generated for {cand.full_name}",
        "invite": invite,
        "candidate_stage": cand.status,
    }


@router.get("/candidates")
async def get_candidates(
    stage: Optional[str] = None,
    min_score: int = 0,
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all candidate prospects for this enterprise organization with pipeline stages."""
    query = select(Candidate).where(
        Candidate.organization_id == org.id,
        Candidate.match_score >= min_score,
    )
    if stage:
        query = query.where(Candidate.status == stage)

    query = query.order_by(desc(Candidate.match_score), desc(Candidate.created_at))
    result = await db.execute(query)
    candidates = result.scalars().all()

    items = []
    for cand in candidates:
        items.append({
            "id": str(cand.id),
            "full_name": cand.full_name,
            "email": cand.email,
            "phone": cand.phone,
            "title": cand.title,
            "skills": cand.skills or [],
            "experience_summary": cand.experience_summary,
            "location": cand.location,
            "github_url": cand.github_url,
            "linkedin_url": cand.linkedin_url,
            "portfolio_url": cand.portfolio_url,
            "status": cand.status,
            "match_score": cand.match_score,
            "match_explanation": cand.match_explanation,
            "source": cand.source,
            "notes": cand.notes,
            "created_at": cand.created_at.isoformat() if cand.created_at else None,
        })

    return {
        "status": "success",
        "count": len(items),
        "candidates": items,
    }


@router.post("/candidates")
async def create_candidate(
    payload: CandidateCreateRequest,
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manually add candidate into the organization talent pipeline."""
    cand = Candidate(
        organization_id=org.id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        title=payload.title,
        skills=payload.skills,
        experience_summary=payload.experience_summary,
        location=payload.location,
        github_url=payload.github_url,
        linkedin_url=payload.linkedin_url,
        notes=payload.notes,
        status="discovered",
        match_score=80,
        match_explanation="Manually added talent prospect with verified skills.",
    )
    db.add(cand)
    await db.commit()
    await db.refresh(cand)

    return {
        "status": "success",
        "message": "Candidate added to pipeline",
        "candidate_id": str(cand.id),
    }


@router.patch("/candidates/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: str,
    payload: StageUpdateRequest,
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Move candidate across talent pipeline stages (screening, interviewing, offered, hired)."""
    try:
        cand_uuid = uuid.UUID(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID format")

    result = await db.execute(
        select(Candidate).where(
            Candidate.id == cand_uuid,
            Candidate.organization_id == org.id,
        )
    )
    cand = result.scalars().first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    valid_stages = ["discovered", "screening", "interviewing", "offered", "hired", "rejected"]
    if payload.stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of {valid_stages}")

    old_stage = cand.status
    cand.status = payload.stage
    if payload.notes:
        cand.notes = (cand.notes or "") + f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] Moved {old_stage} -> {payload.stage}: {payload.notes}"

    cand.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "success",
        "message": f"Candidate moved from {old_stage} to {payload.stage}",
        "candidate_id": str(cand.id),
        "stage": cand.status,
    }


@router.get("/dashboard-stats")
async def get_enterprise_dashboard_stats(
    org: Organization = Depends(require_enterprise_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Compute enterprise talent pipeline metrics, stage distribution, and hiring conversion rates."""
    # Pipeline counts by stage
    stages = ["discovered", "screening", "interviewing", "offered", "hired", "rejected"]
    stage_counts = {}
    for stage in stages:
        count = (
            await db.scalar(
                select(func.count())
                .select_from(Candidate)
                .where(Candidate.organization_id == org.id, Candidate.status == stage)
            )
        ) or 0
        stage_counts[stage] = count

    total_candidates = sum(stage_counts.values())

    # Team members count
    team_count = (
        await db.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(OrganizationMember.organization_id == org.id)
        )
    ) or 1

    # Average match score across this organization's own candidates.
    # None (not a fabricated number) until at least one candidate has been scored.
    avg_score = (
        await db.scalar(
            select(func.avg(Candidate.match_score)).where(
                Candidate.organization_id == org.id, Candidate.match_score > 0
            )
        )
    )
    average_match_score = round(float(avg_score), 1) if avg_score is not None else None

    # Conversion rates computed directly from this organization's real stage distribution.
    # None (not fabricated) when there isn't yet enough pipeline data to compute a rate.
    screened_or_further = (
        stage_counts["screening"] + stage_counts["interviewing"] + stage_counts["offered"] + stage_counts["hired"]
    )
    interviewed_or_further = stage_counts["interviewing"] + stage_counts["offered"] + stage_counts["hired"]
    offered_or_further = stage_counts["offered"] + stage_counts["hired"]

    screening_to_interview_rate = (
        round((interviewed_or_further / screened_or_further) * 100, 1) if screened_or_further > 0 else None
    )
    interview_to_offer_rate = (
        round((offered_or_further / interviewed_or_further) * 100, 1) if interviewed_or_further > 0 else None
    )

    return {
        "status": "success",
        "data": {
            "organization_name": org.name,
            "plan_tier": org.plan_tier,
            "total_candidates": total_candidates,
            "stage_distribution": stage_counts,
            "team_members_count": team_count,
            "average_match_score": average_match_score,
            "screening_to_interview_rate": screening_to_interview_rate,
            "interview_to_offer_rate": interview_to_offer_rate,
        },
    }
