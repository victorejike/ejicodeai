"""Comprehensive tests for extended agent pipeline:
Extraction, Validation, Deduplication, Matching, Profile Analyzer, Follow-Up, Rejection Recovery, and Scrapers.
"""
import pytest
from agents.extraction.data_extraction_agent import DataExtractionAgent
from agents.validation.validation_agent import ValidationAgent
from agents.deduplication.deduplication_agent import DeduplicationAgent
from agents.matching.matching_agent import MatchingAgent
from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent
from agents.follow_up.follow_up_agent import FollowUpAgent
from agents.rejection.rejection_recovery_agent import RejectionRecoveryAgent
from agents.scrapers.adapters import ScraperRegistry
from agents.base.base_agent import AgentStatus


@pytest.mark.asyncio
async def test_data_extraction_agent_no_fabrication():
    agent = DataExtractionAgent()

    raw_item = {
        "title": "Lead Python Developer",
        "company": "Cognitive AI Lab",
        "raw_description": "We offer $150k - $180k for a remote senior Python FastAPI engineer.",
        "url": "https://remoteok.com/job/12345?utm_source=rss",
    }

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {"raw_items": [raw_item]},
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    opp = result["output_data"]["opportunities"][0]

    assert opp["title"] == "Lead Python Developer"
    assert opp["company_name"] == "Cognitive AI Lab"
    assert opp["location_type"] == "remote"
    assert "Python" in opp["tech_required"]
    assert "FastAPI" in opp["tech_required"]
    # Missing fields must be None, NOT fabricated
    assert opp["contact_email"] is None
    assert opp["contact_name"] is None
    assert opp["deadline"] is None
    # Verify UTM params cleaned
    assert "utm_source" not in opp["source_url"]


@pytest.mark.asyncio
async def test_validation_agent_confidence_scoring():
    agent = ValidationAgent()

    high_quality_opp = {
        "title": "Principal Distributed Systems Engineer",
        "company_name": "Vertex Dynamics",
        "company_domain": "vertexdynamics.com",
        "company_url": "https://vertexdynamics.com",
        "source_url": "https://vertexdynamics.com/careers/lead",
        "description": "Comprehensive job description exceeding 50 characters with detailed technical expectations.",
        "contact_email": "marcus.vance@vertexdynamics.com",
    }

    low_quality_opp = {
        "title": "Dev",
        "company_name": "Unknown",
        "company_domain": None,
        "company_url": None,
        "source_url": None,
        "description": "Short",
        "contact_email": "invalid-email-address",
    }

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {"opportunities": [high_quality_opp, low_quality_opp]},
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    opps = result["output_data"]["opportunities"]

    # High quality
    scores1 = opps[0]["confidence_scores"]
    assert scores1["email_confidence"] >= 0.90
    assert scores1["company_confidence"] >= 0.90
    assert scores1["job_confidence"] >= 0.90
    assert opps[0]["needs_review"] is False

    # Low quality
    scores2 = opps[1]["confidence_scores"]
    assert scores2["email_confidence"] == 0.0
    assert opps[1]["needs_review"] is True
    assert result["output_data"]["flagged_for_review"] == 1


