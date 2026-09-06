"""Test supervisor agent state preservation and workflow execution."""
import pytest
from unittest.mock import AsyncMock, patch
from agents.base.base_agent import AgentStatus
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor.graph import build_supervisor_graph


@pytest.mark.asyncio
async def test_supervisor_preserves_opportunities_across_agents():
    supervisor = SupervisorAgent()

    mock_job_opps = [
        {"title": "Staff Python Engineer", "company": "TestCorp", "score": 90, "source_url": "https://test.com/job1"},
        {"title": "Senior FastAPI Dev", "company": "DevInc", "score": 85, "source_url": "https://test.com/job2"},
    ]
    mock_companies = [
        {"name": "TestCorp", "domain": "testcorp.com", "industry": "AI"},
    ]

    with patch.object(supervisor.job_scout, "process", new_callable=AsyncMock) as mock_js, \
         patch.object(supervisor.company_scout, "process", new_callable=AsyncMock) as mock_cs, \
         patch.object(supervisor.ranking, "process", new_callable=AsyncMock) as mock_rk, \
         patch.object(supervisor.research, "process", new_callable=AsyncMock) as mock_rs, \
         patch.object(supervisor.contact_discovery, "process", new_callable=AsyncMock) as mock_cd:

        mock_js.return_value = {
            "status": AgentStatus.SUCCESS,
            "output_data": {"opportunities": mock_job_opps},
        }
        mock_cs.return_value = {
            "status": AgentStatus.SUCCESS,
            "output_data": {"companies": mock_companies},
        }
        mock_rk.return_value = {
            "status": AgentStatus.SUCCESS,
            "output_data": {"opportunities": mock_job_opps},
        }
        mock_rs.return_value = {
            "status": AgentStatus.SUCCESS,
            "output_data": {"summary": "Great fit", "fit_score": 92},
        }
        mock_cd.return_value = {
            "status": AgentStatus.SUCCESS,
            "output_data": {"contacts": [{"email": "tech@testcorp.com", "title": "CTO"}]},
        }

        initial_state = {
            "status": AgentStatus.PENDING,
            "input_data": {"trigger_type": "daily_discovery"},
            "output_data": {},
        }

        result = await supervisor.process(initial_state)

        # Verify supervisor succeeded
        assert result["status"] == AgentStatus.SUCCESS
        output = result["output_data"]
        assert output["opportunities_discovered"] == 2
        assert output["companies_discovered"] == 1

        # Verify ranking received the job scout opportunities despite company scout running in between
        ranking_call_state = mock_rk.call_args[0][0]
        assert len(ranking_call_state["input_data"]["opportunities"]) == 2
