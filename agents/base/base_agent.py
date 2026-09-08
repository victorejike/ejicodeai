"""Base agent class and state management for LangGraph."""
import time
from typing import TypedDict, Optional, Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATED = "escalated"


class AgentState(TypedDict, total=False):
    """LangGraph agent state dictionary."""
    # Execution metadata
    run_id: str
    agent_name: str
    status: AgentStatus
    timestamp: str

    # Input/Output
    input_data: dict
    output_data: dict

    # Processing
    messages: List[dict]
    current_step: str
    steps_completed: List[str]

    # Context
    company_data: Optional[dict]
    opportunity_data: Optional[dict]
    contact_data: Optional[dict]

    # Ownership / pipeline position. Set by the orchestrator so every agent can
    # attribute its work to the right user and report where it sits in the chain.
    user_id: Optional[str]
    organization_id: Optional[str]
    workflow_execution_id: Optional[str]
    stage: Optional[str]
    stage_index: Optional[int]
    stage_total: Optional[int]

    # Errors and escalation
    error_message: Optional[str]
    error_count: int
    escalation_reason: Optional[str]

    # Confidence and quality
    confidence_score: float
    quality_checks_passed: bool

    # Sub-agent tracking
    sub_agent_results: dict
    dependencies_resolved: bool


@dataclass
class BaseAgent:
    """Base agent class for all agents in the system."""
    
    name: str
    agent_type: str
    description: str
    max_retries: int = 3
    timeout_seconds: int = 600
    confidence_threshold: float = 0.65
    
    def __post_init__(self):
        """Initialize agent."""
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for agent."""
        import logging
        return logging.getLogger(f"agents.{self.name}")
    
    async def validate_input(self, input_data: dict) -> bool:
        """Validate input data."""
        raise NotImplementedError
    
    async def process(self, state: AgentState) -> AgentState:
        """Process agent task - to be implemented by subclasses."""
        raise NotImplementedError
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate output data."""
        raise NotImplementedError
    
    def _update_state(self, state: AgentState, updates: dict) -> AgentState:
        """Update agent state."""
        return {**state, **updates}

    # ------------------------------------------------------------------
    # Real-time reporting
    # ------------------------------------------------------------------

    @staticmethod
    def _describe_volume(data: Optional[dict]) -> Dict[str, int]:
        """Count the list-valued keys of a payload, e.g. {"opportunities": 42}.

        This is what makes a hand-off auditable from the event feed alone: you can
        see 60 opportunities go into validation and 47 come out.
        """
        if not isinstance(data, dict):
            return {}
        return {k: len(v) for k, v in data.items() if isinstance(v, list)}

    async def emit(
        self,
        state: AgentState,
        event_type: str,
        message: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> None:
        """Publish a live event attributed to this agent and the state's owner."""
        from agents.base.agent_events import emit as emit_event

        body = {"agent": self.name}
        if state.get("stage"):
            body["stage"] = state["stage"]
        if state.get("stage_index") is not None:
            body["stage_index"] = state["stage_index"]
        if state.get("stage_total") is not None:
            body["stage_total"] = state["stage_total"]
        if payload:
            body.update(payload)

        await emit_event(
            event_type,
            message,
            payload=body,
            severity=severity,
            user_id=state.get("user_id"),
            organization_id=state.get("organization_id"),
        )

    async def run(self, state: AgentState) -> AgentState:
        """Run `process` with start/finish/failure events around it.

        Orchestrators should call this rather than `process` directly so every
        agent becomes visible in the live feed without each one re-implementing
        its own telemetry. `process` stays the pure unit of work.
        """
        input_data = state.get("input_data") or {}
        started = time.monotonic()

        await self.emit(
            state,
            "agent.started",
            f"{self.description or self.name} started",
            payload={"received": self._describe_volume(input_data)},
        )

        try:
            result = await self.process(state)
        except Exception as exc:
            await self.emit(
                state,
                "agent.failed",
                f"{self.name} failed: {exc}",
                severity="error",
                payload={"error": str(exc), "duration_ms": int((time.monotonic() - started) * 1000)},
            )
            raise

        output_data = (result or {}).get("output_data") or {}
        status = (result or {}).get("status")
        failed = status in (AgentStatus.FAILURE, AgentStatus.ESCALATED)

        await self.emit(
            state,
            "agent.failed" if failed else "agent.completed",
            (result or {}).get("error_message") or f"{self.name} finished",
            severity="error" if failed else "success",
            payload={
                "produced": self._describe_volume(output_data),
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        return result


class SupervisorAgent(BaseAgent):
    """Supervisor agent for orchestrating all other agents."""
    
    def __init__(self):
        super().__init__(
            name="supervisor",
            agent_type="coordinator",
            description="Central coordinator for multi-agent system",
        )
    
    async def validate_input(self, input_data: dict) -> bool:
        """Validate supervisor input."""
        required_fields = ["trigger_type", "payload"]
        return all(field in input_data for field in required_fields)
    
    async def process(self, state: AgentState) -> AgentState:
        """Coordinate all agents."""
        state["status"] = AgentStatus.SUCCESS
        state["current_step"] = state.get("current_step", "processed")
        return state
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate supervisor output."""
        return "results" in output_data and "status" in output_data
