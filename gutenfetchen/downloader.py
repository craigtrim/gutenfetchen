"""Download plain-text files from Project Gutenberg."""

from __future__ import annotations

import re
from pathlib import Path

import requests
from rich.console import Console

from gutenfetchen.cleaner import clean_file
from gutenfetchen.models import Book
from gutenfetchen.naming import make_filename

console = Console()

# Media file extensions that indicate a file listing, not prose.
_MEDIA_EXT_RE = re.compile(r"\.\s*(mp3|mp4|ogg|wav|flac|m4a|m3u|aac)\b", re.IGNORECASE)

# Minimum non-blank lines expected in a real book after START/END extraction.
_MIN_PROSE_LINES = 50


def _validate_content(text: str, title: str) -> None:
    """Raise ValueError if *text* does not look like a plain-text book.

    Checks applied (Issue #3):
      1. Must contain a ``*** START`` marker (standard Gutenberg format).
      2. Must have at least ``_MIN_PROSE_LINES`` non-blank lines between
         the START and END markers.
      3. Must not be predominantly media file references (.mp3, .mp4, etc.).
    """
    lines = text.splitlines()

    has_start = any("*** START" in line for line in lines)
    if not has_start:
        raise ValueError(f"Rejected '{title}': no *** START marker — not a standard Gutenberg text")

    # Count non-blank lines between START and END
    inside = False
    content_lines = 0
    for line in lines:
        if "*** START" in line:
            inside = True
            continue
        if "*** END" in line:
            break
        if inside and line.strip():
            content_lines += 1

    if content_lines < _MIN_PROSE_LINES:
        raise ValueError(
            f"Rejected '{title}': only {content_lines} content lines — likely not prose"
        )

    # Check for media file listings
    media_lines = sum(1 for line in lines if _MEDIA_EXT_RE.search(line))
    if media_lines > content_lines * 0.3:
        raise ValueError(
            f"Rejected '{title}': {media_lines} media file references — not a text edition"
        )


def download_book(book: Book, output_dir: Path, *, clean: bool = True) -> tuple[Path, bool]:
    """Download a single book's plain text. Returns (file_path, was_cached)."""
    url = book.text_url
    if url is None:
        raise ValueError(f"No plain text available for: {book.title}")

    filename = make_filename(book)
    filepath = output_dir / filename

    if filepath.exists():
        return filepath, True

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    _validate_content(resp.text, book.title)

    filepath.write_text(resp.text, encoding="utf-8")
    if clean:
        clean_file(filepath)
    return filepath, False


def download_books(
    books: list[Book],
    output_dir: Path,
    limit: int | None = None,
    *,
    clean: bool = True,
) -> list[Path]:
    """Download multiple books. Creates output_dir if needed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = books[:limit] if limit else books
    paths: list[Path] = []

    for book in targets:
        try:
            path, cached = download_book(book, output_dir, clean=clean)
            paths.append(path)
            if cached:
                console.print(f"  [dim]- Cached: {path.resolve()}[/dim]")
            else:
                console.print(f"  [green]✓[/green] {book.title}")
        except (ValueError, requests.RequestException) as e:
            console.print(f"  [red]✗[/red] Skipping '{book.title}': {e}")

    return paths
