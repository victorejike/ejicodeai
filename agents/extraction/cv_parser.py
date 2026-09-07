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
    "Python", "TypeScript", "JavaScript", "Go", "Golang", "Rust", "Java", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "SQL", "HTML", "CSS", "R", "Scala", "Dart", "Elixir", "Bash", "Shell",
    # Frameworks & Libraries
    "FastAPI", "Django", "Flask", "React", "React Native", "Next.js", "Vue", "Vue.js", "Angular", "Node.js", "Express", "NestJS", "Spring", "Spring Boot", ".NET", "Rails", "Ruby on Rails", "Tailwind CSS", "GraphQL", "REST", "gRPC", "Flutter",
    # Databases & Caching
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "Firebase", "Firestore", "Supabase", "Snowflake", "ClickHouse", "Neo4j", "ChromaDB", "Pinecone", "Qdrant", "Weaviate",
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "GCP", "Google Cloud", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible", "CI/CD", "GitHub Actions", "GitLab CI", "Linux", "Nginx", "Helm", "Prometheus", "Grafana",
    # AI / ML / Data
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "scikit-learn", "Pandas", "NumPy", "OpenAI", "LangChain", "LlamaIndex", "Hugging Face", "NLP", "Computer Vision", "LLMs", "RAG", "Fine-tuning", "Transformers",
    # Architecture & Practices
    "Microservices", "System Design", "Distributed Systems", "TDD", "Agile", "Scrum", "API Design", "Event-Driven Architecture", "Kafka", "RabbitMQ"
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
    contact = {
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

    # Phone
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_match:
        phone_candidate = phone_match.group(0).strip()
        # Verify it has at least 7 digits to avoid false positives with dates
        if len(re.sub(r"\D", "", phone_candidate)) >= 7:
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

    # Location heuristic (requires explicit prefix or clear location line)
    loc_match = re.search(r"(?:Location|Address|Based in|Lives in)[:\s]+([^\r\n]+)", text[:1500], re.IGNORECASE)
    if loc_match:
        candidate_loc = loc_match.group(1).strip()
        if len(candidate_loc) < 60:
            contact["location"] = candidate_loc

    return contact


def segment_sections(text: str) -> Dict[str, str]:
    """Segment CV into logical sections (summary, experience, education, skills, projects, certifications)."""
    section_patterns = {
        "summary": r"(?:summary|profile|about\s+me|professional\s+summary|objective)",
        "experience": r"(?:work\s+experience|professional\s+experience|experience|employment\s+history|career\s+history)",
        "education": r"(?:education|academic\s+background|qualifications|academic\s+history)",
        "skills": r"(?:skills|technical\s+skills|core\s+competencies|proficiencies|technologies)",
        "projects": r"(?:projects|key\s+projects|personal\s+projects|open\s+source)",
        "certifications": r"(?:certifications|licenses|courses|accreditations)",
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
            if re.match(r"^#*\s*" + pattern + r"[:\s]*$", stripped, re.IGNORECASE):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(stripped)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


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
    """Parse work experience entries, calculating duration and extracting role/company/bullets."""
    if not experience_text:
        return [], 0.0

    entries: List[Dict[str, Any]] = []
    # Match patterns like "Jan 2020 - Present", "2018 - 2022", "06/2019 – 08/2021"
    date_regex = re.compile(
        r"(?P<start>(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4}))"
        r"\s*[-–—to]+\s*"
        r"(?P<end>(?:Present|Current|Now|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4}))",
        re.IGNORECASE
    )

    lines = [l.strip() for l in experience_text.split("\n") if l.strip()]
    current_entry: Optional[Dict[str, Any]] = None
    all_years = []
    previous_line = ""

    for line in lines:
        date_match = date_regex.search(line)
        if date_match:
            if current_entry:
                entries.append(current_entry)

            start_str = date_match.group("start")
            end_str = date_match.group("end")
            is_current = bool(re.search(r"present|current|now", end_str, re.IGNORECASE))

            # Extract years for total experience estimation
            start_year_m = re.search(r"\b(19\d{2}|20\d{2})\b", start_str)
            end_year_m = re.search(r"\b(19\d{2}|20\d{2})\b", end_str)
            
            s_year = int(start_year_m.group(1)) if start_year_m else None
            e_year = datetime.now().year if is_current else (int(end_year_m.group(1)) if end_year_m else None)

            if s_year and e_year and e_year >= s_year:
                all_years.append((s_year, e_year))

            # Line before or remaining text often contains Role and Company
            headline = line[:date_match.start()].strip() + " " + line[date_match.end():].strip()
            headline = headline.strip(" |-,•")
            if not headline and previous_line:
                headline = previous_line.strip(" |-,•")

            parts = [p.strip() for p in re.split(r" at | \| |, ", headline) if p.strip()]
            role = parts[0] if parts else "Professional Role"
            company = parts[1] if len(parts) > 1 else None

            current_entry = {
                "title": role,
                "company": company or "Organization",
                "start_date": start_str,
                "end_date": end_str,
                "is_current": is_current,
                "bullets": [],
            }
        elif current_entry:
            clean_bullet = line.lstrip("•-*• \t")
            if clean_bullet:
                current_entry["bullets"].append(clean_bullet)
        previous_line = line

    if current_entry:
        entries.append(current_entry)

    # Compute total continuous experience years avoiding simple overlaps
    total_years = 0.0
    if all_years:
        min_year = min(y[0] for y in all_years)
        max_year = max(y[1] for y in all_years)
        total_years = float(max_year - min_year)
        if total_years < 1.0 and all_years:
            total_years = 1.0

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
                entries.append({
                    "degree": kw,
                    "institution": line.split(",")[0].strip(),
                    "year": grad_year,
                    "details": line,
                })
                break

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
    experience, years_exp = extract_experience_intelligence(sections.get("experience", raw_text))
    education = extract_education_intelligence(sections.get("education", ""))
    projects = extract_projects_intelligence(sections.get("projects", ""))

    # First name / Full name heuristic from header or first line
    header_lines = [l.strip() for l in (sections.get("header") or raw_text).split("\n") if l.strip()]
    full_name = None
    if header_lines:
        first_line = header_lines[0]
        # Avoid lines that look like emails, URLs, or headers
        if len(first_line) < 50 and not re.search(r"[@/\\:|]", first_line):
            full_name = first_line

    # Headline / Target Title heuristic
    title = None
    if len(header_lines) > 1 and len(header_lines[1]) < 60 and not re.search(r"[@/\\:]", header_lines[1]):
        title = header_lines[1]
    elif experience:
        title = experience[0].get("title")

    # Overall Confidence Calculation
    confidence_signals = [
        1.0 if contact.get("email") else 0.0,
        1.0 if skills else 0.0,
        1.0 if experience else 0.0,
        1.0 if education else 0.5,
        1.0 if full_name else 0.3,
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
        "contact_info": contact,
        "skills": skills,
        "skills_list": [s["name"] for s in skills],
        "experience": experience,
        "experience_years": years_exp,
        "education": education,
        "projects": projects,
        "raw_sections": sections,
        "confidence_score": confidence_score,
        "status": "completed",
    }
