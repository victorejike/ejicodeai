"""Unit tests for EJICODE AI Individual AI Career Agent and Multi-Source Engine."""
import pytest
from agents.validation.validation_agent import ValidationAgent
from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.deduplication.deduplication_agent import DeduplicationAgent, get_source_priority
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.rejection.rejection_recovery_agent import RejectionRecoveryAgent


class TestValidationAndAntiScam:
    def test_source_reliability_scoring(self):
        val = ValidationAgent()
        assert val.calculate_source_reliability("greenhouse") == 98
        assert val.calculate_source_reliability("company_websites") == 98
        assert val.calculate_source_reliability("linkedin") == 90
        assert val.calculate_source_reliability("upwork") == 88
        assert val.calculate_source_reliability("reddit") == 65

    def test_anti_scam_detection_safe(self):
        val = ValidationAgent()
        item = {
            "title": "Senior Backend Engineer",
            "company_name": "ScaleVector Inc",
            "company_domain": "scalevector.com",
            "company_url": "https://scalevector.com",
            "description": "ScaleVector is expanding core backend teams with expertise in Python.",
            "contact_email": "careers@scalevector.com",
            "salary_min": 140000,
            "salary_max": 180000,
        }
        res = val.detect_anti_scam_flags(item)
        assert res["safety_status"] == "SAFE"
        assert res["verification_confidence"] >= 90
        assert len(res["scam_flags"]) == 0

    def test_anti_scam_detection_high_risk(self):
        val = ValidationAgent()
        item = {
            "title": "Data Entry Specialist",
            "company_name": "Unknown",
            "description": "Please wire transfer application fee or buy gift cards for home office setup.",
            "contact_email": "recruiter129@gmail.com",
            "salary_min": 200000,
            "salary_max": 600000,
        }
        res = val.detect_anti_scam_flags(item)
        assert res["safety_status"] in ["HIGH RISK", "REJECTED"]
        assert res["verification_confidence"] < 50
        assert len(res["scam_flags"]) >= 1


class TestProfileAnalyzerAndTransferableSkills:
    def test_transferable_role_mapping(self):
        roles = ProfileAnalyzerAgent.map_transferable_roles("Software Engineer")
        assert "Backend Engineer" in roles
        assert "Full Stack Engineer" in roles
        assert "AI Engineer" in roles
        assert "Python Developer" in roles

    def test_candidate_intelligence_profile_build(self):
        agent = ProfileAnalyzerAgent()
        raw = {
            "full_name": "Victor Ejike",
            "title": "Software Engineer",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
            "experience_years": 5.0,
            "salary_min": 130000,
            "salary_max": 190000,
        }
        intel = agent.build_candidate_intelligence_profile(raw)
        assert intel["seniority_level"] == "Senior"
        assert "Python" in intel["skills"]
        assert len(intel["transferable_roles"]) >= 4
        assert intel["availability"] == "Immediately"


class TestProposalGenerationSelfMarketing:
    @pytest.mark.asyncio
    async def test_generate_self_marketing_materials(self):
        agent = ProposalGenerationAgent()
        candidate = {
            "full_name": "Victor Ejike",
            "title": "Full Stack AI Engineer",
            "skills": ["Python", "FastAPI", "React", "PyTorch"],
            "experience_years": 4.0,
        }
        materials = await agent.generate_self_marketing_materials(
            candidate_profile=candidate,
            opportunity={"title": "Lead Backend Engineer", "company_name": "Nova Labs"},
        )
        assert materials["truthfulness_verified"] is True
        assert "Victor Ejike" in materials["bios"]["short"]
        assert "Nova Labs" in materials["cover_letter"]
        assert "freelance_proposal" in materials
        assert "day_3" in materials["follow_up_cadence"]
        assert "day_7" in materials["follow_up_cadence"]
        assert "day_14" in materials["follow_up_cadence"]


class TestDeduplicationSourcePriority:
    def test_source_priority_ranking(self):
        assert get_source_priority("greenhouse") > get_source_priority("linkedin")
        assert get_source_priority("linkedin") > get_source_priority("upwork")
        assert get_source_priority("upwork") > get_source_priority("reddit")

    def test_merge_records_respects_priority(self):
        high_prio = {
            "source": "greenhouse",
            "source_url": "https://boards.greenhouse.io/nova/jobs/1",
            "title": "Senior Python Engineer",
            "company_name": "Nova Labs",
            "salary_min": 140000,
        }
        lower_prio = {
            "source": "reddit",
            "source_url": "https://reddit.com/r/forhire/comments/xyz/python",
            "title": "[Hiring] Python Engineer",
            "company_name": "Nova Labs",
            "salary_max": 180000,
        }
        merged = DeduplicationAgent.merge_records(lower_prio, high_prio)
        assert merged["source"] == "greenhouse"
        assert len(merged["all_sources"]) == 2
        assert merged["salary_min"] == 140000
        assert merged["salary_max"] == 180000


class TestCompanyFirstDiscovery:
    def test_approach_potential_evaluation(self):
        scout = CompanyScoutAgent()
        company = {
            "name": "Kinetix AI",
            "domain": "kinetix.ai",
            "industry": "Artificial Intelligence",
            "tech_stack": ["Python", "PyTorch", "FastAPI"],
        }
        user_skills = ["Python", "FastAPI", "React"]
        eval_result = scout.evaluate_approach_potential(company, user_skills)
        assert eval_result["approach_score"] >= 80
        assert "Kinetix AI" in eval_result["approach_reason"]
        assert eval_result["pipeline_type"] == "proactive_approach"


class TestRejectionRecoveryIntelligence:
    def test_rejection_categorization(self):
        agent = RejectionRecoveryAgent()
        res1 = agent.analyze_rejection_reason("The role was filled internally by our team.")
        assert res1["category"] == "timing_position_filled"

        res2 = agent.analyze_rejection_reason("Candidate lacks required years of experience.")
        assert res2["category"] == "seniority_mismatch"

        res3 = agent.analyze_rejection_reason("We use Go instead of Python for our backend services.")
        assert res3["category"] == "tech_stack_mismatch"
