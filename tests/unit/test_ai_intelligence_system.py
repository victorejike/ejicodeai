"""Comprehensive test suite for the Full Operational AI Intelligence System.
Verifies CV parsing, anti-fabrication rules, central tool registry (23 tools),
6-factor transparent matching, event bus, and live discovery.
"""
import asyncio
import pytest
from datetime import datetime

from agents.extraction.cv_parser import parse_cv_document, extract_contact_info, segment_sections
from agents.tools.registry import (
    TOOL_REGISTRY,
    list_available_tools,
    calculate_candidate_match,
    generate_truthful_proposal,
    generate_truthful_outreach,
    generate_invite_message,
    detect_scam_opportunity,
    extract_talent_criteria_from_job,
    deduplicate_records,
)
from backend.app.services.event_bus import EventBus


SAMPLE_CV = """Dr. Victor Ejike
Lead AI Architect & Distributed Systems Engineer
victor@ejicode.ai | +1 555 987 6543 | github.com/victorejike | linkedin.com/in/victorejike
Location: San Francisco, CA

SUMMARY
Principal systems architect with 7 years engineering production-grade distributed agent systems,
real-time event streaming architectures, and autonomous platforms.

WORK EXPERIENCE
Principal AI Systems Architect | Ejicode Intelligence Labs
Jan 2021 - Present
• Designed autonomous multi-agent orchestration engines using FastAPI, Redis, and PyTorch.
• Built low-latency event-driven microservices on AWS with Docker and Kubernetes.
• Scaled data ingestion pipelines to 50M records daily using PostgreSQL and ChromaDB.

Senior Backend Engineer | Apex Scale Corp
Mar 2017 - Dec 2020
• Developed scalable REST and GraphQL APIs in Python, Go, and TypeScript.
• Maintained automated CI/CD deployment pipelines on GCP.

EDUCATION
Ph.D. in Computer Engineering, Stanford University, 2017

KEY PROJECTS
Ejicode Autonomous Career Agent: Built reactive multi-agent system in Python and Next.js.
https://github.com/victorejike/ejicodeai

TECHNICAL SKILLS
Python, TypeScript, Go, FastAPI, React, Next.js, Docker, Kubernetes, AWS, GCP, PostgreSQL, Redis, PyTorch, LangChain, Microservices, CI/CD
"""


def test_cv_parser_factual_intelligence():
    """Verify CV intelligence parsing and zero-fabrication rules."""
    result = parse_cv_document(SAMPLE_CV.encode("utf-8"), "victor_cv.txt", "txt")
    
    assert result["status"] == "completed"
    assert result["full_name"] == "Dr. Victor Ejike"
    assert "Lead AI Architect" in result["title"]
    assert result["contact_info"]["email"] == "victor@ejicode.ai"
    assert result["contact_info"]["phone"] == "+1 555 987 6543"
    assert result["contact_info"]["location"] == "San Francisco, CA"
    assert result["contact_info"]["github"] == "https://github.com/victorejike"
    assert result["contact_info"]["linkedin"] == "https://linkedin.com/in/victorejike"
    
    # Skills check
    skills = result["skills_list"]
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "Kubernetes" in skills
    assert "PostgreSQL" in skills
    
    # Experience check
    assert result["experience_years"] >= 6.0
    assert len(result["experience"]) == 2
    assert result["experience"][0]["is_current"] is True
    
    # Confidence score
    assert result["confidence_score"] >= 0.90


def test_anti_fabrication_unknown_defaults():
    """Verify that unmentioned data is strictly None and not fabricated."""
    sparse_cv = """Jane Doe
Software Developer
jane@example.com

EXPERIENCE
Developer | LocalTech
2022 - Present
• Built websites using HTML and CSS.
"""
    result = parse_cv_document(sparse_cv.encode("utf-8"), "sparse_cv.txt", "txt")
    
    # Should not invent missing fields
    assert result["contact_info"]["phone"] is None
    assert result["contact_info"]["github"] is None
    assert result["contact_info"]["linkedin"] is None
    assert result["contact_info"]["location"] is None
    assert len(result["education"]) == 0
    assert len(result["projects"]) == 0