@pytest.mark.asyncio
async def test_deduplication_agent_merging():
    agent = DeduplicationAgent()

    # Two postings of the same job across Indeed and LinkedIn with slight variation
    opp_indeed = {
        "title": "Senior Python Backend Developer",
        "company_name": "DeepScale Systems Inc",
        "company_domain": "deepscale.io",
        "source": "indeed",
        "source_url": "https://indeed.com/viewjob?jk=123",
        "tech_required": ["Python", "FastAPI"],
        "salary_max": 160000,
    }

    opp_linkedin = {
        "title": "Sr. Python Backend Dev",
        "company_name": "DeepScale Systems",
        "company_domain": "deepscale.io",
        "source": "linkedin",
        "source_url": "https://linkedin.com/jobs/view/456",
        "tech_required": ["Python", "Docker", "PostgreSQL"],
        "salary_max": 175000,
        "contact_email": "hiring@deepscale.io",
    }

    opp_unrelated = {
        "title": "Staff Product Manager",
        "company_name": "OtherCo",
        "source": "google_search",
        "source_url": "https://otherco.com/pm",
        "tech_required": ["Jira"],
    }

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {"opportunities": [opp_indeed, opp_linkedin, opp_unrelated]},
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    output = result["output_data"]

    assert output["total_raw"] == 3
    assert output["total_unique"] == 2
    assert output["duplicates_merged"] == 1

    merged = [o for o in output["opportunities"] if "DeepScale" in o["company_name"]][0]
    # Sources merged
    assert len(merged["all_sources"]) == 2
    assert "https://indeed.com/viewjob?jk=123" in merged["all_source_urls"]
    assert "https://linkedin.com/jobs/view/456" in merged["all_source_urls"]
    # Tech stack merged
    assert "FastAPI" in merged["tech_required"]
    assert "Docker" in merged["tech_required"]
    # Retained maximum salary
    assert merged["salary_max"] == 175000
    # Retained contact email
    assert merged["contact_email"] == "hiring@deepscale.io"


@pytest.mark.asyncio
async def test_matching_agent_weighted_rubric():
    agent = MatchingAgent()

    candidate = {
        "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
        "experience_years": 6.0,
        "remote_preference": "remote",
        "salary_min": 140000,
        "career_goals": "Architect scalable AI backend infrastructure and agent platforms.",
    }

    ideal_opp = {
        "title": "Lead Python Platform Engineer",
        "company_name": "Aether AI",
        "tech_required": ["Python", "FastAPI", "Docker", "Kubernetes"],
        "location_type": "remote",
        "salary_min": 150000,
        "salary_max": 190000,
        "description": "Architect scalable backend infrastructure for high-throughput AI agent platforms.",
    }

    weak_opp = {
        "title": "Entry Level Frontend Intern",
        "company_name": "WebShop",
        "tech_required": ["PHP", "WordPress", "jQuery"],
        "location_type": "onsite",
        "location": "Dallas, TX",
        "salary_min": 50000,
        "description": "Maintain simple content pages.",
    }

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {
            "opportunities": [weak_opp, ideal_opp],
            "candidate_profile": candidate,
        },
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    scored = result["output_data"]["opportunities"]

    assert scored[0]["company_name"] == "Aether AI"
    assert scored[0]["match_score"] >= 85
    assert "score_breakdown" in scored[0]
    assert scored[0]["score_breakdown"]["skills_match"] >= 30
    assert scored[0]["match_explanation"] != ""

    assert scored[1]["company_name"] == "WebShop"
    assert scored[1]["match_score"] < 50


@pytest.mark.asyncio
async def test_profile_analyzer_and_search_strategy():
    agent = ProfileAnalyzerAgent()

    profile = {
        "full_name": "Alex Mercer",
        "title": "Staff Backend Engineer",
        "experience_years": 8.0,
        "skills": ["Go", "Distributed Systems", "gRPC", "Kubernetes"],
        "remote_preference": "remote",
        "job_types": ["contract", "full-time"],
    }

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {"profile": profile},
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    analysis = result["output_data"]["analysis"]

    assert analysis["candidate_intelligence_profile"]["seniority_level"] == "Staff / Principal"
    assert len(analysis["search_queries"]) >= 2
    assert any("Go" in q for q in analysis["search_queries"])

    # Target sources must be sources we can actually query - never a name with no
    # adapter behind it - and company boards are skipped until the candidate
    # names companies to watch.
    registry_sources = set(ScraperRegistry().available_sources)
    assert analysis["target_sources"]
    assert set(analysis["target_sources"]).issubset(registry_sources)
    assert "greenhouse" not in analysis["target_sources"]
    assert "lever" not in analysis["target_sources"]


