"""Workflow State Engine - Orchestrates sequential multi-agent execution with strict atomic state locking."""
from datetime import datetime, timezone
import logging
import secrets
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.models.core import WorkflowExecution, WorkflowStep

logger = logging.getLogger(__name__)

WORKFLOW_STAGES: List[str] = [
    "profile_analyzer",
    "discovery",
    "extraction",
    "validation",
    "deduplication",
    "research",
    "matching",
    "contact",
    "proposal",
    "approval",
    "outreach",
    "follow_up",
    "monitoring",
]


class StepLockException(Exception):
    """Raised when an agent tries to execute out of sequential order or when locked."""
    pass


class WorkflowEngine:
    """Manages sequential execution order, state transitions, distributed step locking, and persistence."""

    @staticmethod
    async def create_workflow(
        workflow_type: str = "individual_career_engine",
        input_params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        stages: Optional[List[str]] = None,
    ) -> str:
        """Initialize a new workflow execution with all sequential steps in WAITING state."""
        stages_to_run = stages or WORKFLOW_STAGES
        exec_id = str(uuid4())

        async with async_session() as session:
            wf = WorkflowExecution(
                id=exec_id,
                workflow_type=workflow_type,
                user_id=UUID(user_id) if user_id else None,
                organization_id=UUID(organization_id) if organization_id else None,
                status="pending",
                current_step=stages_to_run[0],
                lock_token=None,
                input_params=input_params or {},
                output_summary={},
                started_at=datetime.now(timezone.utc),
            )
            session.add(wf)

            for idx, stage_name in enumerate(stages_to_run):
                step = WorkflowStep(
                    id=str(uuid4()),
                    workflow_execution_id=exec_id,
                    agent_name=stage_name,
                    step_index=idx,
                    status="pending" if idx == 0 else "waiting",
                    input_data={},
                    output_data={},
                    retry_count=0,
                    max_retries=3,
                )
                session.add(step)

            await session.commit()
            logger.info("Created WorkflowExecution %s with %d stages", exec_id, len(stages_to_run))
            return exec_id

    @staticmethod
    async def acquire_step_lock(
        execution_id: str,
        agent_name: str,
    ) -> Tuple[str, str]:
        """Atomically verify previous stages completed and acquire step lock.
        Returns: (step_id, lock_token)
        Raises: StepLockException if prerequisites not satisfied or another agent holds lock.
        """
        async with async_session() as session:
            wf = await session.get(WorkflowExecution, execution_id)
            if not wf:
                raise StepLockException(f"Workflow {execution_id} does not exist.")

            if wf.status in ["failed", "cancelled", "completed"]:
                raise StepLockException(f"Workflow {execution_id} is in terminal status: {wf.status}")

            # Query all steps ordered by step_index
            stmt = select(WorkflowStep).where(
                WorkflowStep.workflow_execution_id == execution_id
            ).order_by(WorkflowStep.step_index)
            res = await session.execute(stmt)
            steps = res.scalars().all()

            target_step = None
            target_idx = -1
            for s in steps:
                if s.agent_name == agent_name:
                    target_step = s
                    target_idx = s.step_index
                    break

            if not target_step:
                raise StepLockException(f"Agent {agent_name} is not part of workflow {execution_id}.")

            # 1. Enforce strict sequential order: all prior steps must be "completed"
            for s in steps:
                if s.step_index < target_idx:
                    if s.status != "completed":
                        target_step.status = "waiting"
                        await session.commit()
                        raise StepLockException(
                            f"Cannot run {agent_name}: previous stage {s.agent_name} has status '{s.status}'."
                        )

            # 2. Check if already running or completed
            if target_step.status == "completed":
                raise StepLockException(f"Stage {agent_name} already completed.")

            # 3. Acquire lock
            lock_token = secrets.token_hex(16)
            target_step.status = "running"
            target_step.started_at = datetime.now(timezone.utc)

            wf.status = "running"
            wf.current_step = agent_name
            wf.lock_token = lock_token

            await session.commit()
            logger.info("Agent %s acquired step lock for workflow %s", agent_name, execution_id)
            return str(target_step.id), lock_token

    @staticmethod
    async def complete_step(
        execution_id: str,
        agent_name: str,
        output_data: Dict[str, Any],
        execution_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Mark step as completed, save outputs, and unlock execution."""
        async with async_session() as session:
            wf = await session.get(WorkflowExecution, execution_id)
            if not wf:
                return

            stmt = select(WorkflowStep).where(
                and_(
                    WorkflowStep.workflow_execution_id == execution_id,
                    WorkflowStep.agent_name == agent_name,
                )
            )
            res = await session.execute(stmt)
            step = res.scalars().first()

            if step:
                step.status = "completed"
                step.output_data = output_data
                step.completed_at = datetime.now(timezone.utc)
                if execution_logs:
                    step.execution_logs = execution_logs

            # Forward output into next step input if next step exists
            next_step_stmt = select(WorkflowStep).where(
                and_(
                    WorkflowStep.workflow_execution_id == execution_id,
                    WorkflowStep.step_index == (step.step_index + 1 if step else -1),
                )
            )
            next_res = await session.execute(next_step_stmt)
            next_step = next_res.scalars().first()

            if next_step:
                next_step.status = "pending"
                next_step.input_data = output_data
                wf.current_step = next_step.agent_name
            else:
                # All steps completed!
                wf.status = "completed"
                wf.completed_at = datetime.now(timezone.utc)
                wf.current_step = "completed"

            wf.lock_token = None
            await session.commit()
            logger.info("Stage %s completed for workflow %s", agent_name, execution_id)

    @staticmethod
    async def fail_step(
        execution_id: str,
        agent_name: str,
        error_message: str,
    ) -> bool:
        """Handle step failure with retry policy. Returns True if retrying, False if marked failed."""
        async with async_session() as session:
            wf = await session.get(WorkflowExecution, execution_id)
            stmt = select(WorkflowStep).where(
                and_(
                    WorkflowStep.workflow_execution_id == execution_id,
                    WorkflowStep.agent_name == agent_name,
                )
            )
            res = await session.execute(stmt)
            step = res.scalars().first()

            if not step:
                return False

            step.error_message = error_message
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = "retrying"
                if wf:
                    wf.status = "retrying"
                    wf.lock_token = None
                await session.commit()
                logger.warning("Stage %s failing, retry %d/%d scheduled", agent_name, step.retry_count, step.max_retries)
                return True
            else:
                step.status = "failed"
                step.completed_at = datetime.now(timezone.utc)
                if wf:
                    wf.status = "failed"
                    wf.error_message = f"Failed at {agent_name}: {error_message}"
                    wf.completed_at = datetime.now(timezone.utc)
                    wf.lock_token = None
                await session.commit()
                logger.error("Stage %s failed permanently: %s", agent_name, error_message)
                return False

    @staticmethod
    async def get_workflow_status(execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full workflow status, current step, and step breakdown."""
        async with async_session() as session:
            wf = await session.get(WorkflowExecution, execution_id)
            if not wf:
                return None

            stmt = select(WorkflowStep).where(
                WorkflowStep.workflow_execution_id == execution_id
            ).order_by(WorkflowStep.step_index)
            res = await session.execute(stmt)
            steps = res.scalars().all()

            return {
                "id": str(wf.id),
                "workflow_type": wf.workflow_type,
                "status": wf.status,
                "current_step": wf.current_step,
                "error_message": wf.error_message,
                "started_at": wf.started_at.isoformat() if wf.started_at else None,
                "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
                "steps": [
                    {
                        "agent_name": s.agent_name,
                        "step_index": s.step_index,
                        "status": s.status,
                        "retry_count": s.retry_count,
                        "output_summary": list(s.output_data.keys()) if isinstance(s.output_data, dict) else None,
                        "error_message": s.error_message,
                    }
                    for s in steps
                ],
            }
