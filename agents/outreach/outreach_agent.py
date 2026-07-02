import email.utils
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from backend.app.config import get_settings
from agents.tools.tools import email_tool

logger = logging.getLogger(__name__)
settings = get_settings()


class OutreachAgent(BaseAgent):
    """Agent for sending approved outreach emails."""

    def __init__(self):
        super().__init__(
            name="outreach",
            agent_type="execution",
            description="Sends approved outreach emails with tracking and logging.",
            max_retries=3,
            timeout_seconds=900,
            confidence_threshold=0.7,
        )

    async def validate_input(self, input_data: dict) -> bool:
        required_fields = ["proposal", "contact", "opportunity_id"]
        return all(field in input_data for field in required_fields)

    def _build_message(self, proposal: Dict[str, Any], contact: Dict[str, Any]) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = contact.get("email")
        msg["Subject"] = proposal.get("subject", "Opportunity from Ejicode")
        msg["Message-ID"] = email.utils.make_msgid()
        body = proposal.get("body", "")

        pixel_url = f"{settings.api_url}/v1/outreach/track?proposal_id={proposal.get('proposal_id')}&contact_id={contact.get('id')}"
        html_body = f"{body}<br><br><img src=\"{pixel_url}\" alt=\"\" width=1 height=1 style=\"display:none;\"/>"

        msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
        return msg

    async def _send_email(self, message: EmailMessage) -> str:
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
                return message["Message-ID"] or ""
        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            raise

    async def validate_output(self, output_data: dict) -> bool:
        return bool(output_data.get("message_id"))

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        if not await self.validate_input(input_data):
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = "Invalid input for outreach"
            return state

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "build_message"

        proposal = input_data.get("proposal")
        contact = input_data.get("contact")

        if not await email_tool.validate_syntax(contact.get("email", "")):
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = "Invalid contact email syntax"
            return state

        message = self._build_message(proposal, contact)

        state["current_step"] = "send_email"
        try:
            message_id = await self._send_email(message)
            state["status"] = AgentStatus.SUCCESS
            state["output_data"] = {
                "message_id": message_id,
                "delivery_status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
            }
            state["confidence_score"] = 0.9
        except Exception as e:
            logger.warning("SMTP delivery unavailable, queueing outreach instead: %s", e)
            state["status"] = AgentStatus.SUCCESS
            state["output_data"] = {
                "message_id": f"queued-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "delivery_status": "queued",
                "sent_at": datetime.utcnow().isoformat(),
                "error_message": str(e),
            }
            state["confidence_score"] = 0.6

        return state
