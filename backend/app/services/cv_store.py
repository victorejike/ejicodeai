"""Storage and file rendering for the CVs the agents build.

Two callers need the same mapping - the CV builder stage of the pipeline and
``POST /individual/cv/build`` - and the download endpoint has to be able to
re-render a stored CV months later. Keeping the column mapping, the version
counter and the renderer selection here means a CV downloaded from history is
byte-for-byte the same document the agent produced.

``content_text`` is the source of truth. ``.docx`` and ``.pdf`` are derived from
it on demand, which is precisely why the output stays machine-readable: there is
no second, richer representation that could drift away from the extractable text.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import GeneratedCV

logger = logging.getLogger(__name__)

#: Formats ``GET /cv/{id}/download`` can serve.
DOWNLOAD_FORMATS: Tuple[str, ...] = ("txt", "docx", "pdf")

_MEDIA_TYPES = {
    "txt": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def to_row_values(cv: Dict[str, Any]) -> Dict[str, Any]:
    """Map one ``CVBuilderAgent.build()`` result onto ``GeneratedCV`` columns."""
    target_title = cv.get("target_title")
    target_company = cv.get("target_company")
    if target_title and target_company:
        label = f"{target_title} - {target_company}"
    else:
        label = target_title or "General CV"

    return {
        "opportunity_id": _as_uuid(cv.get("target_opportunity_id")),
        "label": label,
        "target_title": target_title,
        "target_company": target_company,
        "content_text": cv.get("content_text") or "",
        "sections": cv.get("sections") or {},
        "cover_letter": cv.get("cover_letter"),
        "ats_score": int(cv.get("ats_score") or 0),
        "ats_breakdown": {
            "components": cv.get("breakdown") or {},
            "maximums": cv.get("breakdown_maximums") or {},
            "measured_out_of": cv.get("measured_out_of"),
            "word_count": cv.get("word_count"),
            "recommendations": cv.get("recommendations") or [],
            "headings_used": cv.get("headings_used") or [],
            "keywords_required": cv.get("keywords_required") or [],
        },
        "keywords_matched": cv.get("keywords_matched") or [],
        "keywords_missing": cv.get("keywords_missing") or [],
        "format_warnings": cv.get("issues") or [],
        # "ai" only when the provider's summary survived the truthfulness check.
        "generator": "ai" if cv.get("summary_source") == "ai" else "template",
    }


async def next_version(user_id: uuid.UUID, db: AsyncSession) -> int:
    """One monotonic version counter per user, so history reads chronologically."""
    current = (
        await db.execute(
            select(func.max(GeneratedCV.version)).where(GeneratedCV.user_id == user_id)
        )
    ).scalar()
    return int(current or 0) + 1


async def save_generated_cvs(
    user_id: uuid.UUID,
    cvs: Sequence[Dict[str, Any]],
    db: AsyncSession,
    *,
    commit: bool = True,
) -> Dict[str, Any]:
    """Persist each built CV; writes ``cv_id``/``version`` back onto the dicts.

    Writing the ids back is what lets a later stage (outreach, the UI's download
    button) point at a stored document rather than at an in-memory dict.
    """
    usable = [cv for cv in cvs if isinstance(cv, dict) and cv.get("content_text")]
    if not usable:
        return {"saved": 0, "rows": [], "best_ats_score": None}

    version = await next_version(user_id, db)
    pairs: List[Tuple[Dict[str, Any], GeneratedCV]] = []

    for cv in usable:
        row = GeneratedCV(user_id=user_id, version=version, **to_row_values(cv))
        version += 1
        db.add(row)
        pairs.append((cv, row))

    await db.flush()
    if commit:
        await db.commit()

    for cv, row in pairs:
        cv["cv_id"] = str(row.id)
        cv["version"] = row.version

    logger.info("CV store: saved %d CVs for user %s", len(pairs), user_id)
    return {
        "saved": len(pairs),
        "rows": [row for _, row in pairs],
        "best_ats_score": max(int(cv.get("ats_score") or 0) for cv in usable),
    }


def cv_summary(row: GeneratedCV) -> Dict[str, Any]:
    """Compact shape for the version list."""
    return {
        "id": str(row.id),
        "version": row.version,
        "label": row.label,
        "target_title": row.target_title,
        "target_company": row.target_company,
        "opportunity_id": str(row.opportunity_id) if row.opportunity_id else None,
        "ats_score": row.ats_score,
        "keywords_matched": row.keywords_matched or [],
        "keywords_missing": row.keywords_missing or [],
        "generator": row.generator,
        "is_general": row.opportunity_id is None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "formats": list(DOWNLOAD_FORMATS),
    }


def cv_detail(row: GeneratedCV) -> Dict[str, Any]:
    """Full shape, including the text the ATS would read."""
    return {
        **cv_summary(row),
        "content_text": row.content_text,
        "sections": row.sections or {},
        "cover_letter": row.cover_letter,
        "ats_breakdown": row.ats_breakdown or {},
        "format_warnings": row.format_warnings or [],
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _slug(text: Optional[str], fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-")
    return (cleaned or fallback)[:60]


def render(row: GeneratedCV, fmt: str) -> Tuple[bytes, str, str]:
    """Render a stored CV. Returns ``(body, media_type, filename)``."""
    if fmt not in DOWNLOAD_FORMATS:
        raise ValueError(f"Unsupported format '{fmt}'. Use one of: {', '.join(DOWNLOAD_FORMATS)}")

    from agents.cv_builder.cv_builder_agent import ATS_HEADINGS
    from agents.cv_builder.renderers import render_docx, render_pdf

    text = row.content_text or ""
    headings = tuple((row.sections or {}).keys()) or ATS_HEADINGS

    if fmt == "txt":
        body = text.encode("utf-8")
    elif fmt == "docx":
        body = render_docx(text, headings)
    else:
        body = render_pdf(text, headings)

    name_part = _slug((text.splitlines() or [""])[0], "CV")
    target_part = _slug(row.target_company or row.target_title, "General")
    filename = f"{name_part}-{target_part}-v{row.version}.{fmt}"
    return body, _MEDIA_TYPES[fmt], filename
