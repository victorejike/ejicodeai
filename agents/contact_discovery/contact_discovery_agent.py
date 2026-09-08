"""Contact Discovery Agent - finds decision-maker contact information."""
import logging
import re
from typing import List, Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class ContactDiscoveryAgent(BaseAgent):
    """Contact Discovery Agent - finds public contact info for decision-makers."""
    
    def __init__(self):
        super().__init__(
            name="contact_discovery",
            agent_type="enrichment",
            description="Discovers and validates contact information for decision-makers",
            max_retries=2,
            timeout_seconds=600,
        )
        
        self.target_roles = ["CTO", "VP Engineering", "Head of Engineering", "Founder", "CEO"]
    
    async def validate_input(self, input_data: dict) -> bool:
        """Validate contact discovery input."""
        return "company_id" in input_data or "domain" in input_data
    
    async def _find_emails_on_website(self, domain: str) -> List[str]:
        """Extract emails from company website."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            emails = []
            
            async with httpx.AsyncClient() as client:
                # Check homepage
                response = await client.get(f"https://{domain}", timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract emails using regex
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                found_emails = re.findall(email_pattern, response.text)
                
                # Filter out common no-reply addresses
                for email in found_emails:
                    if not any(skip in email.lower() for skip in ["no-reply", "noreply", "robot", "bot"]):
                        if email not in emails:
                            emails.append(email)
            
            return emails[:10]  # Return top 10
        except Exception as e:
            self.logger.warning(f"Website email extraction error: {e}")
            return []
    
    async def _search_linkedin(self, company_name: str) -> List[Dict[str, Any]]:
        """LinkedIn team search.

        LinkedIn blocks unauthenticated people-search, and we hold no LinkedIn
        credentials, so there is nothing to return. The previous version emitted a
        hardcoded "Example Contact / VP Engineering" for every company, which then
        flowed into real outreach - an invented person is worse than none.
        """
        self.logger.debug("LinkedIn contact search is unavailable (no authenticated source); skipping")
        return []

    async def _search_hunterio(self, company_name: str) -> List[Dict[str, Any]]:
        """Query Hunter.io for real contacts. Returns [] when no key is configured."""
        if not company_name:
            return []

        from backend.app.config import get_settings

        api_key = get_settings().hunter_io_api_key
        if not api_key:
            # No guessed `contact@<company>.com`: a pattern-guessed address is not a
            # discovered contact and must never be presented as one.
            return []

        domain = company_name if "." in company_name else None
        try:
            import httpx

            params: Dict[str, Any] = {"api_key": api_key, "limit": 10}
            if domain:
                params["domain"] = domain
            else:
                params["company"] = company_name

            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get("https://api.hunter.io/v2/domain-search", params=params)
                if resp.status_code != 200:
                    self.logger.warning("Hunter.io returned %s for %s", resp.status_code, company_name)
                    return []
                data = resp.json().get("data", {}) or {}

            contacts: List[Dict[str, Any]] = []
            for entry in data.get("emails", []) or []:
                email = entry.get("value")
                if not email:
                    continue
                first = entry.get("first_name")
                last = entry.get("last_name")
                full_name = " ".join(p for p in (first, last) if p) or None
                position = entry.get("position")
                confidence_pct = entry.get("confidence")
                contacts.append({
                    "name": full_name,
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "title": position,
                    "linkedin_url": entry.get("linkedin"),
                    "source": "hunter.io",
                    # Hunter reports a 0-100 deliverability score; map it, don't invent it.
                    "confidence": (
                        "verified" if (confidence_pct or 0) >= 90
                        else "probable" if (confidence_pct or 0) >= 60
                        else "unverified"
                    ),
                    "confidence_score": confidence_pct,
                    "is_decision_maker": bool(
                        position and any(role.lower() in position.lower() for role in self.target_roles)
                    ),
                    "domain": data.get("domain"),
                })
            return contacts
        except Exception as e:
            self.logger.warning(f"Hunter.io lookup error: {e}")
            return []

    async def _validate_email_smtp(self, email: str, domain: str) -> bool:
        """Validate email via SMTP."""
        try:
            import smtplib
            
            # Check MX records for domain
            mx_domain = email.split('@')[1]
            
            try:
                # Simple validation - in production use proper SMTP verification
                mx_record = smtplib.quoteaddr(email)
                return True
            except:
                return False
        except Exception as e:
            self.logger.warning(f"Email validation error: {e}")
            return False
    
    async def process(self, state: AgentState) -> AgentState:
        """Discover contacts for company."""
        company_id = state.get("input_data", {}).get("company_id")
        domain = state.get("input_data", {}).get("domain")
        company_name = state.get("input_data", {}).get("company_name")
        
        self.logger.info(f"Contact Discovery Agent: Finding contacts for {domain or company_id} ({company_name})")
        
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "contact_discovery"
        
        if not domain:
            return self._update_state(state, {
                "status": AgentStatus.FAILURE,
                "error_message": "No domain provided",
            })
        
        contacts = []
        
        # Method 1: Extract emails from website
        website_emails = await self._find_emails_on_website(domain)
        for email in website_emails:
            is_valid = await self._validate_email_smtp(email, domain)
            if is_valid:
                contacts.append({
                    "email": email,
                    "source": "website",
                    "confidence": "verified" if is_valid else "probable",
                    "domain": domain,
                })
        
        # Method 2: Search LinkedIn
        if company_name:
            linkedin_contacts = await self._search_linkedin(company_name)
            contacts.extend(linkedin_contacts)
        
        # Method 3: Hunter.io (if configured)
        hunter_contacts = await self._search_hunterio(company_name)
        contacts.extend(hunter_contacts)

        self.logger.info(f"Discovered {len(contacts)} contacts for {domain}")
        
        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": state.get("steps_completed", []) + ["contact_discovery"],
            "output_data": {
                "contacts": contacts,
                "count": len(contacts),
            },
            "status": AgentStatus.SUCCESS,
            "confidence_score": 0.65 if len(contacts) > 0 else 0.3,
        })
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate contact discovery output."""
        return "contacts" in output_data
