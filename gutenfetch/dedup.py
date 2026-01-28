"""Deduplication and author filtering for search results."""

from __future__ import annotations

import re

from gutenfetch.models import Book


def deduplicate(books: list[Book]) -> list[Book]:
    """Remove duplicate works, keeping the one with the highest download count."""
    seen: dict[str, Book] = {}
    for book in books:
        key = _normalize_title(book.title)
        if key not in seen or book.download_count > seen[key].download_count:
            seen[key] = book
    return sorted(seen.values(), key=lambda b: b.download_count, reverse=True)


def filter_by_author(books: list[Book], author_query: str) -> list[Book]:
    """Keep only books where the queried author name matches an actual author."""
    query_parts = _name_parts(author_query)
    return [b for b in books if _author_matches(b, query_parts)]


def filter_has_text(books: list[Book]) -> list[Book]:
    """Keep only books that have a plain-text download URL."""
    return [b for b in books if b.text_url is not None]


def _author_matches(book: Book, query_parts: set[str]) -> bool:
    """Check if any author on the book matches the query name parts."""
    for author in book.authors:
        author_parts = _name_parts(author.name)
        if query_parts.issubset(author_parts):
            return True
    return False


def _name_parts(name: str) -> set[str]:
    """Extract lowercase name parts, stripping punctuation."""
    cleaned = re.sub(r"[^a-z\s]", "", name.lower())
    return {p for p in cleaned.split() if len(p) > 1}


def _normalize_title(title: str) -> str:
    """Normalize a title for dedup comparison."""
    title = title.lower()
    # Remove subtitle after colon, semicolon, or dash
    title = re.split(r"[:;—–\-]", title)[0]
    # Remove leading articles
    title = re.sub(r"^(the|a|an)\s+", "", title.strip())
    # Remove punctuation and collapse whitespace
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title
