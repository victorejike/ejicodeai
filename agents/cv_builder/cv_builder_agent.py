"""CV Builder Agent - builds an ATS-parseable CV from the candidate's own profile.

Two rules shape this agent:

1. **Nothing is invented.** Every line of the document traces back to a field the
   candidate filled in. A requirement the job asks for and the profile does not
   contain is reported as a *missing keyword* for the user to add if it is true of
   them - it is never written into their CV on their behalf.
2. **The format is safe by construction.** The renderers can only emit a single
   stream of left-aligned paragraphs (see ``renderers.py``), so the layout
   failures that actually break applicant tracking systems - tables, text boxes,
   multiple columns, images, headers and footers - are not expressible. The score
   then re-checks the produced text, so a regression shows up as a number.

The ATS score is out of 100 across four components. When a component cannot be
measured (no target job, so no requirement list) it is reported as ``None`` and
the total is normalised over what *was* measurable, rather than filled in with an
optimistic guess.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agents.base.base_agent import AgentState, AgentStatus, BaseAgent
from agents.base.skill_vocabulary import canonicalize, extract_skills

#: Section headings applicant tracking systems are known to recognise. Order is
#: the reading order of the document.
ATS_HEADINGS: Tuple[str, ...] = (
    "Professional Summary",
    "Skills",
    "Experience",
    "Projects",
    "Education",
    "Certifications",
)

#: Sections that must carry content for a CV to be considered complete.
REQUIRED_HEADINGS: Tuple[str, ...] = ("Professional Summary", "Skills", "Experience")

#: Characters that survive badly through CV text extraction. The renderer never
#: produces them; the check exists so profile text carrying them is flagged.
UNSAFE_GLYPHS = "•‣▪◦●○◆◇■□★☆✦✓✔✗✘➤➔→←↑↓⇒»«§¶™®©…"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MONTHS = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
    "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}

_ATS_SYSTEM_PROMPT = (
    "You rewrite CV professional summaries for applicant tracking systems. "
    "Use ONLY the facts given to you. Never add skills, employers, metrics, dates or "
    "achievements that are not in the facts. Plain sentences, no bullet characters, "
    "no markdown, no emoji, no first-person pronouns. 60 words maximum."
)


def _clean(value: Any) -> Optional[str]:
    """Collapse whitespace and strip ATS-hostile glyphs from a profile value."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    for glyph in UNSAFE_GLYPHS:
        text = text.replace(glyph, "-" if glyph in "•‣▪◦●○◆◇■□" else "")
    text = text.replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    return text.strip() or None


def _format_date(value: Any) -> Optional[str]:
    """Normalise a date to ``Mon YYYY`` / ``YYYY``, the formats parsers expect."""
    text = _clean(value)
    if not text:
        return None
    if text.lower() in {"present", "current", "now", "ongoing"}:
        return "Present"
    iso = re.match(r"^(\d{4})[-/](\d{1,2})", text)
    if iso:
        month = _MONTHS.get(iso.group(2).zfill(2))
        return f"{month} {iso.group(1)}" if month else iso.group(1)
    year_only = re.match(r"^(\d{4})$", text)
    if year_only:
        return year_only.group(1)
    return text