def test_all_23_tools_registered():
    """Verify all 23 central tools are present and callable in tool registry."""
    tools = list_available_tools()
    assert len(tools) == 23
    
    expected_tools = [
        "search_live_jobs",
        "search_contract_gigs",
        "search_github_talent",
        "search_companies_by_tech",
        "extract_document_text",
        "parse_cv_structured",
        "normalize_job_data",
        "deduplicate_records",
        "verify_domain_mx",
        "verify_email_format",
        "research_company_profile",
        "calculate_candidate_match",
        "rank_opportunities_for_user",
        "rank_candidates_for_job",
        "generate_truthful_proposal",
        "generate_truthful_outreach",
        "generate_invite_message",
        "schedule_follow_up",
        "log_agent_event",
        "check_opportunity_freshness",
        "detect_scam_opportunity",
        "extract_talent_criteria_from_job",
        "summarize_placement_pipeline",
    ]
    for exp in expected_tools:
        assert exp in TOOL_REGISTRY, f"Missing tool: {exp}"


def test_six_factor_matching_algorithm():
    """Verify transparent 6-factor matching generates why_matches, evidence, and gaps."""
    candidate = {
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "experience_years": 5.0,
        "title": "Senior Backend Architect",
        "remote_preference": "remote",
    }
    
    job = {
        "title": "Senior Python Backend Engineer",
        "tech_required": ["Python", "FastAPI", "Docker", "Kubernetes", "Rust"],
        "min_experience_years": 4.0,
        "location_type": "remote",
    }
    
    match = calculate_candidate_match(candidate, job)
    
    assert "score" in match
    assert 0 <= match["score"] <= 100
    assert "why_matches" in match
    assert len(match["relevant_evidence"]) > 0
    assert len(match["potential_gaps"]) > 0
    # Gaps should identify Rust and Kubernetes as not found
    gaps_str = " ".join(match["potential_gaps"]).lower()
    assert "rust" in gaps_str or "kubernetes" in gaps_str


def test_truthful_proposal_generation():
    """Verify generated proposal adheres strictly to candidate's real capabilities."""
    profile = {
        "full_name": "Victor Ejike",
        "skills_list": ["Python", "FastAPI", "Docker", "Kubernetes"],
    }
    job = {
        "title": "Staff Platform Engineer",
        "company_name": "ScaleAI Corp",
    }
    proposal = generate_truthful_proposal(profile, job)
    
    assert "Victor Ejike" in proposal["body"]
    assert "ScaleAI Corp" in proposal["body"]
    assert "Python" in proposal["body"]
    assert proposal["anti_fabrication_verified"] is True


def test_scam_detection_tool():
    """Verify anti-scam tool catches upfront fee / crypto fraud."""
    safe_job = {
        "title": "Senior Frontend Developer",
        "description": "Looking for a React and Next.js expert to build responsive dashboards. Competitive salary.",
    }
    scam_job = {
        "title": "Data Entry Specialist",
        "description": "Earn $5000/week! Send BTC investment or contact telegram @easycrypto to pay registration fee.",
    }
    
    assert detect_scam_opportunity(safe_job)["is_safe"] is True
    assert detect_scam_opportunity(scam_job)["is_safe"] is False
    assert len(detect_scam_opportunity(scam_job)["flags"]) > 0


def test_talent_criteria_extraction():
    """Verify organization requirement extraction from unstructured job description."""
    raw_jd = """Senior AI Systems Architect
We need a seasoned architect with 5+ years of experience in Python, FastAPI, and Kubernetes.
Must be comfortable in a remote environment building scalable microservices.
"""
    criteria = extract_talent_criteria_from_job(raw_jd)
    
    assert criteria["title"] == "Senior AI Systems Architect"
    assert "Python" in criteria["required_skills"]
    assert "FastAPI" in criteria["required_skills"]
    assert criteria["min_experience_years"] == 5.0
    assert criteria["location_type"] == "remote"


@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    """Verify async event bus publishes and delivers real-time events to subscribers."""
    bus = EventBus(max_history=50)
    received = []

    async def reader():
        async for ev in bus.subscribe(user_id="test-user"):
            received.append(ev)
            if len(received) >= 1:
                break

    task = asyncio.create_task(reader())
    await asyncio.sleep(0.05)  # Allow subscriber to attach

    await bus.publish(
        event_type="test.event",
        message="Integration test event",
        payload={"sample": 123},
        user_id="test-user",
    )

    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 1
    assert received[0]["message"] == "Integration test event"
    assert received[0]["user_id"] == "test-user"
