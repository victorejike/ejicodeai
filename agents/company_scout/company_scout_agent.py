"""Company Scout Agent — Discovers companies needing candidate skills and generates the 'Companies You Should Approach' pipeline."""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class GitHubTrendingScraper:
    """Scrape GitHub trending repos to find active tech companies/projects."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(headers={"User-Agent": "EjicodeAI/1.0"}) as client:
                resp = await client.get("https://github.com/trending", timeout=20)
                soup = BeautifulSoup(resp.text, "html.parser")

                companies = []
                for repo in soup.select("article.Box-row")[:20]:
                    name_tag = repo.select_one("h2 a")
                    if not name_tag:
                        continue
                    full_name = name_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                    parts = full_name.split("/")
                    if len(parts) != 2:
                        continue
                    owner, repo_name = parts

                    desc_tag = repo.select_one("p")
                    description = desc_tag.get_text(strip=True) if desc_tag else ""

                    lang_tag = repo.select_one("[itemprop='programmingLanguage']")
                    language = lang_tag.get_text(strip=True) if lang_tag else ""

                    stars_tag = repo.select_one("a[href$='/stargazers']")
                    stars = stars_tag.get_text(strip=True).replace(",", "") if stars_tag else "0"

                    companies.append({
                        "name": owner,
                        "domain": f"github.com/{owner}",
                        "website": f"https://github.com/{owner}",
                        "industry": language or "Technology",
                        "description": description,
                        "tech_stack": [language] if language else ["Python", "JavaScript"],
                        "source": "github_trending",
                        "metadata": {"repo": repo_name, "stars": stars, "language": language},
                    })

                logger.info(f"GitHub Trending: {len(companies)} companies")
                return companies
        except Exception as e:
            logger.error(f"GitHub Trending error: {e}")
            return []


class HNShowScraper:
    """Scrape HN 'Show HN' posts to find new startups/products."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"tags": "show_hn", "hitsPerPage": 30, "numericFilters": "points>10"},
                    timeout=15,
                )
                hits = resp.json().get("hits", [])

                companies = []
                for hit in hits:
                    title = hit.get("title", "")
                    url = hit.get("url", "")
                    if not url or not title:
                        continue

                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc.replace("www.", "")
                    except Exception:
                        domain = ""

                    if not domain:
                        continue

                    companies.append({
                        "name": title.replace("Show HN: ", "")[:80],
                        "domain": domain,
                        "website": url,
                        "industry": "Technology / AI",
                        "description": title,
                        "tech_stack": ["Python", "FastAPI", "React"],
                        "source": "hackernews_show",
                        "metadata": {"points": hit.get("points", 0), "hn_id": hit.get("objectID")},
                    })

                logger.info(f"HN Show HN: {len(companies)} companies")
                return companies
        except Exception as e:
            logger.error(f"HN Show HN error: {e}")
            return []


class CompanyScoutAgent(BaseAgent):
    """Discovers tech companies and builds the 'Companies You Should Approach' proactive pipeline."""

    def __init__(self):
        super().__init__(
            name="company_scout",
            agent_type="discovery",
            description="Discovers active tech companies and builds proactive 'Companies You Should Approach' pipeline",
            max_retries=3,
            timeout_seconds=120,
        )
        self.scrapers = [GitHubTrendingScraper(), HNShowScraper()]

    async def validate_input(self, input_data: dict) -> bool:
        return True

    def evaluate_approach_potential(self, company: Dict[str, Any], candidate_skills: List[str]) -> Dict[str, Any]:
        """Determine whether the individual could be valuable to this company even without a formal job post."""
        comp_tech = set(company.get("tech_stack", []))
        user_skills = set(candidate_skills or ["Python", "FastAPI", "React"])
        overlap = list(comp_tech & user_skills)

        # Baseline alignment
        score = 75
        if overlap:
            score += min(len(overlap) * 10, 20)

        c_name = company.get("name", "Target Company")
        ind = company.get("industry", "Technology")

        approach_reason = (
            f"{c_name} is actively launching products in {ind} and scaling engineering infrastructure. "
            f"Your proficiency in {', '.join(list(user_skills)[:3])} matches their technical domain."
        )

        return {
            "company_name": c_name,
            "domain": company.get("domain"),
            "website": company.get("website"),
            "industry": ind,
            "description": company.get("description"),
            "approach_score": min(score, 98),
            "approach_reason": approach_reason,
            "target_contact_role": "VP of Engineering or Technical Founder",
            "valuable_skills": overlap or list(user_skills)[:3],
            "pipeline_type": "proactive_approach",
        }

    async def process(self, state: AgentState) -> AgentState:
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "discovery"

        results = await asyncio.gather(*[s.scrape() for s in self.scrapers], return_exceptions=True)

        all_companies = []
        for r in results:
            if isinstance(r, list):
                all_companies.extend(r)

        # Deduplicate by domain
        seen = {}
        for c in all_companies:
            domain = c.get("domain", "")
            if domain and domain not in seen:
                seen[domain] = c
        unique = list(seen.values())

        # If candidate profile is passed, generate "Companies You Should Approach"
        input_data = state.get("input_data", {})
        candidate_skills = input_data.get("skills", ["Python", "FastAPI", "PostgreSQL"])
        companies_to_approach = [
            self.evaluate_approach_potential(c, candidate_skills) for c in unique[:10]
        ]

        logger.info(f"Company Scout: {len(unique)} unique companies found, {len(companies_to_approach)} evaluated for approach")

        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": ["company_discovery"],
            "output_data": {
                "companies": unique,
                "count": len(unique),
                "companies_to_approach": companies_to_approach,
            },
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "companies" in output_data
