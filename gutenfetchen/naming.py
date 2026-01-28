"""Filename generation for downloaded texts."""

from __future__ import annotations

import re

from gutenfetchen.models import Book


def make_filename(book: Book) -> str:
    """Generate a clean filename: 'first-last--title.txt'."""
    author_part = slugify(book.authors[0].display_name) if book.authors else "unknown"
    title_part = slugify(book.title)
    return f"{author_part}--{title_part}.txt"


def slugify(text: str) -> str:
    """Convert text to a lowercase-hyphenated slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:80]
