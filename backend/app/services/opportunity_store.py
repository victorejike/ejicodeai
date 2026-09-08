"""Persistence for the opportunities an agent run brings back.

One place decides how a scraped/validated/scored dict becomes an ``Opportunity``
row, because two callers already need it - ``POST /individual/search`` and the
career pipeline - and a second copy of the mapping is how the two would start
disagreeing about what "the same job" means.

Two rules the rest of the system depends on:

* a row is **one user's view** of a posting, so identity is
  ``(user_id, source_url)`` and never ``source_url`` alone;
* a field is only overwritten when the incoming record actually carries a
  value. A later, thinner sighting of the same job must not erase the
  description or the score an earlier one established.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Opportunity

logger = logging.getLogger(__name__)

#: Numeric trust fields are left NULL rather than defaulted: an unverified
#: posting must not look verified to the user.
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%a, %d %b %Y %H:%M:%S %z")


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Best-effort ISO/RFC date parse; ``None`` when the source did not say."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reliability(record: Dict[str, Any]) -> Optional[int]:
    """Reliability the record already carries, else the source's known tier."""
    stated = _as_int(record.get("source_reliability_score"))
    if stated is not None:
        return stated
    source = record.get("source") or record.get("source_platform")
    if not source:
        return None
    from agents.scrapers.adapters import ScraperRegistry

    return ScraperRegistry.source_reliability(str(source))


def to_column_values(record: Dict[str, Any]) -> Dict[str, Any]:
    """Map one agent-shaped opportunity dict onto ``Opportunity`` columns.

    Keys whose value is ``None`` are omitted, so the caller can apply this over
    an existing row without clearing what is already known.
    """
    safety = record.get("safety") if isinstance(record.get("safety"), dict) else {}
    confidence = (
        record.get("confidence_scores") if isinstance(record.get("confidence_scores"), dict) else {}
    )

    # The pipeline's matching stage names it match_score; a raw scrape has none.
    score = _as_int(record.get("match_score"))
    if score is None:
        score = _as_int(record.get("score"))

    verification = _as_int(safety.get("verification_confidence"))
    if verification is None and confidence.get("overall_confidence") is not None:
        overall = _as_float(confidence.get("overall_confidence"))
        verification = _as_int(overall * 100) if overall is not None else None

    values: Dict[str, Any] = {
        "title": (record.get("title") or "").strip() or None,
        "type": record.get("type") or record.get("employment_type"),
        "pipeline_type": record.get("pipeline_type"),
        "source_platform": record.get("source") or record.get("source_platform"),
        "raw_description": record.get("description") or record.get("raw_description"),
        "location": record.get("location"),
        "location_type": record.get("location_type"),
        "salary_min": _as_float(record.get("salary_min")),
        "salary_max": _as_float(record.get("salary_max")),
        "salary_currency": record.get("salary_currency"),
        "tech_required": list(record.get("tech_required") or []) or None,
        "all_sources": list(record.get("all_sources") or []) or None,
        "score": score,
        "score_breakdown": record.get("score_breakdown") or None,
        "quality_score": _as_int(record.get("quality_score")),
        "source_reliability_score": _reliability(record),
        "safety_status": safety.get("safety_status") or record.get("safety_status"),
        "verification_confidence": verification,
        "freshness_status": record.get("freshness_status"),
        "rank": _as_int(record.get("rank")),
        "posted_at": _parse_datetime(record.get("posted_at") or record.get("posted_date")),
        "expires_at": _parse_datetime(record.get("expires_at")),
    }
    return {key: value for key, value in values.items() if value is not None}


async def save_scored_opportunities(
    user_id: uuid.UUID,
    records: Sequence[Dict[str, Any]],
    db: AsyncSession,
    *,
    commit: bool = True,
) -> Dict[str, Any]:
    """Upsert this user's copy of every record and return what changed.

    ``ids`` maps ``source_url`` to the stored row id, which is how a later stage
    (the CV builder, outreach) links its own output to a real opportunity instead
    of to a dict that only existed in memory.
    """
    created = 0
    updated = 0
    skipped = 0
    pending: Dict[str, Opportunity] = {}

    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue
        source_url = (record.get("source_url") or "").strip()
        title = (record.get("title") or "").strip()
        if not source_url or not title:
            # Without a URL there is nothing to dedupe on and nothing for the
            # user to open; without a title there is nothing to show.
            skipped += 1
            continue

        values = to_column_values(record)
        row = pending.get(source_url)
        if row is None:
            row = (
                await db.execute(
                    select(Opportunity).where(
                        Opportunity.user_id == user_id,
                        Opportunity.source_url == source_url,
                    )
                )
            ).scalars().first()

        if row is None:
            row = Opportunity(
                user_id=user_id,
                source_url=source_url,
                title=title,
                type=values.get("type") or "full-time",
                freshness_status=values.get("freshness_status") or "OPEN",
            )
            for column, value in values.items():
                setattr(row, column, value)
            db.add(row)
            created += 1
        else:
            for column, value in values.items():
                setattr(row, column, value)
            updated += 1
        pending[source_url] = row

    if pending:
        await db.flush()
        if commit:
            await db.commit()

    logger.info(
        "Opportunity store: %d created, %d updated, %d skipped for user %s",
        created, updated, skipped, user_id,
    )
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "ids": {url: str(row.id) for url, row in pending.items()},
    }


def attach_stored_ids(
    records: Iterable[Dict[str, Any]],
    ids: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Return the records with their stored row id under ``id``.

    Done as a copy so the stage output that gets persisted is the version that
    carries the ids - the next stage reads the same dicts the database holds.
    """
    out: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        stored_id = ids.get((record.get("source_url") or "").strip())
        out.append({**record, "id": stored_id} if stored_id else dict(record))
    return out
