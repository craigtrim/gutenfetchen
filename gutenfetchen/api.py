"""Gutendex API client for searching the Project Gutenberg catalog."""

from __future__ import annotations

import json
import random
import re
import shutil
import time
from pathlib import Path

import requests
from rich.console import Console

from gutenfetchen.models import Author, Book, SearchResult

_console = Console()

BASE_URL = "https://gutendex.com/books/"

CACHE_DIR = Path(".gutenfetch_cache")


def _cache_key(query: str, languages: str) -> str:
    """Create a filesystem-safe cache directory name from a query."""
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    return f"{slug}_{languages}"


def _cache_path(query: str, languages: str, page: int) -> Path:
    """Return the path for a cached page JSON file."""
    return CACHE_DIR / _cache_key(query, languages) / f"page_{page}.json"


def clear_cache(query: str | None = None, languages: str = "en") -> None:
    """Remove cached catalog pages.

    If *query* is given, only that query's cache is removed.
    If *query* is None, the entire cache directory is removed.
    """
    if query is None:
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
    else:
        target = CACHE_DIR / _cache_key(query, languages)
        if target.exists():
            shutil.rmtree(target)


def _read_cache(query: str, languages: str, page: int) -> dict | None:  # type: ignore[type-arg]
    """Return cached JSON data for a page, or None on miss."""
    path = _cache_path(query, languages, page)
    if path.exists():
        return dict(json.loads(path.read_text(encoding="utf-8")))
    return None


def _write_cache(query: str, languages: str, page: int, data: dict) -> None:  # type: ignore[type-arg]
    """Write a page's JSON response to the cache."""
    path = _cache_path(query, languages, page)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def search_books(query: str, languages: str = "en") -> SearchResult:
    """Search for books by title or combined query."""
    params = {"search": query, "languages": languages}
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return _parse_response(resp.json())


def search_all_pages(query: str, languages: str = "en", *, refresh: bool = False) -> list[Book]:
    """Fetch all pages for a query, following pagination.

    Results are cached to ``.gutenfetch_cache/`` so repeat queries skip
    the network.  Pass *refresh=True* to ignore the cache and re-fetch.
    """
    if refresh:
        clear_cache(query, languages)

    # --- Try loading from cache first ---
    cached_books: list[Book] = []
    page_num = 1
    while True:
        data = _read_cache(query, languages, page_num)
        if data is None:
            break
        page = _parse_response(data)
        cached_books.extend(page.books)
        if not page.next_url:
            # Cache is complete — all pages present
            _console.print(
                f"[dim]Loaded {len(cached_books)} cached results for "
                f"'{query}' ({page_num} pages)[/dim]"
            )
            return cached_books
        page_num += 1

    # --- Cache miss or partial: fetch from network ---
    # Start fresh from page 1 to ensure consistency
    params = {"search": query, "languages": languages}
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    _write_cache(query, languages, 1, data)
    result = _parse_response(data)
    all_books = list(result.books)
    next_url = result.next_url
    page_num = 1

    with _console.status("[yellow]Fetching catalog pages...[/yellow]") as status:
        while next_url:
            page_num += 1
            status.update(
                f"[yellow]Fetching catalog page {page_num} "
                f"({len(all_books)} books so far)...[/yellow]"
            )
            time.sleep(0.5)
            resp = requests.get(next_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            _write_cache(query, languages, page_num, data)
            page = _parse_response(data)
            all_books.extend(page.books)
            next_url = page.next_url

    return all_books


def fetch_random(n: int, languages: str = "en") -> list[Book]:
    """Fetch n random English books with plain text available."""
    # Gutendex supports sorting by random via the `sort` param is not available,
    # but we can grab a few pages from random offsets and sample from them.
    # First, get total count of English books with text.
    params = {"languages": languages, "mime_type": "text/plain"}
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    total = data.get("count", 0)
    if total == 0:
        return []

    # Gutendex has 32 results per page
    max_page = max(1, total // 32)
    collected: dict[int, Book] = {}

    # Sample from random pages until we have enough
    attempts = 0
    while len(collected) < n and attempts < n + 10:
        page = random.randint(1, max_page)
        params_page = {"languages": languages, "mime_type": "text/plain", "page": str(page)}
        time.sleep(0.5)
        resp = requests.get(BASE_URL, params=params_page, timeout=30)
        if resp.status_code != 200:
            attempts += 1
            continue
        result = _parse_response(resp.json())
        for book in result.books:
            if book.text_url and book.media_type == "Text" and book.id not in collected:
                collected[book.id] = book
                if len(collected) >= n:
                    break
        attempts += 1

    return list(collected.values())[:n]


def _parse_response(data: dict) -> SearchResult:  # type: ignore[type-arg]
    """Parse a Gutendex JSON response into a SearchResult."""
    books = [_parse_book(item) for item in data.get("results", [])]
    return SearchResult(
        count=data.get("count", 0),
        books=books,
        next_url=data.get("next"),
    )


def _parse_book(item: dict) -> Book:  # type: ignore[type-arg]
    """Parse a single book dict from the Gutendex API."""
    authors = [
        Author(
            name=a.get("name", "Unknown"),
            birth_year=a.get("birth_year"),
            death_year=a.get("death_year"),
        )
        for a in item.get("authors", [])
    ]
    return Book(
        id=item["id"],
        title=item.get("title", ""),
        authors=authors,
        formats=item.get("formats", {}),
        download_count=item.get("download_count", 0),
        languages=item.get("languages", []),
        subjects=item.get("subjects", []),
        media_type=item.get("media_type", "Text"),
    )
