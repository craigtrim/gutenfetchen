"""Shared test fixtures."""

from __future__ import annotations

import pytest

from gutenfetchen.models import Author, Book


@pytest.fixture
def sample_author() -> Author:
    return Author(name="Conrad, Joseph", birth_year=1857, death_year=1924)


@pytest.fixture
def sample_book(sample_author: Author) -> Book:
    return Book(
        id=219,
        title="Heart of Darkness",
        authors=[sample_author],
        formats={
            "text/plain; charset=utf-8": "https://www.gutenberg.org/files/219/219-0.txt",
            "text/html": "https://www.gutenberg.org/files/219/219-h/219-h.htm",
        },
        download_count=50000,
        languages=["en"],
        subjects=["Africa -- Fiction"],
    )


@pytest.fixture
def sample_api_response() -> dict:  # type: ignore[type-arg]
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 219,
                "title": "Heart of Darkness",
                "authors": [{"name": "Conrad, Joseph", "birth_year": 1857, "death_year": 1924}],
                "formats": {
                    "text/plain; charset=utf-8": "https://www.gutenberg.org/files/219/219-0.txt",
                },
                "download_count": 50000,
                "languages": ["en"],
                "subjects": ["Africa -- Fiction"],
            },
            {
                "id": 526,
                "title": "The Secret Agent: A Simple Tale",
                "authors": [{"name": "Conrad, Joseph", "birth_year": 1857, "death_year": 1924}],
                "formats": {
                    "text/plain; charset=utf-8": "https://www.gutenberg.org/files/526/526-0.txt",
                },
                "download_count": 20000,
                "languages": ["en"],
                "subjects": ["Anarchists -- Fiction"],
            },
        ],
    }


@pytest.fixture
def duplicate_books() -> list[Book]:
    author = Author(name="Conrad, Joseph")
    return [
        Book(
            id=219,
            title="Heart of Darkness",
            authors=[author],
            formats={"text/plain; charset=utf-8": "https://example.com/219.txt"},
            download_count=50000,
        ),
        Book(
            id=9999,
            title="Heart of Darkness: A Novella",
            authors=[author],
            formats={"text/plain; charset=utf-8": "https://example.com/9999.txt"},
            download_count=1000,
        ),
        Book(
            id=526,
            title="The Secret Agent: A Simple Tale",
            authors=[author],
            formats={"text/plain; charset=utf-8": "https://example.com/526.txt"},
            download_count=20000,
        ),
    ]
