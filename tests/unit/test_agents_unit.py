"""Unit tests for individual agents and tools."""
import pytest
from unittest.mock import AsyncMock, patch

from agents.base.base_agent import AgentStatus
from agents.ranking.ranking_agent import RankingAgent
from agents.knowledge_base.knowledge_base_agent import KnowledgeBaseAgent
from agents.research.research_agent import ResearchAgent
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.tools.tools import email_tool


class TestRankingAgent:
    @pytest.mark.asyncio
    async def test_validate_input(self):
        agent = RankingAgent()
        assert await agent.validate_input({"opportunities": []}) is True
        assert await agent.validate_input({"something_else": 123}) is False

    def test_tech_match_scoring(self):
        agent = RankingAgent()
        # Technology fit is measured against the candidate's own declared skills,
        # not against a fixed idea of a "good" stack.
        agent.load_candidate({"skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]})

        # High match
        opp_high = {"tech_required": ["Python", "FastAPI", "Docker", "PostgreSQL"]}
        score_high = agent._score_tech_match(opp_high)
        assert score_high >= 20

        # Zero match
        opp_zero = {"tech_required": ["COBOL", "Fortran", "Pascal"]}
        score_zero = agent._score_tech_match(opp_zero)
        assert score_zero == 0

    def test_tech_match_without_candidate_skills_scores_zero(self):
        """With no skills on file there is no basis to award technology points."""
        agent = RankingAgent()
        assert agent._score_tech_match({"tech_required": ["Python", "FastAPI"]}) == 0

    def test_tech_match_differs_per_candidate(self):
        """Two candidates must not receive the same technology score for one job."""
        opportunity = {"tech_required": ["Python", "Django", "PostgreSQL", "Celery"]}

        backend = RankingAgent()
        backend.load_candidate({"skills": ["Python", "Django", "PostgreSQL", "Celery"]})

        designer = RankingAgent()
        designer.load_candidate({"skills": ["Figma", "UX Research", "Design Systems"]})

        assert backend._score_tech_match(opportunity) > designer._score_tech_match(opportunity)

    def test_compensation_scored_against_candidate_expectation(self):
        agent = RankingAgent()
        agent.load_candidate({"salary_min": 150000})
        assert agent._score_compensation({"salary_max": 180000}) == 15
        assert agent._score_compensation({"salary_max": 90000}) == 2
        # Undisclosed pay is a weak signal regardless of expectation.
        assert agent._score_compensation({}) == 3

    def test_company_fit_scoring(self):
        agent = RankingAgent()
        comp_tech = {"company_size": "startup", "funding_stage": "series_a"}
        score = agent._score_company_fit(comp_tech)
        assert score > 0

    @pytest.mark.asyncio
    async def test_ranking_process(self):
        agent = RankingAgent()
        state = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "opportunities": [
                    {
                        "id": "opp-1",
                        "title": "Legacy COBOL Developer",
                        "tech_required": ["COBOL"],
                        "company_id": "c1",
                    },
                    {
                        "id": "opp-2",
                        "title": "Senior AI / FastAPI Engineer",
                        "tech_required": ["Python", "FastAPI", "AI", "PostgreSQL"],
                        "company_id": "c2",
                    },
                ],
                "companies": {
                    "c1": {"company_size": "enterprise"},
                    "c2": {"company_size": "startup", "funding_stage": "series_a"},
                },
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
            "quality_checks_passed": True,
        }

        result = await agent.process(state)
        assert result["status"] == AgentStatus.SUCCESS
        ranked = result["output_data"]["opportunities"]
        assert len(ranked) == 2
        # Highest score should be ranked first
        assert ranked[0]["id"] == "opp-2"
        assert ranked[0]["rank"] == 1
        assert ranked[1]["id"] == "opp-1"
        assert ranked[1]["rank"] == 2


class TestKnowledgeBaseAgent:
    @pytest.mark.asyncio
    async def test_kb_sync_and_retrieve(self):
        agent = KnowledgeBaseAgent()
        # Test sync
        state_sync = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "operation": "sync",
                "documents": [
                    {"content": "Ejicode builds autonomous AI business development platforms.", "metadata": {"topic": "overview"}},
                ],
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
            "quality_checks_passed": True,
        }
        res_sync = await agent.process(state_sync)
        assert res_sync["status"] == AgentStatus.SUCCESS
        assert res_sync["output_data"]["stored_documents"] >= 1

        # Test retrieve
        state_retrieve = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "operation": "retrieve",
                "collection": "proposals",
                "query": "autonomous AI business development",
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
            "quality_checks_passed": True,
        }
        res_retrieve = await agent.process(state_retrieve)
        assert res_retrieve["status"] == AgentStatus.SUCCESS
        assert "results" in res_retrieve["output_data"]


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_validate_input(self):
        agent = ResearchAgent()
        assert await agent.validate_input({"domain": "example.com"}) is True
        assert await agent.validate_input({"company_id": "123"}) is True
        assert await agent.validate_input({}) is False

    @pytest.mark.asyncio
    async def test_research_process_with_mock(self):
        agent = ResearchAgent()
        with patch.object(
            agent,
            "_scrape_website",
            new_callable=AsyncMock,
            return_value={
                "homepage": "We build cloud-native SaaS for enterprises.",
                "about": "Founded in 2020.",
                "services": ["Cloud Migration", "AI Solutions"],
                "tech_indicators": ["Kubernetes", "Python"],
                "team_size_estimate": 45,
            },
        ), patch.object(
            agent,
            "_detect_tech_stack",
            new_callable=AsyncMock,
            return_value={"detected_tech": ["Python", "Kubernetes"]},
        ), patch.object(
            agent,
            "_analyze_with_llm",
            new_callable=AsyncMock,
            return_value={"ai_opportunity_score": 88, "summary": "Great match"},
        ):
            state = {
                "status": AgentStatus.PENDING,
                "input_data": {"domain": "cloudsaas.io"},
                "output_data": {},
                "messages": [],
                "current_step": "initialization",
                "steps_completed": [],
                "error_count": 0,
                "confidence_score": 1.0,
                "quality_checks_passed": True,
            }
            result = await agent.process(state)
            assert result["status"] == AgentStatus.SUCCESS
            out = result["output_data"]
            assert out["domain"] == "cloudsaas.io"
            assert out["analysis"]["ai_opportunity_score"] == 88


class TestContactDiscoveryAgent:
    @pytest.mark.asyncio
    async def test_validate_input(self):
        agent = ContactDiscoveryAgent()
        assert await agent.validate_input({"domain": "example.com"}) is True
        assert await agent.validate_input({"company_id": "123"}) is True
        assert await agent.validate_input({}) is False


class TestEmailTool:
    @pytest.mark.asyncio
    async def test_validate_syntax(self):
        assert await email_tool.validate_syntax("valid.user@example.com") is True
        assert await email_tool.validate_syntax("user+tag@domain.co.uk") is True
        assert await email_tool.validate_syntax("invalid-email") is False
        assert await email_tool.validate_syntax("@missingusername.com") is False
        assert await email_tool.validate_syntax("spaces in@email.com") is False
