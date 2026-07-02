from agents.outreach.outreach_agent import OutreachAgent
from agents.base.base_agent import AgentStatus


class FakeSMTP:
    def __init__(self, *args, **kwargs):
        raise OSError("smtp unavailable")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_outreach_agent_falls_back_to_queued_delivery_when_smtp_is_unavailable(monkeypatch):
    monkeypatch.setattr("agents.outreach.outreach_agent.smtplib.SMTP", FakeSMTP)

    agent = OutreachAgent()
    state = {
        "status": AgentStatus.PENDING,
        "input_data": {
            "proposal": {
                "proposal_id": "proposal-123",
                "subject": "Hello",
                "body": "Hello there",
            },
            "contact": {
                "id": "contact-123",
                "email": "person@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "title": "CTO",
            },
            "opportunity_id": "opportunity-123",
        },
        "output_data": {},
        "messages": [],
        "current_step": "initialization",
        "steps_completed": [],
        "error_count": 0,
        "confidence_score": 1.0,
        "quality_checks_passed": True,
    }

    result = __import__("asyncio").run(agent.process(state))

    assert result["status"] == AgentStatus.SUCCESS
    assert result["output_data"]["delivery_status"] == "queued"
    assert result["output_data"]["message_id"].startswith("queued-")
