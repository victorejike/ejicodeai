"""Company Scout Agent — Discovers companies needing candidate skills and generates the 'Companies You Should Approach' pipeline."""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.base.skill_vocabulary import extract_skills_by_category

logger = logging.getLogger(__name__)

#: Who signs off on a hire, by the discipline the candidate works in. This is
#: knowledge about how companies are organised - it is selected using the
#: candidate's own skills, never assumed to be engineering.
CONTACT_ROLES_BY_DISCIPLINE = {
    "language": ["Engineering Manager", "Head of Engineering", "Technical Founder"],
    "framework": ["Engineering Manager", "Head of Engineering", "Technical Founder"],
    "database": ["Head of Engineering", "Data Platform Lead"],
    "cloud": ["Head of Platform", "Head of Infrastructure"],
    "devops": ["Head of Platform", "Head of Infrastructure", "SRE Lead"],
    "architecture": ["Head of Engineering", "Principal Engineer"],
    "ai": ["Head of AI", "Head of Machine Learning", "Technical Founder"],
    "data": ["Head of Data", "Analytics Lead"],
    "design": ["Head of Design", "Design Director", "Product Lead"],
    "product": ["Head of Product", "VP Product", "Founder"],
    "marketing": ["Head of Marketing", "Growth Lead", "Founder"],
    "business": ["Head of Sales", "Commercial Director", "Founder"],
    "security": ["Head of Security", "CISO"],
    "quality": ["QA Lead", "Head of Engineering"],
    "communication": ["Hiring Manager"],
    "healthcare": ["Clinical Director", "Head of Nursing"],
    "education": ["Head of Department", "Principal"],
    "operations": ["Head of Operations", "Operations Director"],
    "engineering": ["Engineering Manager", "Head of Engineering"],
}


class GitHubTrendingScraper:
    """Scrape GitHub trending repos to find active tech companies/projects."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx
            from bs4 import BeautifulSoup

            from agents.scrapers.base_adapter import scraper_config

            cfg = scraper_config()
            async with httpx.AsyncClient(headers=cfg.headers) as client:
                resp = await client.get("https://github.com/trending", timeout=cfg.timeout)
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
                        # Only the language GitHub actually reports; no filler.
                        "industry": language or None,
                        "description": description or None,
                        "tech_stack": [language] if language else [],
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
                        # A Show HN post says nothing about the industry or the
                        # stack, so both stay unknown until something confirms them.
                        "industry": None,
                        "description": title,
                        "tech_stack": [],
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

    @staticmethod
    def suggest_contact_roles(candidate_skills: List[str]) -> List[str]:
        """Roles that hire for the candidate's discipline, inferred from their skills."""
        if not candidate_skills:
            return []
        grouped = extract_skills_by_category(" ".join(str(s) for s in candidate_skills))
        ranked = sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True)
        roles: List[str] = []
        for category, _ in ranked:
            for role in CONTACT_ROLES_BY_DISCIPLINE.get(category, []):
                if role not in roles:
                    roles.append(role)
            if len(roles) >= 3:
                break
        return roles[:3]

    def evaluate_approach_potential(
        self, company: Dict[str, Any], candidate_skills: List[str]
    ) -> Dict[str, Any]:
        """Determine whether the individual could be valuable to this company even without a formal job post.

        Scored out of 100 from four things we can actually observe. With no
        candidate skills the score is ``None`` and ``pipeline_type`` is
        ``"unscored"`` - a company cannot be a good approach target for a
        candidate we know nothing about.
        """
        comp_tech = [str(t).strip() for t in (company.get("tech_stack") or []) if str(t).strip()]
        skills = [str(s).strip() for s in (candidate_skills or []) if str(s).strip()]

        comp_tech_lower = {t.lower() for t in comp_tech}
        skills_lower = {s.lower() for s in skills}
        overlap = [t for t in comp_tech if t.lower() in skills_lower]

        c_name = company.get("name") or "This company"
        industry = company.get("industry")
        reachable = bool(company.get("domain") or company.get("website"))

        if not skills:
            return {
                "company_name": c_name,
                "domain": company.get("domain"),
                "website": company.get("website"),
                "industry": industry,
                "description": company.get("description"),
                "approach_score": None,
                "score_breakdown": {},
                "approach_reason": (
                    f"{c_name} was discovered as an active company, but your profile has no skills on "
                    "file yet, so we cannot say whether approaching them is worth your time."
                ),
                "target_contact_role": None,
                "target_contact_roles": [],
                "valuable_skills": [],
                "pipeline_type": "unscored",
                "missing_inputs": ["candidate_skills"],
            }

        # Skill overlap is the substance of the case for approaching. Credited on
        # the share of their stack you cover, floored by the absolute number of
        # matching skills so a company listing 20 technologies is not penalised.
        if comp_tech_lower:
            ratio = len(overlap) / len(comp_tech_lower)
            count_credit = min(len(overlap), 4) / 4
            skill_points = int(round(60 * max(ratio, count_credit)))
        else:
            skill_points = 0

        breakdown = {
            "skill_overlap": skill_points,
            # A published stack is what makes the fit verifiable instead of assumed.
            "assessable_stack": 15 if comp_tech_lower else 0,
            "reachable": 15 if reachable else 0,
            "industry_clarity": 10 if industry else 0,
        }
        score = min(sum(breakdown.values()), 100)

        reason_parts = []
        if overlap:
            reason_parts.append(
                f"{c_name} works with {', '.join(overlap[:3])}, which you already have on your profile."
            )
        elif comp_tech:
            reason_parts.append(
                f"{c_name} works with {', '.join(comp_tech[:3])}, none of which is on your profile yet."
            )
        else:
            reason_parts.append(f"{c_name} has not published a technology stack, so the fit is unverified.")

        if industry:
            reason_parts.append(f"Industry: {industry}.")
        if not reachable:
            reason_parts.append("No website or domain found, so outreach would need a contact first.")

        return {
            "company_name": c_name,
            "domain": company.get("domain"),
            "website": company.get("website"),
            "industry": industry,
            "description": company.get("description"),
            "approach_score": score,
            "score_breakdown": breakdown,
            "approach_reason": " ".join(reason_parts),
            "target_contact_roles": self.suggest_contact_roles(skills),
            "target_contact_role": (self.suggest_contact_roles(skills) or [None])[0],
            "valuable_skills": overlap,
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

        # "Companies You Should Approach" is only meaningful against a real
        # profile; with none, the companies are still returned but unscored.
        input_data = state.get("input_data", {})
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}
        candidate_skills = (
            input_data.get("skills")
            or candidate_profile.get("skills")
            or candidate_profile.get("technologies")
            or []
        )
        companies_to_approach = [
            self.evaluate_approach_potential(c, candidate_skills) for c in unique[:10]
        ]
        companies_to_approach.sort(key=lambda c: c.get("approach_score") or -1, reverse=True)

        logger.info(
            "Company Scout: %d unique companies found, %d evaluated for approach against %d candidate skills",
            len(unique), len(companies_to_approach), len(candidate_skills),
        )

        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": ["company_discovery"],
            "output_data": {
                "companies": unique,
                "count": len(unique),
                "companies_to_approach": companies_to_approach,
                "candidate_profile": candidate_profile,
            },
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "companies" in output_data
