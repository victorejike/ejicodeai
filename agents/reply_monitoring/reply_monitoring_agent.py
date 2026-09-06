import asyncio
import email
import email.policy
import imaplib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from backend.app.config import get_settings
from agents.tools.tools import ai_service_tool

logger = logging.getLogger(__name__)
settings = get_settings()


class ReplyMonitoringAgent(BaseAgent):
    """Agent for monitoring replies and follow-up workflows."""

    def __init__(self):
        super().__init__(
            name="reply_monitoring",
            agent_type="monitoring",
            description="Polls email replies and classifies them for follow-ups.",
            max_retries=1,
            timeout_seconds=1200,
            confidence_threshold=0.7,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return True  # since=None is valid; defaults to last 7 days

    def _heuristic_classify(self, content: str) -> str:
        lower = content.lower()
        if any(w in lower for w in ["unsubscribe", "remove me", "opt out", "stop emailing", "take me off"]):
            return "UNSUBSCRIBE"
        if any(w in lower for w in ["mailer-daemon", "undeliverable", "delivery failure", "failure notice", "mailbox not found", "user unknown", "550 5."]):
            return "BOUNCE"
        if any(w in lower for w in ["out of the office", "out of office", "automatic reply", "on annual leave", "on vacation", "away from"]):
            return "AUTO_REPLY"
        if any(w in lower for w in ["not interested", "no thank", "pass on this", "not looking", "not a fit", "uninterested"]):
            return "NOT_INTERESTED"
        if any(w in lower for w in ["sounds good", "interested", "let's talk", "lets chat", "schedule a call", "set up a call", "calendly", "available tomorrow"]):
            return "INTERESTED"
        if any(w in lower for w in ["send more info", "more information", "share details", "pricing", "send deck", "case study"]):
            return "REQUEST_INFO"
        return "UNKNOWN"

    async def _classify_reply(self, content: str) -> str:
        heuristic = self._heuristic_classify(content)
        if heuristic in ["UNSUBSCRIBE", "BOUNCE", "AUTO_REPLY"]:
            return heuristic

        prompt = (
            "Classify this email reply into one of the exact categories: INTERESTED, NOT_INTERESTED, REQUEST_INFO, AUTO_REPLY, BOUNCE, UNSUBSCRIBE."
            f"\nReply content:\n{content}"
        )
        try:
            classification = await ai_service_tool.generate(prompt, system="You classify email responses. Return only the single classification keyword.")
            classification_text = classification.strip().upper()
            if "UNSUBSCRIBE" in classification_text:
                return "UNSUBSCRIBE"
            if "INTERESTED" in classification_text:
                return "INTERESTED"
            if "NOT_INTERESTED" in classification_text or "NOT INTERESTED" in classification_text:
                return "NOT_INTERESTED"
            if "REQUEST_INFO" in classification_text or "INFORMATION" in classification_text:
                return "REQUEST_INFO"
            if "AUTO_REPLY" in classification_text or "OUT OF OFFICE" in classification_text:
                return "AUTO_REPLY"
            if "BOUNCE" in classification_text or "UNDELIVERABLE" in classification_text:
                return "BOUNCE"
        except Exception as e:
            logger.warning("AI reply classification failed, using heuristic: %s", e)

        return heuristic if heuristic != "UNKNOWN" else "UNKNOWN"

    async def validate_output(self, output_data: dict) -> bool:
        return bool(output_data.get("replies", []))

    async def _extract_message_body(self, message: email.message.Message) -> str:
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and part.get_content_disposition() != "attachment":
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/html" and part.get_content_disposition() != "attachment":
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    return html
            return ""
        return message.get_payload(decode=True).decode(message.get_content_charset() or "utf-8", errors="ignore")

    async def _poll_imap(self, since: Optional[datetime]) -> List[Dict[str, Any]]:
        if not settings.imap_host or not settings.imap_user or not settings.imap_password:
            logger.warning("IMAP configuration missing; skipping reply polling")
            return []

        def _sync_poll():
            replies = []
            try:
                with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
                    client.login(settings.imap_user, settings.imap_password)
                    client.select(settings.imap_folder, readonly=True)

                    criteria = ["ALL"]
                    if since:
                        date_str = since.strftime("%d-%b-%Y")
                        criteria = ["SINCE", date_str]

                    result, data = client.search(None, *criteria)
                    if result != "OK":
                        logger.error(f"IMAP search failed: {result}")
                        return replies

                    for num in data[0].split():
                        result, msg_data = client.fetch(num, "(RFC822)")
                        if result != "OK" or not msg_data:
                            continue
                        raw = msg_data[0][1]
                        msg = email.message_from_bytes(raw, policy=email.policy.default)
                        from_header = msg.get("From")
                        subject = msg.get("Subject")
                        message_id = msg.get("Message-ID")
                        in_reply_to = msg.get("In-Reply-To") or ""
                        references = msg.get("References") or ""
                        date_header = msg.get("Date")
                        received_at = date_header if date_header else datetime.utcnow().isoformat()
                        body = ""
                        try:
                            body = self._extract_message_body(msg)
                        except Exception as e:
                            logger.error(f"Failed to extract body from IMAP message: {e}")

                        replies.append({
                            "message_id": message_id,
                            "in_reply_to": in_reply_to,
                            "references": references,
                            "from": from_header,
                            "subject": subject,
                            "received_at": received_at,
                            "content": body,
                        })
            except Exception as e:
                logger.error(f"IMAP polling error: {e}")
            return replies

        replies = await asyncio.to_thread(_sync_poll)
        return replies

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        if not await self.validate_input(input_data):
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = "Invalid input for reply monitoring"
            return state

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "poll_imap"

        since = input_data.get("since")
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        elif isinstance(since, str):
            try:
                since = datetime.fromisoformat(since)
            except ValueError:
                since = datetime.utcnow() - timedelta(days=7)

        raw_replies = await self._poll_imap(since)
        processed: List[Dict[str, Any]] = []

        for reply in raw_replies:
            classification = await self._classify_reply(reply.get("content", ""))
            processed.append({
                "message_id": reply.get("message_id"),
                "in_reply_to": reply.get("in_reply_to"),
                "references": reply.get("references"),
                "from": reply.get("from"),
                "subject": reply.get("subject"),
                "received_at": reply.get("received_at"),
                "content": reply.get("content"),
                "classification": classification,
            })

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {"replies": processed}
        state["confidence_score"] = 0.8 if processed else 0.5
        return state
