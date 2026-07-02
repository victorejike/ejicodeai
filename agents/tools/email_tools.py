import logging
import re
import smtplib
from typing import Optional
from dns import resolver

logger = logging.getLogger(__name__)


class SMTPValidationTool:
    """SMTP and email pattern validation tools."""

    async def validate_syntax(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    async def verify_mx_record(self, domain: str) -> bool:
        try:
            answers = resolver.resolve(domain, "MX")
            return len(answers) > 0
        except Exception as e:
            logger.warning(f"MX lookup failed for {domain}: {e}")
            return False

    async def verify_smtp(self, email: str) -> bool:
        if not await self.validate_syntax(email):
            return False
        domain = email.split("@")[-1]
        if not await self.verify_mx_record(domain):
            return False
        try:
            with smtplib.SMTP(timeout=30) as server:
                server.connect(domain)
                return True
        except Exception as e:
            logger.warning(f"SMTP verify error for {email}: {e}")
            return False