class CVBuilderAgent(BaseAgent):
    """Produces an ATS-safe CV, its ATS score and its honest keyword gaps."""

    def __init__(self):
        super().__init__(
            name="cv_builder",
            agent_type="generation",
            description="Builds an ATS-parseable CV from the candidate's profile, tailored to a target role",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        """A CV needs a real person behind it: a name plus skills or history."""
        profile = (input_data or {}).get("candidate_profile") or (input_data or {}).get("profile") or {}
        if not isinstance(profile, dict):
            return False
        has_identity = bool(profile.get("full_name") or profile.get("name"))
        has_substance = bool(
            profile.get("skills") or profile.get("technologies") or profile.get("experience")
        )
        return has_identity and has_substance

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------

    @staticmethod
    def extract_requirement_keywords(opportunity: Optional[Dict[str, Any]]) -> List[str]:
        """What the target posting actually asks for, canonicalised.

        Combines the structured ``tech_required`` list with skills named in the
        title and description, so a posting that only writes its requirements in
        prose is still measured against.
        """
        if not opportunity:
            return []
        stated = [str(t) for t in (opportunity.get("tech_required") or []) if str(t).strip()]
        prose = " ".join(
            str(opportunity.get(field) or "")
            for field in ("title", "description", "requirements", "raw_description")
        )
        return canonicalize(stated + extract_skills(prose))

    @staticmethod
    def align_keywords(
        candidate_skills: Sequence[Any], required_keywords: Sequence[Any]
    ) -> Tuple[List[str], List[str]]:
        """``(matched, missing)`` - matched are the candidate's own, missing are gaps.

        Missing keywords are never added to the document. They are returned so the
        user can add the ones that are genuinely true of them.
        """
        own = canonicalize(candidate_skills)
        own_lower = {s.lower() for s in own}
        matched: List[str] = []
        missing: List[str] = []
        for keyword in canonicalize(required_keywords):
            if keyword.lower() in own_lower:
                if keyword not in matched:
                    matched.append(keyword)
            elif keyword not in missing:
                missing.append(keyword)
        return matched, missing

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _contact_line(profile: Dict[str, Any]) -> str:
        """Machine-readable contact block: one line, pipe separated, no icons."""
        parts = [
            _clean(profile.get("location")),
            _clean(profile.get("email")),
            _clean(profile.get("phone")),
            _clean(profile.get("linkedin_url")),
            _clean(profile.get("github_url")),
            _clean(profile.get("portfolio_url")),
        ]
        return " | ".join(p for p in parts if p)

    @classmethod
    def _deterministic_summary(
        cls,
        profile: Dict[str, Any],
        matched: Sequence[str],
        opportunity: Optional[Dict[str, Any]],
    ) -> str:
        """Summary assembled from profile facts only. Used when no AI key exists."""
        title = _clean(profile.get("title") or profile.get("primary_title"))
        years = profile.get("experience_years")
        try:
            years_val = float(years) if years not in (None, "") else None
        except (TypeError, ValueError):
            years_val = None

        sentences: List[str] = []
        opening = title or "Professional"
        if years_val:
            opening += f" with {years_val:.0f}+ years of experience"
        sentences.append(opening + ".")

        if matched:
            sentences.append(f"Relevant skills: {', '.join(list(matched)[:8])}.")
        else:
            own = canonicalize(profile.get("skills"))
            if own:
                sentences.append(f"Core skills: {', '.join(own[:8])}.")

        bio = _clean(profile.get("bio"))
        if bio:
            sentences.append(bio if bio.endswith(".") else bio + ".")

        goals = _clean(profile.get("career_goals"))
        if goals:
            sentences.append(f"Focus: {goals}" + ("" if goals.endswith(".") else "."))

        target_title = _clean((opportunity or {}).get("title"))
        if target_title:
            sentences.append(f"Applying for: {target_title}.")

        return " ".join(sentences)

    @classmethod
    def render_cv(
        cls,
        profile: Dict[str, Any],
        *,
        opportunity: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Render the CV text and report which sections carry content.

        Single column, standard headings, ``- `` bullets, reverse-chronological.
        """
        profile = profile or {}
        required = cls.extract_requirement_keywords(opportunity)
        own_skills = canonicalize(profile.get("skills")) or canonicalize(profile.get("technologies"))
        matched, missing = cls.align_keywords(own_skills, required)

        name = _clean(profile.get("full_name") or profile.get("name")) or "Candidate"
        title = _clean(profile.get("title") or profile.get("primary_title"))

        lines: List[str] = [name]
        if title:
            lines.append(title)
        contact = cls._contact_line(profile)
        if contact:
            lines.append(contact)

        sections: Dict[str, List[str]] = {}

        # Professional Summary
        summary_text = _clean(summary) or cls._deterministic_summary(profile, matched, opportunity)
        sections["Professional Summary"] = [summary_text] if summary_text else []

        # Skills - the candidate's own list, with the target's requirements first so
        # a keyword-matching parser finds them early. Nothing is added here.
        ordered_skills = matched + [s for s in own_skills if s not in matched]
        sections["Skills"] = [", ".join(ordered_skills)] if ordered_skills else []

        # Experience - reverse-chronological, bullets that evidence a matched
        # requirement lifted to the top of their entry.
        experience_lines: List[str] = []
        for entry in cls._sorted_experience(profile.get("experience")):
            experience_lines.extend(cls._render_experience_entry(entry, matched))
        sections["Experience"] = experience_lines

        # Projects
        project_lines: List[str] = []
        for project in (profile.get("projects") or []):
            project_lines.extend(cls._render_project(project))
        sections["Projects"] = project_lines

        # Education
        education_lines: List[str] = []
        for entry in (profile.get("education") or []):
            rendered = cls._render_education(entry)
            if rendered:
                education_lines.append(rendered)
        sections["Education"] = education_lines

        # Certifications
        cert_lines: List[str] = []
        for cert in (profile.get("certifications") or []):
            rendered = cls._render_certification(cert)
            if rendered:
                cert_lines.append(rendered)
        sections["Certifications"] = cert_lines

        for heading in ATS_HEADINGS:
            body = [line for line in sections.get(heading, []) if line]
            if not body:
                continue
            lines.append("")
            lines.append(heading)
            lines.extend(body)

        content_text = "\n".join(lines).strip() + "\n"
        return {
            "content_text": content_text,
            "sections": {k: v for k, v in sections.items() if v},
            "headings_used": [h for h in ATS_HEADINGS if sections.get(h)],
            "keywords_matched": matched,
            "keywords_missing": missing,
            "keywords_required": required,
            "skills_listed": ordered_skills,
        }

    @staticmethod
    def _sorted_experience(experience: Any) -> List[Any]:
        """Reverse-chronological ordering, most recent first.

        Entries that say "Present" sort first; the rest by whatever year they
        state. Entries with no dates keep their original relative position.
        """
        entries = list(experience or [])

        def key(item: Any) -> Tuple[int, int]:
            if not isinstance(item, dict):
                return (0, 0)
            end = str(item.get("end_date") or item.get("end") or "").lower()
            if end in {"present", "current", "now", "ongoing"}:
                return (2, 9999)
            years = re.findall(r"(\d{4})", f"{end} {item.get('start_date') or item.get('start') or ''}")
            return (1, max(int(y) for y in years)) if years else (0, 0)

        return sorted(entries, key=key, reverse=True)

    @classmethod
    def _render_experience_entry(cls, entry: Any, matched: Sequence[str]) -> List[str]:
        """One role: heading line, date line, then ``- `` bullets."""
        if not isinstance(entry, dict):
            text = _clean(entry)
            return [f"- {text}"] if text else []

        role = _clean(entry.get("title") or entry.get("role") or entry.get("position"))
        company = _clean(entry.get("company") or entry.get("employer") or entry.get("organization"))
        header = ", ".join(p for p in (role, company) if p)
        if not header:
            return []

        lines = [header]

        start = _format_date(entry.get("start_date") or entry.get("start"))
        end = _format_date(entry.get("end_date") or entry.get("end")) or ("Present" if start else None)
        location = _clean(entry.get("location"))
        date_parts = [f"{start} - {end}" if start and end else (start or end), location]
        date_line = " | ".join(p for p in date_parts if p)
        if date_line:
            lines.append(date_line)

        bullets: List[str] = []
        raw_bullets = entry.get("bullets") or entry.get("highlights") or entry.get("achievements") or []
        if isinstance(raw_bullets, str):
            raw_bullets = [raw_bullets]
        for bullet in raw_bullets:
            text = _clean(bullet)
            if text:
                bullets.append(text)
        description = _clean(entry.get("description") or entry.get("summary"))
        if description and description not in bullets:
            bullets.extend(
                part.strip() for part in re.split(r"(?<=[.!?])\s+", description) if part.strip()
            )

        matched_lower = [m.lower() for m in matched]

        def evidences_requirement(text: str) -> int:
            lowered = text.lower()
            return sum(1 for keyword in matched_lower if keyword in lowered)

        # Bullets already written by the candidate are only reordered, never edited:
        # the ones that evidence a requirement of this job come first.
        bullets.sort(key=evidences_requirement, reverse=True)
        lines.extend(f"- {b}" for b in bullets)
        return lines

    @staticmethod
    def _render_project(project: Any) -> List[str]:
        if not isinstance(project, dict):
            text = _clean(project)
            return [f"- {text}"] if text else []
        name = _clean(project.get("name") or project.get("title"))
        tech = ", ".join(_clean(t) or "" for t in (project.get("tech_stack") or project.get("technologies") or []))
        description = _clean(project.get("description"))
        url = _clean(project.get("url") or project.get("link"))
        header = " | ".join(p for p in (name, tech.strip(", ") or None, url) if p)
        lines = [header] if header else []
        if description:
            lines.append(f"- {description}")
        return lines

    @staticmethod
    def _render_education(entry: Any) -> Optional[str]:
        if not isinstance(entry, dict):
            return _clean(entry)
        parts = [
            _clean(entry.get("degree") or entry.get("qualification")),
            _clean(entry.get("field") or entry.get("field_of_study")),
            _clean(entry.get("institution") or entry.get("school") or entry.get("university")),
            _format_date(entry.get("end_date") or entry.get("graduation_year") or entry.get("year")),
        ]
        return ", ".join(p for p in parts if p) or None

    @staticmethod
    def _render_certification(cert: Any) -> Optional[str]:
        if not isinstance(cert, dict):
            return _clean(cert)
        parts = [
            _clean(cert.get("name") or cert.get("title")),
            _clean(cert.get("issuer") or cert.get("authority")),
            _format_date(cert.get("issued") or cert.get("date") or cert.get("year")),
        ]
        return ", ".join(p for p in parts if p) or None

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def check_format_safety(content_text: str) -> Tuple[int, List[str]]:
        """``(points out of 25, issues)`` for the things that break CV parsers."""
        issues: List[str] = []
        points = 25

        if "\t" in content_text:
            issues.append("Tab characters found: parsers read them as column breaks.")
            points -= 8

        found_glyphs = sorted({g for g in UNSAFE_GLYPHS if g in content_text})
        if found_glyphs:
            issues.append(f"Non-standard characters found: {' '.join(found_glyphs)}")
            points -= 6

        if re.search(r"\S {3,}\S", content_text):
            issues.append("Runs of spaces found: these imitate columns and misorder extracted text.")
            points -= 5

        bad_bullets = re.findall(r"(?m)^\s*[*+>·]\s+", content_text)
        if bad_bullets:
            issues.append("Non-standard bullet characters found: use '- '.")
            points -= 3

        if re.search(r"(?m)^\s+\S", content_text):
            issues.append("Indented lines found: leading whitespace can imply a table cell.")
            points -= 3

        return max(points, 0), issues

    @classmethod
    def score_ats(
        cls,
        content_text: str,
        *,
        required_keywords: Sequence[str],
        matched_keywords: Sequence[str],
        sections: Dict[str, List[str]],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Four-component ATS score, normalised over what could be measured."""
        issues: List[str] = []
        recommendations: List[str] = []

        # 1. Keyword coverage (40) - only measurable against a target posting.
        if required_keywords:
            present = [
                k for k in matched_keywords if k.lower() in content_text.lower()
            ]
            coverage = round(40 * len(present) / len(required_keywords))
            keyword_coverage: Optional[int] = coverage
            if len(present) < len(required_keywords):
                recommendations.append(
                    f"{len(required_keywords) - len(present)} of {len(required_keywords)} "
                    "requirements from this posting are not evidenced on your profile."
                )
        else:
            keyword_coverage = None
            recommendations.append(
                "Build against a specific job to measure keyword coverage for that posting."
            )

        # 2. Format safety (25).
        format_safety, format_issues = cls.check_format_safety(content_text)
        issues.extend(format_issues)

        # 3. Section completeness (20) - 4 points per section a parser looks for.
        completeness = 0
        if _EMAIL_RE.search(content_text):
            completeness += 4
        else:
            issues.append("No email address in the contact block: recruiters cannot reply.")
        for heading in REQUIRED_HEADINGS:
            if sections.get(heading):
                completeness += 4
            else:
                issues.append(f"Missing section: {heading}.")
        if sections.get("Education") or sections.get("Certifications"):
            completeness += 4
        else:
            recommendations.append("Add education or certifications; most parsers expect one of them.")

        # 4. Readability (15).
        readability = 0
        words = content_text.split()
        word_count = len(words)
        if 250 <= word_count <= 1200:
            readability += 5
        else:
            issues.append(
                f"CV is {word_count} words; parsers and reviewers expect roughly 250-1200."
            )
        bullets = [b for b in re.findall(r"(?m)^- (.+)$", content_text)]
        if bullets:
            avg_words = sum(len(b.split()) for b in bullets) / len(bullets)
            if avg_words <= 28:
                readability += 5
            else:
                issues.append(f"Bullets average {avg_words:.0f} words; keep them under 28.")
        else:
            issues.append("No bullet points found under Experience.")
        long_lines = [line for line in content_text.splitlines() if len(line) > 220]
        if not long_lines:
            readability += 5
        else:
            issues.append(f"{len(long_lines)} very long line(s) found; break them into bullets.")

        components: Dict[str, Optional[int]] = {
            "keyword_coverage": keyword_coverage,
            "format_safety": format_safety,
            "section_completeness": completeness,
            "readability": readability,
        }
        maxima = {
            "keyword_coverage": 40,
            "format_safety": 25,
            "section_completeness": 20,
            "readability": 15,
        }
        measured = {k: v for k, v in components.items() if v is not None}
        available = sum(maxima[k] for k in measured)
        score = round(100 * sum(measured.values()) / available) if available else 0

        return {
            "ats_score": score,
            "breakdown": components,
            "breakdown_maximums": maxima,
            "measured_out_of": available,
            "issues": issues,
            "recommendations": recommendations,
            "word_count": word_count,
        }

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    async def _ai_summary(
        self, profile: Dict[str, Any], matched: Sequence[str], opportunity: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Ask the configured provider to phrase the summary from given facts only.

        Returns ``None`` when no provider is configured or when the answer
        introduces a skill the candidate never claimed - in which case the
        deterministic summary is used instead.
        """
        try:
            from backend.app.services.ai.manager import ai_manager
        except Exception:  # pragma: no cover - AI stack optional
            return None

        own_skills = canonicalize(profile.get("skills"))
        facts = {
            "title": profile.get("title") or profile.get("primary_title"),
            "years_of_experience": profile.get("experience_years"),
            "skills": own_skills,
            "career_goals": profile.get("career_goals"),
            "bio": profile.get("bio"),
            "target_role": (opportunity or {}).get("title"),
            "target_company": (opportunity or {}).get("company_name"),
            "requirements_the_candidate_meets": list(matched),
        }
        prompt = (
            "Write the Professional Summary section of a CV, 2-3 sentences, using only "
            f"these facts:\n{facts}\n"
            "Do not mention any technology that is not in 'skills'. Do not state a number "
            "of years unless 'years_of_experience' is given. Output the summary text only."
        )

        try:
            response = await ai_manager.generate(
                prompt, system_prompt=_ATS_SYSTEM_PROMPT, max_tokens=300, temperature=0.4
            )
        except Exception as exc:
            self.logger.warning("AI summary unavailable: %s", exc)
            return None

        if not getattr(response, "success", False):
            return None
        text = _clean(getattr(response, "output", None) or "")
        if not text or len(text) > 900:
            return None

        # Truthfulness guard: the model may not introduce skills of its own.
        own_lower = {s.lower() for s in own_skills}
        invented = [s for s in extract_skills(text) if s.lower() not in own_lower]
        if invented:
            self.logger.warning(
                "Discarding AI summary: it introduced skills not on the profile (%s)",
                ", ".join(invented),
            )
            return None
        if not profile.get("experience_years") and re.search(r"\b\d+\+?\s*(years|yrs)\b", text, re.I):
            self.logger.warning("Discarding AI summary: it invented a number of years of experience")
            return None
        return text

    async def build(
        self,
        profile: Dict[str, Any],
        opportunity: Optional[Dict[str, Any]] = None,
        *,
        use_ai: bool = True,
    ) -> Dict[str, Any]:
        """Build one CV (optionally tailored to ``opportunity``) with its ATS report."""
        summary = await self._ai_summary(
            profile,
            self.align_keywords(
                canonicalize(profile.get("skills")), self.extract_requirement_keywords(opportunity)
            )[0],
            opportunity,
        ) if use_ai else None

        rendered = self.render_cv(profile, opportunity=opportunity, summary=summary)
        report = self.score_ats(
            rendered["content_text"],
            required_keywords=rendered["keywords_required"],
            matched_keywords=rendered["keywords_matched"],
            sections=rendered["sections"],
            profile=profile,
        )

        return {
            **rendered,
            **report,
            "summary_source": "ai" if summary else "template",
            "target_opportunity_id": (opportunity or {}).get("id"),
            "target_title": (opportunity or {}).get("title"),
            "target_company": (opportunity or {}).get("company_name"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def process(self, state: AgentState) -> AgentState:
        """Build one tailored CV per top opportunity, plus a general-purpose one."""
        input_data = state.get("input_data", {}) or {}
        profile = input_data.get("candidate_profile") or input_data.get("profile") or {}
        opportunities = [o for o in (input_data.get("opportunities") or []) if isinstance(o, dict)]
        limit = int(input_data.get("cv_limit") or 3)

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "cv_builder"

        if not await self.validate_input({"candidate_profile": profile}):
            state["status"] = AgentStatus.ESCALATED
            state["escalation_reason"] = "profile_incomplete"
            state["error_message"] = (
                "A CV needs your name and either your skills or your work history."
            )
            state["output_data"] = {
                "cvs": [],
                "count": 0,
                "candidate_profile": profile,
                "opportunities": opportunities,
            }
            return state

        # Highest-scoring opportunities first when matching already ran.
        ranked = sorted(
            opportunities,
            key=lambda o: o.get("match_score") if isinstance(o.get("match_score"), (int, float)) else -1,
            reverse=True,
        )[:limit]

        cvs: List[Dict[str, Any]] = []
        base = await self.build(profile, None)
        base["is_general"] = True
        cvs.append(base)

        for index, opportunity in enumerate(ranked, start=1):
            await self.emit(
                state,
                "agent.progress",
                f"Tailoring CV {index} of {len(ranked)} for "
                f"{opportunity.get('title') or 'a role'} at {opportunity.get('company_name') or 'an employer'}",
                payload={"ats_target": opportunity.get("source_url")},
            )
            tailored = await self.build(profile, opportunity)
            tailored["is_general"] = False
            cvs.append(tailored)

        best = max((c["ats_score"] for c in cvs), default=0)
        self.logger.info("CV Builder: produced %d CVs, best ATS score %s", len(cvs), best)

        return self._update_state(state, {
            "current_step": "cv_builder_complete",
            "steps_completed": state.get("steps_completed", []) + ["cv_builder"],
            "output_data": {
                "cvs": cvs,
                "count": len(cvs),
                "best_ats_score": best,
                # Handed to the next stage untouched.
                "candidate_profile": profile,
                "opportunities": opportunities,
            },
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "cvs" in output_data
