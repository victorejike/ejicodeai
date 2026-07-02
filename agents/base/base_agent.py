"""Base agent class and state management for LangGraph."""
from typing import TypedDict, Optional, Any, List
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
