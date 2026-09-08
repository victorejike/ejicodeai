"""Deterministic skill extraction from CV / profile text.

The vocabulary lives in ``agents/data/skill_keywords.json`` rather than in an
agent, so adding a skill does not mean editing agent logic - and so the same
vocabulary is used everywhere skills are read out of text (CV parsing, keyword
gap analysis for the ATS CV builder, requirement extraction from a job post).

This is the *fallback* path: when an AI provider is configured the agents ask it
first and use this to backfill. With no keys at all the product still works.
"""
from __future__ import annotations

import functools
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

VOCABULARY_PATH = Path(__file__).resolve().parents[1] / "data" / "skill_keywords.json"


@functools.lru_cache(maxsize=1)
def _vocabulary() -> Tuple[Tuple[str, str, "re.Pattern[str]"], ...]:
    """``(canonical name, category, compiled alias pattern)`` for every known skill."""
    try:
        raw = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - shipped with the package
        logger.error("Could not load skill vocabulary from %s: %s", VOCABULARY_PATH, exc)
        return ()

    compiled: List[Tuple[str, str, "re.Pattern[str]"]] = []
    for entry in raw.get("skills", []):
        name = entry.get("name")
        if not name:
            continue
        aliases = entry.get("aliases") or [name]
        # An alias may already carry its own \b anchors; only add them when it
        # starts with a normal character, so "c\+\+" and "\br\b" both work.
        parts = []
        for alias in aliases:
            pattern = alias if alias.startswith("\\b") or alias.endswith("\\b") else rf"(?<![\w+#]){alias}(?![\w+#])"
            parts.append(pattern)
        try:
            compiled.append((name, entry.get("category") or "other", re.compile("|".join(parts), re.I)))
        except re.error as exc:
            logger.warning("Skipping skill '%s' with invalid alias pattern: %s", name, exc)
    return tuple(compiled)


def known_skills() -> List[str]:
    """Every canonical skill name in the vocabulary."""
    return [name for name, _, _ in _vocabulary()]


def extract_skills(text: Optional[str], *, limit: Optional[int] = None) -> List[str]:
    """Canonical skill names that literally appear in ``text``.

    Order follows the vocabulary, so results are stable across runs. Nothing is
    inferred: a skill is only reported when its name or an alias is present.
    """
    if not text:
        return []
    haystack = str(text)
    found = [name for name, _, pattern in _vocabulary() if pattern.search(haystack)]
    return found[:limit] if limit else found


def extract_skills_by_category(text: Optional[str]) -> Dict[str, List[str]]:
    """Same as :func:`extract_skills` but grouped, e.g. ``{"language": ["Python"]}``."""
    grouped: Dict[str, List[str]] = {}
    if not text:
        return grouped
    haystack = str(text)
    for name, category, pattern in _vocabulary():
        if pattern.search(haystack):
            grouped.setdefault(category, []).append(name)
    return grouped


def canonicalize(values: Optional[Iterable[Any]]) -> List[str]:
    """Map free-text skill labels onto canonical names, keeping unknown ones as-is.

    ``["fastapi", "postgres", "Stakeholder mgmt"]`` ->
    ``["FastAPI", "PostgreSQL", "Stakeholder mgmt"]``. Unrecognised entries are
    preserved because a user's own wording for their skill is still their skill.
    """
    if not values:
        return []
    vocabulary = _vocabulary()
    out: List[str] = []
    seen: set = set()
    for value in values:
        label = str(value).strip()
        if not label:
            continue
        canonical = label
        for name, _, pattern in vocabulary:
            if pattern.fullmatch(label) or (len(label) > 1 and pattern.search(label) and len(label) <= len(name) + 4):
                canonical = name
                break
        key = canonical.lower()
        if key not in seen:
            seen.add(key)
            out.append(canonical)
    return out
