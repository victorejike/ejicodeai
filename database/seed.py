"""Database seeding script for local development and demonstration."""
import asyncio
import logging
import bcrypt

from backend.app.config import get_settings
from backend.app.database import async_session, init_db
from backend.app.models import (
    AgentRun,
    Campaign,
    Company,
    CompanyResearchReport,
    Contact,
    Opportunity,
    OutreachHistory,
    Proposal,
    SearchConfig,
    Settings,
    User,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


async def seed_database() -> None:
    """Seed the database with realistic sample data."""
    await init_db()
    settings = get_settings()

    async with async_session() as session:
        # 1. Admin User
        admin_pass_hash = hash_password(settings.dev_password or "admin123")
        existing_user = await session.get(User, "00000000-0000-0000-0000-000000000001")
        if not existing_user:
            admin_user = User(
                id="00000000-0000-0000-0000-000000000001",
                email="admin@ejicode.com",
                username=settings.dev_username or "admin",
                hashed_password=admin_pass_hash,
                full_name="Ejicode Admin",
                roles=["admin", "operator"],
                is_active=True,
                is_superuser=True,
            )
            session.add(admin_user)
            logger.info("Created admin user: admin@ejicode.com")

        # 2. Settings
        default_settings = [
            (
                "company_profile",
                {
                    "name": "Ejicode",
                    "tagline": "empathy and engineering, inseparable",
                    "services": [
                        "AI Engineering",
                        "Backend Development",
                        "Full Stack",
                        "API Development",
                        "Cloud Infrastructure",
                        "Automation",
                        "Enterprise Software",
                    ],
                    "tech_stack": ["Go", "Python", "React", "Vue", "FastAPI", "PostgreSQL", "Docker"],
                    "minimum_contract_value": 2000,
                    "target_company_sizes": ["startup", "small", "mid"],
                    "preferred_locations": ["remote", "UK", "US", "UAE"],
                },
                "Ejicode company profile for proposal generation",
            ),
            (
                "outreach_limits",
                {
                    "max_emails_per_day": 50,
                    "min_send_interval_minutes": 5,
                    "follow_up_interval_days": 5,
                    "max_follow_ups": 3,
                },
                "Outreach rate limits",
            ),
        ]
        for key, val, desc in default_settings:
            existing_setting = await session.get(Settings, key)
            if not existing_setting:
                session.add(Settings(key=key, value=val, description=desc))
                logger.info(f"Created setting: {key}")

        # 3. Sample Companies
        c1_id = "11111111-1111-1111-1111-111111111111"
        c2_id = "22222222-2222-2222-2222-222222222222"
        c3_id = "33333333-3333-3333-3333-333333333333"

        if not await session.get(Company, c1_id):
            c1 = Company(
                id=c1_id,
                name="Acme Health Tech",
                domain="acmehealth.io",
                website_url="https://acmehealth.io",
                linkedin_url="https://linkedin.com/company/acmehealth",
                industry="Healthcare AI",
                company_size="51-200",
                funding_stage="Series B",
                location="San Francisco, CA (Remote)",
                description="AI-driven clinical notes and diagnosis assistant for telehealth clinicians.",
                tech_stack=["Python", "FastAPI", "PostgreSQL", "React", "AWS"],
                pain_points=["Scaling backend pipeline for high-throughput speech transcription", "HIPAA-compliant LLM deployment"],
                fit_score=94,
                fit_reasoning="Strong alignment with Ejicode's FastAPI, Python, and AI Engineering core proficiencies.",
                status="researched",
            )
            session.add(c1)

        if not await session.get(Company, c2_id):
            c2 = Company(
                id=c2_id,
                name="FinFlow Systems",
                domain="finflow.co",
                website_url="https://finflow.co",
                linkedin_url="https://linkedin.com/company/finflow-systems",
                industry="Fintech",
                company_size="11-50",
                funding_stage="Seed",
                location="London, UK (Hybrid)",
                description="Cross-border payment automation and real-time reconciliation platform.",
                tech_stack=["Go", "PostgreSQL", "Kafka", "Docker"],
                pain_points=["Need senior backend architecture consulting to support ISO 20022 standards"],
                fit_score=88,
                fit_reasoning="Ejicode has dedicated Go and fintech payments background.",
                status="contacted",
            )
            session.add(c2)

        if not await session.get(Company, c3_id):
            c3 = Company(
                id=c3_id,
                name="LogiSmart Logistics",
                domain="logismart.de",
                website_url="https://logismart.de",
                linkedin_url="https://linkedin.com/company/logismart",
                industry="Supply Chain",
                company_size="201-500",
                funding_stage="Series A",
                location="Berlin, Germany (Remote)",
                description="Predictive fleet dispatching and automated warehouse routing.",
                tech_stack=["Python", "Vue", "Docker", "Redis"],
                pain_points=["Legacy queue bottleneck during peak morning dispatches"],
                fit_score=82,
                fit_reasoning="Ejicode automation and queue orchestration experience matches warehouse demands.",
                status="discovered",
            )
            session.add(c3)

        # 4. Contacts
        ct1_id = "44444444-4444-4444-4444-444444444444"
        ct2_id = "55555555-5555-5555-5555-555555555555"

        if not await session.get(Contact, ct1_id):
            ct1 = Contact(
                id=ct1_id,
                company_id=c1_id,
                first_name="Elena",
                last_name="Rostova",
                full_name="Elena Rostova",
                email="elena@acmehealth.io",
                email_confidence="high",
                linkedin_url="https://linkedin.com/in/elena-rostova",
                title="VP of Engineering",
                role_category="engineering_leadership",
                is_decision_maker=True,
                source="linkedin_company_scout",
                notes="Leads tech scaling; previously CTO at HealthScale.",
                status="active",
            )
            session.add(ct1)

        if not await session.get(Contact, ct2_id):
            ct2 = Contact(
                id=ct2_id,
                company_id=c2_id,
                first_name="Marcus",
                last_name="Vance",
                full_name="Marcus Vance",
                email="marcus@finflow.co",
                email_confidence="verified",
                linkedin_url="https://linkedin.com/in/marcus-vance",
                title="Founder & CEO",
                role_category="executive",
                is_decision_maker=True,
                source="company_scout",
                notes="Actively hiring engineering partners for Q4 release.",
                status="active",
            )
            session.add(ct2)

        # 5. Opportunities
        op1_id = "66666666-6666-6666-6666-666666666666"
        op2_id = "77777777-7777-7777-7777-777777777777"

        if not await session.get(Opportunity, op1_id):
            op1 = Opportunity(
                id=op1_id,
                company_id=c1_id,
                title="Staff Backend / AI Engineer (Contract to Hire)",
                type="contract",
                source_platform="RemoteOK",
                source_url="https://remoteok.com/remote-jobs/acme-health-staff-backend-ai",
                raw_description="Looking for an experienced backend & AI engineer to scale our FastAPI pipelines.",
                location_type="remote",
                location="Remote - Worldwide",
                salary_min=120000,
                salary_max=160000,
                salary_currency="USD",
                tech_required=["Python", "FastAPI", "LLM", "PostgreSQL"],
                score=95,
                rank=1,
                status="researched",
            )
            session.add(op1)

        if not await session.get(Opportunity, op2_id):
            op2 = Opportunity(
                id=op2_id,
                company_id=c2_id,
                title="Senior Golang Distributed Systems Consultant",
                type="consulting",
                source_platform="LinkedIn",
                source_url="https://linkedin.com/jobs/view/finflow-senior-golang-consultant",
                raw_description="Seeking external expert to audit and optimize our ledger reconciliation microservice.",
                location_type="hybrid",
                location="London, UK",
                salary_min=100000,
                salary_max=140000,
                salary_currency="GBP",
                tech_required=["Go", "Kafka", "PostgreSQL", "Docker"],
                score=89,
                rank=2,
                status="contacted",
            )
            session.add(op2)

        # 6. Proposals
        pr1_id = "88888888-8888-8888-8888-888888888888"
        if not await session.get(Proposal, pr1_id):
            pr1 = Proposal(
                id=pr1_id,
                opportunity_id=op1_id,
                contact_id=ct1_id,
                type="cold_outreach",
                subject="Accelerating Acme Health's FastAPI & HIPAA LLM Pipeline",
                body="Hi Elena,\n\nI noticed Acme Health is scaling speech-to-text and clinical assistant pipelines. At Ejicode, we build high-throughput FastAPI systems with sub-second latency and HIPAA-compliant LLM inference.\n\nWould you be open to a brief 15-minute sync on how we helped similar healthtech teams reduce transcription lag by 40%?\n\nBest,\nVictor Ejike\nEjicode AI Engineering",
                tone="professional",
                word_count=58,
                generation_model="gemini-2.5-flash",
                status="pending_review",
            )
            session.add(pr1)

        # 7. Campaigns
        cp1_id = "99999999-9999-9999-9999-999999999999"
        if not await session.get(Campaign, cp1_id):
            cp1 = Campaign(
                id=cp1_id,
                name="Q3 HealthTech & AI Acceleration",
                description="Outreach targeting Series A/B healthtech companies hiring backend & AI engineers.",
                status="active",
                target_criteria={"min_score": 85, "industries": ["Healthcare AI", "Telehealth"]},
                schedule={"days": ["Monday", "Tuesday", "Thursday"], "send_time_utc": "14:00"},
            )
            session.add(cp1)

        # 8. Agent Runs
        ar1_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        if not await session.get(AgentRun, ar1_id):
            ar1 = AgentRun(
                id=ar1_id,
                agent_name="supervisor",
                trigger_type="daily_discovery",
                status="completed",
                duration_ms=4520,
                input_payload={"trigger_type": "daily_discovery"},
                output_summary={"companies_discovered": 12, "opportunities_scored": 18, "contacts_found": 8},
                items_processed=18,
                items_created=12,
            )
            session.add(ar1)

        # 9. Search Configs
        sc1_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        if not await session.get(SearchConfig, sc1_id):
            sc1 = SearchConfig(
                id=sc1_id,
                name="Remote Python & AI Opportunities",
                type="job_board",
                platform="RemoteOK",
                keywords=["Python", "FastAPI", "AI Engineer", "Backend"],
                filters={"remote_only": True, "min_score": 80},
                is_active=True,
                run_frequency="daily",
            )
            session.add(sc1)

        await session.commit()
        logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_database())
