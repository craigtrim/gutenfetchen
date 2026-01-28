"""Gutendex API client for searching the Project Gutenberg catalog."""

from __future__ import annotations

import random
import time

import requests

from gutenfetchen.models import Author, Book, SearchResult

BASE_URL = "https://gutendex.com/books/"


def search_books(query: str, languages: str = "en") -> SearchResult:
    """Search for books by title or combined query."""
    params = {"search": query, "languages": languages}
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return _parse_response(resp.json())


def search_all_pages(query: str, languages: str = "en") -> list[Book]:
    """Fetch all pages for a query, following pagination."""
    result = search_books(query, languages)
    all_books = list(result.books)
    next_url = result.next_url

    while next_url:
        time.sleep(0.5)
        resp = requests.get(next_url, timeout=30)
        resp.raise_for_status()
        page = _parse_response(resp.json())
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
            if book.text_url and book.id not in collected:
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
    )