@pytest.mark.asyncio
async def test_follow_up_agent_cadence():
    agent = FollowUpAgent()

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {
            "outreach_id": "outreach-999",
            "contact_id": "contact-888",
            "proposal_id": "prop-777",
            "recipient_name": "Marcus Vance",
            "opportunity_title": "Staff AI Engineer",
        },
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    touches = result["output_data"]["scheduled_follow_ups"]

    assert len(touches) == 3
    assert touches[0]["sequence_step"] == 1
    assert touches[0]["delay_days"] == 3
    assert touches[1]["sequence_step"] == 2
    assert touches[1]["delay_days"] == 7
    assert touches[2]["sequence_step"] == 3
    assert touches[2]["delay_days"] == 14
    assert "Marcus" in touches[0]["body_draft"]


@pytest.mark.asyncio
async def test_rejection_recovery_agent():
    agent = RejectionRecoveryAgent()

    state = {
        "status": AgentStatus.PENDING,
        "input_data": {
            "opportunity": {
                "title": "Senior AI Engineer",
                "company_name": "ScaleDynamics",
                "industry": "Enterprise AI",
                "tech_required": ["Python", "PyTorch"],
            },
            "rejection_reason": "Position filled internally by senior candidate",
        },
    }
    result = await agent.process(state)
    assert result["status"] == AgentStatus.SUCCESS
    output = result["output_data"]

    assert output["rejection_analysis"]["category"] == "timing_position_filled"
    assert output["continuous_search_queued"] is True
    assert len(output["lookalike_queries"]) >= 1
    assert any("ScaleDynamics" in q["similar_to"] for q in output["lookalike_queries"])
    assert len(output["alternate_contact_roles"]) >= 2


@pytest.mark.asyncio
async def test_scraper_registry_multi_source():
    """Discovery fans every search term out across every real registered source."""
    registry = ScraperRegistry()

    # Only sources with an adapter behind them may be queried; a source name
    # nothing implements must be dropped rather than silently reported as used.
    assert "google_jobs" in registry.available_sources
    assert set(registry.available_sources) == set(registry.opportunity_adapters)

    calls = []

    class _StubAdapter:
        def __init__(self, source, items):
            self.source = source
            self.items = items

        async def search(self, query, filters=None):
            calls.append((self.source, query))
            return [dict(item) for item in self.items]

    # greenhouse (reliability 98) and remoteok (lower) advertise the same posting;
    # the higher-trust copy must be the one that survives deduplication.
    posting = {
        "title": "Senior Python Engineer",
        "company_name": "Aether AI",
        "source_url": "https://boards.greenhouse.io/aether/jobs/1",
    }
    registry.opportunity_adapters = {
        "greenhouse": _StubAdapter("greenhouse", [{**posting, "source": "greenhouse", "description": "Full role brief."}]),
        "remoteok": _StubAdapter("remoteok", [{**posting, "source": "remoteok", "description": ""}]),
        "google_jobs": _StubAdapter("google_jobs", [{
            "title": "Backend Engineer",
            "company_name": "Northwind",
            "source_url": "https://www.google.com/search?q=northwind",
            "source": "google_jobs",
        }]),
    }

    results = await registry.search_all(
        queries=["Python FastAPI", "Backend Engineer", "python fastapi"],
        sources=["greenhouse", "remoteok", "google_jobs", "no_such_source"],
    )

    # Two distinct terms ("python fastapi" repeats) x three known sources.
    assert len(calls) == 6
    assert {c[0] for c in calls} == {"greenhouse", "remoteok", "google_jobs"}
    assert "no_such_source" not in {c[0] for c in calls}

    assert len(results) == 2
    by_url = {r["source_url"]: r for r in results}
    assert by_url[posting["source_url"]]["source"] == "greenhouse"
    assert by_url["https://www.google.com/search?q=northwind"]["source"] == "google_jobs"


@pytest.mark.asyncio
async def test_scraper_registry_requires_search_terms():
    """No search term means no discovery - never a blind global feed."""
    registry = ScraperRegistry()
    assert await registry.search_opportunities() == []
    assert await registry.search_opportunities(queries=["  "]) == []
