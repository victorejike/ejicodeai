"""Unit tests for WorkflowEngine sequential state locking and error recovery."""
import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from backend.app.models.core import Base, WorkflowExecution, WorkflowStep
from agents.supervisor.workflow_engine import WorkflowEngine, StepLockException


@pytest.fixture
async def test_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_workflow_sequential_locking(test_session_factory):
    with patch("agents.supervisor.workflow_engine.async_session", test_session_factory):
        # 1. Create a 3-step workflow
        exec_id = await WorkflowEngine.create_workflow(
            workflow_type="individual_career_engine",
            input_params={"target": "staff engineer"},
            stages=["profile_analyzer", "discovery", "extraction"],
        )
        assert exec_id is not None

        # 2. Stage 2 (discovery) should NOT be able to run before Stage 1 (profile_analyzer) completes
        with pytest.raises(StepLockException) as exc_info:
            await WorkflowEngine.acquire_step_lock(exec_id, "discovery")
        assert "previous stage profile_analyzer has status 'pending'" in str(exc_info.value)

        # 3. Stage 1 acquires lock
        step1_id, lock_token = await WorkflowEngine.acquire_step_lock(exec_id, "profile_analyzer")
        assert lock_token is not None

        # Verify DB state
        status_info = await WorkflowEngine.get_workflow_status(exec_id)
        assert status_info["status"] == "running"
        assert status_info["steps"][0]["status"] == "running"
        assert status_info["steps"][1]["status"] == "waiting"

        # 4. Stage 1 completes
        await WorkflowEngine.complete_step(
            exec_id,
            "profile_analyzer",
            output_data={"skills": ["Python", "Go"], "niche": "Distributed Systems"},
        )

        # 5. Now Stage 2 can acquire lock
        step2_id, lock_token2 = await WorkflowEngine.acquire_step_lock(exec_id, "discovery")
        assert lock_token2 is not None

        # Verify Stage 2 received forwarded output from Stage 1
        async with test_session_factory() as session:
            step2 = await session.get(WorkflowStep, step2_id)
            assert step2.input_data == {"skills": ["Python", "Go"], "niche": "Distributed Systems"}

        # 6. Complete remaining steps
        await WorkflowEngine.complete_step(exec_id, "discovery", output_data={"opps": 5})
        await WorkflowEngine.acquire_step_lock(exec_id, "extraction")
        await WorkflowEngine.complete_step(exec_id, "extraction", output_data={"extracted": 5})

        # Verify workflow is fully completed
        final_status = await WorkflowEngine.get_workflow_status(exec_id)
        assert final_status["status"] == "completed"
        assert final_status["current_step"] == "completed"


@pytest.mark.asyncio
async def test_workflow_retry_and_terminal_failure(test_session_factory):
    with patch("agents.supervisor.workflow_engine.async_session", test_session_factory):
        exec_id = await WorkflowEngine.create_workflow(
            workflow_type="individual_career_engine",
            stages=["discovery"],
        )

        await WorkflowEngine.acquire_step_lock(exec_id, "discovery")

        # Retry 1
        retrying = await WorkflowEngine.fail_step(exec_id, "discovery", "HTTP 503")
        assert retrying is True

        # Retry 2
        retrying = await WorkflowEngine.fail_step(exec_id, "discovery", "HTTP 503")
        assert retrying is True

        # Retry 3
        retrying = await WorkflowEngine.fail_step(exec_id, "discovery", "HTTP 503")
        assert retrying is True

        # Retry 4 exceeds max_retries (3) -> permanent failure
        retrying = await WorkflowEngine.fail_step(exec_id, "discovery", "Permanent DNS failure")
        assert retrying is False

        status = await WorkflowEngine.get_workflow_status(exec_id)
        assert status["status"] == "failed"
        assert "Failed at discovery" in status["error_message"]
