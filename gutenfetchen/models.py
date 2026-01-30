"""Data models for gutenfetchen."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Author:
    """A Project Gutenberg author."""

    name: str
    birth_year: int | None = None
    death_year: int | None = None

    @property
    def display_name(self) -> str:
        """Convert 'Last, First' to 'First Last'."""
        if ", " in self.name:
            parts = self.name.split(", ", 1)
            return f"{parts[1]} {parts[0]}"
        return self.name


@dataclass
class Book:
    """A Project Gutenberg book."""

    id: int
    title: str
    authors: list[Author] = field(default_factory=list)
    formats: dict[str, str] = field(default_factory=dict)
    download_count: int = 0
    languages: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    media_type: str = "Text"

    @property
    def text_url(self) -> str | None:
        """Best plain-text URL, preferring UTF-8."""
        for mime in [
            "text/plain; charset=utf-8",
            "text/plain; charset=us-ascii",
        ]:
            if mime in self.formats:
                return self.formats[mime]
        for mime, url in self.formats.items():
            if mime.startswith("text/plain"):
                return url
        return None


@dataclass
class SearchResult:
    """Paginated search result from Gutendex."""

    count: int
    books: list[Book] = field(default_factory=list)
    next_url: str | None = None
