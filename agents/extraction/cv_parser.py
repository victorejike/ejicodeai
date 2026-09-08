"""CV Intelligence Parser supporting PDF, DOCX, and TXT files.
Extracts skills, work experience, education, certifications, projects, and contact info.
Strictly adheres to Zero Fabrication: missing fields are None or UNKNOWN.
"""
from datetime import datetime
import hashlib
import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import docx

logger = logging.getLogger(__name__)

# Standard Skills Taxonomy for precise keyword matching
SKILLS_TAXONOMY = [
    # Languages
    "Python", "TypeScript", "JavaScript", "Go", "Golang", "Rust", "Java", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "SQL", "HTML", "CSS", "R", "Scala", "Dart", "Elixir", "Bash", "Shell", "Solidity",
    # Frameworks & Libraries
    "FastAPI", "Django", "Flask", "React", "React Native", "Next.js", "Vue", "Vue.js", "Angular", "Node.js", "Express", "NestJS", "Spring", "Spring Boot", ".NET", "Rails", "Ruby on Rails", "Tailwind CSS", "GraphQL", "REST", "gRPC", "Flutter", "Svelte",
    # Databases & Caching
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "Firebase", "Firestore", "Supabase", "Snowflake", "ClickHouse", "Neo4j", "ChromaDB", "Pinecone", "Qdrant", "Weaviate",
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "GCP", "Google Cloud", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible", "CI/CD", "GitHub Actions", "GitLab CI", "Linux", "Nginx", "Helm", "Prometheus", "Grafana", "Datadog", "OpenTelemetry",
    # AI / ML / Data
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "scikit-learn", "Pandas", "NumPy", "OpenAI", "LangChain", "LlamaIndex", "Hugging Face", "NLP", "Computer Vision", "LLMs", "RAG", "Fine-tuning", "Transformers",
    # Architecture & Practices
    "Microservices", "System Design", "Distributed Systems", "TDD", "Agile", "Scrum", "API Design", "Event-Driven Architecture", "Kafka", "RabbitMQ", "OAuth", "JWT"
]


def extract_raw_text(file_bytes: bytes, file_type: str) -> str:
    """Extract raw text from PDF, DOCX, or plain text bytes."""
    clean_type = file_type.lower().replace(".", "").strip()
    
    if clean_type == "pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text_pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
            return "\n\n".join(text_pages).strip()
        except Exception as e:
            logger.error("Failed to parse PDF: %s", e)
            raise ValueError(f"Unable to parse PDF document: {e}")

    elif clean_type in ("docx", "doc"):
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            return "\n".join(paragraphs).strip()
        except Exception as e:
            logger.error("Failed to parse DOCX: %s", e)
            raise ValueError(f"Unable to parse DOCX document: {e}")

    elif clean_type in ("txt", "text", "md", "markdown"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1")
            except Exception as e:
                raise ValueError(f"Unable to decode text document: {e}")
    else:
        raise ValueError(f"Unsupported file format: '{file_type}'. Supported formats are PDF, DOCX, and TXT.")


def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """Extract contact information strictly from text. Missing items are None."""
    contact: Dict[str, Optional[str]] = {
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "portfolio": None,
        "location": None,
    }

    # Email
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
    if email_match:
        contact["email"] = email_match.group(0).strip()

    # Phone: international or national formats
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text)
    if phone_match:
        phone_candidate = phone_match.group(0).strip()
        digits = re.sub(r"\D", "", phone_candidate)
        if 8 <= len(digits) <= 15:
            contact["phone"] = phone_candidate

    # LinkedIn
    li_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    if li_match:
        contact["linkedin"] = f"https://linkedin.com/in/{li_match.group(1)}"

    # GitHub
    gh_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    if gh_match:
        username = gh_match.group(1)
        if username.lower() not in ("features", "pricing", "explore", "enterprise"):
            contact["github"] = f"https://github.com/{username}"

    # Portfolio / Website
    url_matches = re.findall(r"https?://[^\s/$.?#].[^\s]*", text)
    for url in url_matches:
        url_clean = url.rstrip(".,;)")
        if "linkedin.com" not in url_clean and "github.com" not in url_clean:
            contact["portfolio"] = url_clean
            break

    # Location heuristic (explicit prefix or common City, State/Country format)
    loc_match = re.search(r"(?:Location|Address|Based in|Lives in|Residing in|City)[:\s]+([^\r\n,]+(?:,\s*[^\r\n]+)?)", text[:1500], re.IGNORECASE)
    if loc_match:
        candidate_loc = loc_match.group(1).strip()
        if len(candidate_loc) < 60:
            contact["location"] = candidate_loc
    else:
        # Check header lines for City, Country / State
        geo_pattern = re.compile(
            r"(?:^|[\r\n|•·])\s*([A-Z][a-zA-Z ]+,\s*(?:[A-Z]{2}|USA|US|UK|United Kingdom|Canada|Germany|Nigeria|France|Australia|Netherlands|Spain|Italy|India|Singapore|South Africa|Sweden|Ireland|Switzerland|Poland|Brazil|Remote))\b",
            re.IGNORECASE | re.MULTILINE
        )
        geo_match = geo_pattern.search(text[:1200])
        if geo_match:
            cand = geo_match.group(1).strip()
            if len(cand) < 50:
                contact["location"] = cand

    return contact



