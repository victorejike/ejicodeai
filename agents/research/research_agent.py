"""Research Agent - performs deep research on companies."""
import logging
from typing import Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Research Agent - analyzes companies and extracts intelligence."""
    
    def __init__(self):
        super().__init__(
            name="research",
            agent_type="analysis",
            description="Performs deep research on companies and extracts intelligence",
            max_retries=2,
            timeout_seconds=900,
        )
    
    async def validate_input(self, input_data: dict) -> bool:
        """Validate research input."""
        return "company_id" in input_data or "domain" in input_data
    
    async def _scrape_website(self, domain: str) -> Dict[str, Any]:
        """Scrape and analyze company website."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            website_data = {
                "homepage": "",
                "about": "",
                "services": [],
                "tech_indicators": [],
                "team_size_estimate": 0,
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"https://{domain}", timeout=10)
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extract basic info
                    website_data["homepage"] = response.text[:1000]
                    
                    # Extract service descriptions from common sections
                    for tag in soup.find_all(['h1', 'h2', 'p']):
                        text = tag.get_text()
                        if len(text) > 20 and len(text) < 500:
                            website_data["services"].append(text)
                    
                except Exception as e:
                    self.logger.warning(f"Website scrape error for {domain}: {e}")
            
            return website_data
        except Exception as e:
            self.logger.error(f"Website analysis error: {e}")
            return {}
    
    async def _detect_tech_stack(self, domain: str) -> Dict[str, Any]:
        """Detect tech stack indicators from HTTP headers and HTML."""
        try:
            import httpx
            from agents.tools.tools import extraction_tool

            tech_indicators: Dict[str, Any] = {
                "frameworks": [],
                "languages": [],
                "platforms": [],
                "confidence": 0.5,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://{domain}", timeout=10, follow_redirects=True)
                headers = dict(response.headers)
                html = response.text

            # Header-based detection
            server = headers.get("server", "").lower()
            x_powered = headers.get("x-powered-by", "").lower()
            if "nginx" in server:
                tech_indicators["platforms"].append("Nginx")
            if "apache" in server:
                tech_indicators["platforms"].append("Apache")
            if "php" in x_powered:
                tech_indicators["languages"].append("PHP")
            if "express" in x_powered:
                tech_indicators["frameworks"].append("Express")

            # HTML keyword-based detection
            found = await extraction_tool.extract_tech_stack(html)
            tech_indicators["frameworks"].extend([t for t in found if t not in tech_indicators["frameworks"]])
            tech_indicators["confidence"] = 0.7 if found else 0.4

            return tech_indicators
        except Exception as e:
            self.logger.error(f"Tech stack detection error: {e}")
            return {"frameworks": [], "languages": [], "platforms": [], "confidence": 0.3}
    
    async def _analyze_with_llm(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company with Ollama LLM."""
        try:
            from agents.tools.tools import ai_service_tool
            import json

            services_text = " ".join(company_data.get("services", [])[:10])
            tech_text = str(company_data.get("frameworks", []) + company_data.get("languages", []))

            prompt = (
                f"Analyze this company based on their website content and tech stack.\n"
                f"Website content: {services_text[:1500]}\n"
                f"Tech stack detected: {tech_text}\n\n"
                "Return a JSON object with these exact keys:\n"
                "- business_model (string): e.g. SaaS, Agency, Marketplace\n"
                "- team_size (string): estimated range e.g. 1-10, 10-50, 50-200\n"
                "- pain_points (list of strings): top 3 likely pain points\n"
                "- ejicode_fit_score (integer 0-100): how well Ejicode AI/backend services fit\n"
                "- recommended_angle (string): best outreach angle for Ejicode\n"
                "Return only valid JSON, no extra text."
            )

            result = await ai_service_tool.reason(prompt)
            raw = result.get("reasoning", "")

            # Extract JSON from response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(raw[start:end])
            else:
                raise ValueError("No JSON found in LLM response")

            return analysis
        except Exception as e:
            self.logger.error(f"LLM analysis error: {e}")
            return {
                "business_model": "Unknown",
                "team_size": "Unknown",
                "pain_points": [],
                "ejicode_fit_score": 50,
                "recommended_angle": "General outreach",
            }
    
    async def process(self, state: AgentState) -> AgentState:
        """Perform deep company research."""
        company_id = state.get("input_data", {}).get("company_id")
        domain = state.get("input_data", {}).get("domain")
        
        self.logger.info(f"Research Agent: Starting research for {domain or company_id}")
        
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "research"
        
        if not domain:
            return self._update_state(state, {
                "status": AgentStatus.FAILURE,
                "error_message": "No domain provided",
            })
        
        # Perform research steps
        website_data = await self._scrape_website(domain)
        tech_stack = await self._detect_tech_stack(domain)
        analysis = await self._analyze_with_llm({**website_data, **tech_stack})
        
        research_report = {
            "company_id": company_id,
            "domain": domain,
            "website_data": website_data,
            "tech_stack": tech_stack,
            "analysis": analysis,
            "confidence_score": 0.72,
        }
        
        self.logger.info(f"Research complete for {domain}")
        
        return self._update_state(state, {
            "current_step": "research_complete",
            "steps_completed": state.get("steps_completed", []) + ["research"],
            "output_data": research_report,
            "status": AgentStatus.SUCCESS,
            "confidence_score": 0.72,
        })
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate research output."""
        required_keys = ["domain", "analysis"]
        return all(k in output_data for k in required_keys)
