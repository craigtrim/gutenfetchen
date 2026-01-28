"""Download plain-text files from Project Gutenberg."""

from __future__ import annotations

from pathlib import Path

import requests

from gutenfetchen.cleaner import clean_file
from gutenfetchen.models import Book
from gutenfetchen.naming import make_filename


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
                print(f"  Cached: {path.resolve()}")
            else:
                print(f"  Downloaded: {book.title}")
        except (ValueError, requests.RequestException) as e:
            print(f"  Skipping '{book.title}': {e}")

    return paths