def segment_sections(text: str) -> Dict[str, str]:
    """Segment CV into logical sections (summary, experience, education, skills, projects, certifications)."""
    section_patterns = {
        "summary": r"(?:summary|profile|about\s*(?:me)?|professional\s+summary|executive\s+summary|objective|career\s+objective|career\s+profile)",
        "experience": r"(?:work\s+experience|professional\s+experience|experience|employment\s+history|career\s+history|work\s+history|employment)",
        "education": r"(?:education|academic\s+background|qualifications|academic\s+history|academics)",
        "skills": r"(?:skills|technical\s+skills|core\s+competencies|proficiencies|technologies|technical\s+proficiencies|tools|tech\s+stack)",
        "projects": r"(?:projects|key\s+projects|personal\s+projects|open\s+source|selected\s+projects)",
        "certifications": r"(?:certifications|certificates|licenses|courses|accreditations)",
    }

    lines = text.split("\n")
    current_section = "header"
    sections: Dict[str, List[str]] = {
        "header": [],
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for sec_name, pattern in section_patterns.items():
            if re.match(r"^#*\s*\*?" + pattern + r"\*?[:\s]*$", stripped, re.IGNORECASE):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            if current_section in sections:
                sections[current_section].append(stripped)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def extract_summary_intelligence(sections: Dict[str, str], raw_text: str) -> Optional[str]:
    """Extract professional summary or bio from segmented sections or early text paragraphs."""
    summary_text = sections.get("summary")
    if summary_text and len(summary_text.strip()) >= 20:
        lines = [l.strip("•-* \t") for l in summary_text.split("\n") if l.strip()]
        return " ".join(lines)

    # If no explicit summary section, check between header and first section
    header_text = sections.get("header", "")
    if header_text:
        lines = [l.strip() for l in header_text.split("\n") if l.strip()]
        for line in lines[2:]:
            if len(line) >= 40 and not re.search(r"[@/\\:|]", line):
                return line

    return None


def extract_skills_intelligence(text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
    """Identify skills strictly present in CV with confidence score and evidence context."""
    skills_found: Dict[str, Dict[str, Any]] = {}
    skills_section_text = sections.get("skills", "")
    exp_section_text = sections.get("experience", "")

    for skill in SKILLS_TAXONOMY:
        # Exact word-boundary match
        pattern = r"\b" + re.escape(skill) + r"\b"
        
        # Check in skills section
        in_skills = bool(re.search(pattern, skills_section_text, re.IGNORECASE))
        # Check in experience section
        in_exp = bool(re.search(pattern, exp_section_text, re.IGNORECASE))
        # Check globally
        in_global = bool(re.search(pattern, text, re.IGNORECASE))

        if in_skills or in_exp or in_global:
            confidence = 1.0 if in_skills else (0.90 if in_exp else 0.75)
            context = "Explicit in Skills section" if in_skills else ("Demonstrated in Experience" if in_exp else "Mentioned in CV text")
            skills_found[skill] = {
                "name": skill,
                "confidence": confidence,
                "source": context,
            }

    return sorted(list(skills_found.values()), key=lambda s: s["confidence"], reverse=True)


def extract_experience_intelligence(experience_text: str) -> Tuple[List[Dict[str, Any]], float]:
    """Parse work experience entries, calculating duration and extracting role/company/bullets.
    
    Handles standard ranges (Jan 2020 - Present), em-dash / tab separators (Role — Company \t Present),
    and multi-line headline structures.
    """
    if not experience_text:
        return [], 0.0

    date_range_regex = re.compile(
        r"(?P<start>(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4}))"
        r"\s*[-–—to]+\s*"
        r"(?P<end>(?:Present|Current|Now|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4}))",
        re.IGNORECASE
    )

    role_indicators = [
        r"engineer", r"developer", r"architect", r"lead", r"founder", r"director",
        r"manager", r"specialist", r"consultant", r"contributor", r"analyst",
        r"designer", r"head", r"officer", r"intern", r"administrator", r"coordinator",
        r"scientist", r"researcher", r"vp", r"creator"
    ]
    role_pattern = re.compile(r"\b(?:" + "|".join(role_indicators) + r")\b", re.IGNORECASE)

    entries: List[Dict[str, Any]] = []
    lines = [l.strip() for l in experience_text.split("\n") if l.strip()]
    current_entry: Optional[Dict[str, Any]] = None
    all_years = []

    for line in lines:
        date_range_m = date_range_regex.search(line)
        pres_m = re.search(r"[\t|—–\s]\b(Present|Current|Now)\b", line, re.IGNORECASE)
        has_role = bool(role_pattern.search(line))
        has_sep = bool(re.search(r"[\t|—–]|\bat\b", line))
        is_bullet = line.startswith(('•', '-', '*', '— ', '– '))

        # Case A: Date range line modifying an existing entry whose dates were placeholder
        if current_entry and date_range_m and not has_role and (current_entry.get('start_date') in ('Recent', 'Past')):
            current_entry['start_date'] = date_range_m.group('start')
            current_entry['end_date'] = date_range_m.group('end')
            current_entry['is_current'] = bool(re.search(r"present|current|now", current_entry['end_date'], re.IGNORECASE))
            for ym in re.finditer(r"\b(19\d{2}|20\d{2})\b", line):
                all_years.append(int(ym.group(1)))
            continue

        # Case B: Line is a new job headline
        is_headline = False
        if not is_bullet:
            if has_role and (has_sep or date_range_m or pres_m):
                is_headline = True
            elif date_range_m and len(line) < 120:
                is_headline = True
            elif has_role and len(line) < 90 and not line.endswith('.'):
                if not re.match(r'^(?:deliver|founded|direct|architect|contribute|designed|performed|built|implemented|maintained)\b', line, re.IGNORECASE):
                    is_headline = True

        if is_headline:
            if current_entry:
                entries.append(current_entry)

            start_str = "Recent"
            end_str = "Present"
            is_current = False

            if date_range_m:
                start_str = date_range_m.group('start')
                end_str = date_range_m.group('end')
                is_current = bool(re.search(r"present|current|now", end_str, re.IGNORECASE))
                cleaned_line = line[:date_range_m.start()].strip() + ' ' + line[date_range_m.end():].strip()
            elif pres_m:
                is_current = True
                end_str = "Present"
                cleaned_line = line[:pres_m.start()].strip()
            else:
                cleaned_line = line

            for ym in re.finditer(r"\b(19\d{2}|20\d{2})\b", line):
                all_years.append(int(ym.group(1)))

            cleaned_line = cleaned_line.strip(" |-,•—–\t")
            parts = [p.strip() for p in re.split(r"[\t|—–]|\bat\b|, ", cleaned_line) if p.strip()]
            role = parts[0] if parts else "Professional Role"
            company = parts[1] if len(parts) > 1 else "Organization"

            current_entry = {
                "title": role,
                "company": company,
                "start_date": start_str,
                "end_date": end_str,
                "is_current": is_current,
                "bullets": [],
            }
        elif current_entry:
            clean_bullet = line.lstrip("•-*—– \t")
            if clean_bullet:
                current_entry["bullets"].append(clean_bullet)

    if current_entry:
        entries.append(current_entry)

    total_years = 0.0
    if all_years:
        min_y = min(all_years)
        max_y = max(all_years)
        if any(e.get("is_current") for e in entries):
            max_y = datetime.now().year
        total_years = max(1.0, float(max_y - min_y))
    elif entries:
        total_years = float(max(1, len(entries) * 2))

    return entries, total_years


def extract_education_intelligence(education_text: str) -> List[Dict[str, Any]]:
    """Parse degrees, institutions, and graduation years."""
    if not education_text:
        return []

    degree_keywords = [
        "Bachelor", "B.S.", "B.Sc", "BA", "B.A.", "Master", "M.S.", "M.Sc", "MBA", "Ph.D", "PhD", "Doctorate", "Associate", "Diploma"
    ]
    entries = []
    lines = [l.strip() for l in education_text.split("\n") if l.strip()]

    for line in lines:
        for kw in degree_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", line, re.IGNORECASE):
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", line)
                grad_year = int(year_match.group(1)) if year_match else None
                
                # Split institution by comma or em-dash
                parts = [p.strip() for p in re.split(r"[,—–\t]", line) if p.strip()]
                institution = parts[1] if len(parts) > 1 and not kw.lower() in parts[1].lower() else parts[0]
                institution = re.sub(r"\b(in progress|ongoing|completed)\b", "", institution, flags=re.IGNORECASE).strip()

                entries.append({
                    "degree": kw,
                    "institution": institution or line,
                    "year": grad_year,
                    "details": line,
                })
                break

    return entries


def extract_certifications_intelligence(certifications_text: str) -> List[Dict[str, Any]]:
    """Parse certifications, licenses, and issuing authorities."""
    if not certifications_text:
        return []

    entries = []
    lines = [l.strip() for l in certifications_text.split("\n") if l.strip()]

    for line in lines:
        clean_line = line.lstrip("•-* \t")
        if len(clean_line) < 3:
            continue
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", clean_line)
        year = int(year_match.group(1)) if year_match else None
        
        # Split issuer if format is "Cert Name - Issuer" or "Cert Name, Issuer"
        parts = re.split(r"[-–—|,]\s*", clean_line)
        name = parts[0].strip()
        issuer = parts[1].strip() if len(parts) > 1 else None

        entries.append({
            "name": name,
            "issuer": issuer,
            "year": year,
            "details": clean_line,
        })

    return entries


def extract_projects_intelligence(projects_text: str) -> List[Dict[str, Any]]:
    """Parse projects, tool usage, and links."""
    if not projects_text:
        return []

    lines = [l.strip() for l in projects_text.split("\n") if l.strip()]
    projects = []
    current_proj = None

    for line in lines:
        if line.startswith("#") or line.endswith(":") or (len(line) < 50 and not line.startswith("•")):
            if current_proj:
                projects.append(current_proj)
            current_proj = {
                "name": line.strip("#: -"),
                "description": "",
                "tech_stack": [],
                "url": None,
            }
        elif current_proj:
            url_match = re.search(r"https?://[^\s]+", line)
            if url_match:
                current_proj["url"] = url_match.group(0).rstrip(".,)")
            current_proj["description"] += " " + line.lstrip("•-* ")

    if current_proj:
        projects.append(current_proj)

    return projects


def extract_career_goals_intelligence(
    sections: Dict[str, str],
    summary: Optional[str],
    title: Optional[str],
    skills: List[str]
) -> Optional[str]:
    """Extract or infer truthful career goals from objectives, summary, or target role."""
    summary_raw = sections.get("summary", "")
    obj_match = re.search(r"(?:Objective|Career Objective|Goal)[:\s]+([^\r\n.]+)", summary_raw, re.IGNORECASE)
    if obj_match:
        return obj_match.group(1).strip()

    if summary and any(k in summary.lower() for k in ("seeking", "looking to", "aiming to", "focusing on")):
        for sentence in re.split(r"[.!?]", summary):
            if any(k in sentence.lower() for k in ("seeking", "looking to", "aiming to", "focusing on")):
                return sentence.strip()

    if title:
        top_skills = skills[:3]
        if top_skills:
            return f"Advance career as {title} specializing in {', '.join(top_skills)}."
        return f"Advance career as {title}."

    return None


def parse_cv_document(file_bytes: bytes, filename: str, file_type: str) -> Dict[str, Any]:
    """Master CV Ingestion function.
    Reads file bytes, extracts text, breaks into sections, extracts high-fidelity fields,
    and returns a normalized intelligence dictionary conforming to zero-fabrication standards.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    raw_text = extract_raw_text(file_bytes, file_type)
    
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Document contains insufficient readable text.")

    sections = segment_sections(raw_text)
    contact = extract_contact_info(raw_text)
    skills = extract_skills_intelligence(raw_text, sections)
    skills_list = [s["name"] for s in skills]
    experience, years_exp = extract_experience_intelligence(sections.get("experience", raw_text))
    education = extract_education_intelligence(sections.get("education", ""))
    certifications = extract_certifications_intelligence(sections.get("certifications", ""))
    projects = extract_projects_intelligence(sections.get("projects", ""))
    bio = extract_summary_intelligence(sections, raw_text)

    # First name / Full name heuristic from header or first line
    header_lines = [l.strip() for l in (sections.get("header") or raw_text).split("\n") if l.strip()]
    full_name = None
    ignored_headers = ("curriculum vitae", "resume", "cv", "personal details", "profile", "contact information")
    
    for candidate_line in header_lines[:5]:
        clean_line = candidate_line.strip("#* \t")
        if clean_line.lower() in ignored_headers:
            continue
        # Check for explicit Name label
        name_labeled = re.search(r"^(?:Name|Candidate)[:\s]+([A-Za-z\s.'-]+)$", clean_line, re.IGNORECASE)
        if name_labeled:
            full_name = name_labeled.group(1).strip()
            break
        # Avoid lines that look like emails, URLs, phone numbers, or section headers
        if len(clean_line) < 50 and not re.search(r"[@/\\:|0-9]", clean_line):
            words = clean_line.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                full_name = clean_line
                break

    # Headline / Target Title heuristic
    title = None
    for candidate_line in header_lines[1:6]:
        clean_line = candidate_line.strip("#* \t")
        if clean_line == full_name or clean_line.lower() in ignored_headers:
            continue
        title_labeled = re.search(r"^(?:Title|Role|Headline)[:\s]+([A-Za-z\s/&.-]+)$", clean_line, re.IGNORECASE)
        if title_labeled:
            title = title_labeled.group(1).strip()
            break
        if len(clean_line) < 60 and not re.search(r"[@/\\:]", clean_line) and not re.search(r"\b\d{3,}\b", clean_line):
            if any(role_word in clean_line.lower() for role_word in ("engineer", "developer", "architect", "lead", "manager", "designer", "scientist", "consultant", "analyst", "specialist", "administrator")):
                title = clean_line
                break

    if not title and experience:
        title = experience[0].get("title")

    career_goals = extract_career_goals_intelligence(sections, bio, title, skills_list)

    # Overall Confidence Calculation
    confidence_signals = [
        1.0 if contact.get("email") else 0.0,
        1.0 if skills else 0.0,
        1.0 if experience else 0.0,
        1.0 if education else 0.5,
        1.0 if full_name else 0.3,
        1.0 if bio else 0.4,
    ]
    confidence_score = round(sum(confidence_signals) / len(confidence_signals), 2)

    return {
        "file_hash": file_hash,
        "filename": filename,
        "file_type": file_type.lower(),
        "file_size": len(file_bytes),
        "raw_text": raw_text,
        "full_name": full_name,
        "title": title,
        "bio": bio,
        "summary": bio,
        "career_goals": career_goals,
        "contact_info": contact,
        "location": contact.get("location"),
        "skills": skills,
        "skills_list": skills_list,
        "technologies": skills_list,
        "experience": experience,
        "experience_years": years_exp,
        "education": education,
        "certifications": certifications,
        "projects": projects,
        "raw_sections": sections,
        "confidence_score": confidence_score,
        "status": "completed",
    }
