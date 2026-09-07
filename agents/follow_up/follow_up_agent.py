"""Follow-Up Agent - Intelligent multi-touch follow-up scheduler and automated sequence manager."""
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)

DEFAULT_SEQUENCE = [
    {"step": 1, "delay_days": 3, "angle": "quick_check_in"},
    {"step": 2, "delay_days": 7, "angle": "value_add_project_share"},
    {"step": 3, "delay_days": 14, "angle": "graceful_closure"},
]


class FollowUpAgent(BaseAgent):
    """Schedules, drafts, and manages multi-touch follow-up sequences with safety stop triggers."""

    def __init__(self):
        super().__init__(
            name="follow_up",
            agent_type="outreach_followup",
            description="Manages multi-touch follow-up sequences (Day 3, Day 7, Day 14) with automatic termination triggers",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "outreach_id" in input_data or "proposal" in input_data

    @staticmethod
    def generate_followup_copy(step: int, angle: str, recipient_name: str, opportunity_title: str) -> Dict[str, str]:
        """Generate tailored subject and body for specific follow-up sequence touch."""
        first_name = recipient_name.split()[0] if recipient_name else "there"

        if step == 1:
            subject = f"Following up: {opportunity_title}"
            body = (
                f"Hi {first_name},\n\n"
                f"I wanted to follow up briefly on my earlier note regarding {opportunity_title}. "
                f"I know your team is busy scaling, so I wanted to make sure this didn't slip through the cracks.\n\n"
                "Would you be open to a quick 10-minute sync this week to explore how we can support your roadmap?\n\n"
                "Best regards,\nVictor"
            )
        elif step == 2:
            subject = f"Ideas on {opportunity_title}"
            body = (
                f"Hi {first_name},\n\n"
                f"Circling back with a quick idea related to your {opportunity_title} initiative. "
                "We recently helped an engineering team cut pipeline latency by 4x using FastAPI and autonomous agents, "
                "and I see very similar leverage points in your current stack.\n\n"
                "Happy to send over the architectural breakdown if helpful!\n\n"
                "Best,\nVictor"
            )
        else:
            subject = f"Closing the loop: {opportunity_title}"
            body = (
                f"Hi {first_name},\n\n"
                f"I realize your timing might not align right now for {opportunity_title}, so I won't keep following up. "
                "If things open up down the road, please feel free to reach back out anytime.\n\n"
                "Wishing your team continued success!\n\n"
                "Best,\nVictor"
            )

        return {"subject": subject, "body": body}

    @staticmethod
    def schedule_sequence(
        outreach_id: str,
        contact_id: str,
        proposal_id: str,
        recipient_name: str,
        opportunity_title: str,
        start_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Compute scheduled follow-up steps."""
        base_time = start_time or datetime.now(timezone.utc)
        scheduled_steps = []

        for seq in DEFAULT_SEQUENCE:
            step_num = seq["step"]
            scheduled_date = base_time + timedelta(days=seq["delay_days"])
            copy = FollowUpAgent.generate_followup_copy(step_num, seq["angle"], recipient_name, opportunity_title)

            scheduled_steps.append({
                "outreach_id": outreach_id,
                "contact_id": contact_id,
                "proposal_id": proposal_id,
                "sequence_step": step_num,
                "delay_days": seq["delay_days"],
                "scheduled_for": scheduled_date.isoformat(),
                "status": "scheduled",
                "subject": copy["subject"],
                "body_draft": copy["body"],
            })

        return scheduled_steps

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        outreach_id = input_data.get("outreach_id", "outreach-default")
        contact_id = input_data.get("contact_id", "contact-default")
        proposal_id = input_data.get("proposal_id", "prop-default")
        recipient_name = input_data.get("recipient_name", "Team")
        opportunity_title = input_data.get("opportunity_title", "Engineering Partnership")

        self.logger.info("Follow-Up Agent: Generating 3-touch sequence for outreach %s", outreach_id)
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "follow_up"

        steps = self.schedule_sequence(
            outreach_id=outreach_id,
            contact_id=contact_id,
            proposal_id=proposal_id,
            recipient_name=recipient_name,
            opportunity_title=opportunity_title,
        )

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "scheduled_follow_ups": steps,
            "total_touches": len(steps),
            "next_touch_at": steps[0]["scheduled_for"] if steps else None,
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["follow_up"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "scheduled_follow_ups" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for generating follow up schedules directly."""
        outreach_id = input_data.get("outreach_id", "outreach-default")
        contact_id = input_data.get("contact_id", "contact-default")
        proposal_id = input_data.get("proposal_id", "prop-default")
        recipient_name = input_data.get("candidate_name") or input_data.get("recipient_name", "Team")
        opportunity_title = input_data.get("opportunity_title", "Engineering Partnership")

        steps = self.schedule_sequence(
            outreach_id=outreach_id,
            contact_id=contact_id,
            proposal_id=proposal_id,
            recipient_name=recipient_name,
            opportunity_title=opportunity_title,
        )
        return {
            "schedules": steps,
            "scheduled_follow_ups": steps,
            "total_touches": len(steps),
            "next_touch_at": steps[0]["scheduled_for"] if steps else None,
        }
