from __future__ import annotations

from .config import normalize_journal_name


def classify_article(publication_types: list[str]) -> str:
    normalized_types = {publication_type.casefold() for publication_type in publication_types}
    if any("review" in publication_type for publication_type in normalized_types):
        return "Review"
    return "Original article"


def classify_journal_priority(journal: str, whitelist: set[str]) -> str:
    if normalize_journal_name(journal) in whitelist:
        return "high-priority"
    return "normal"
