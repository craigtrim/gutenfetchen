"""Tests for the download module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gutenfetch.downloader import download_book, download_books
from gutenfetch.models import Author, Book


@pytest.fixture
def text_book() -> Book:
    return Book(
        id=219,
        title="Heart of Darkness",
        authors=[Author(name="Conrad, Joseph")],
        formats={"text/plain; charset=utf-8": "https://example.com/219.txt"},
        download_count=50000,
    )


@patch("gutenfetch.downloader.requests.get")
def test_download_book(mock_get: MagicMock, text_book: Book, tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.text = "It was a dark and stormy night..."
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    path, cached = download_book(text_book, tmp_path)

    assert not cached
    assert path.exists()
    assert path.name == "joseph-conrad--heart-of-darkness.txt"
    assert path.read_text() == "It was a dark and stormy night..."


@patch("gutenfetch.downloader.requests.get")
def test_download_book_skips_existing(mock_get: MagicMock, text_book: Book, tmp_path: Path) -> None:
    existing = tmp_path / "joseph-conrad--heart-of-darkness.txt"
    existing.write_text("already here")

    path, cached = download_book(text_book, tmp_path)

    assert cached
    assert path == existing
    mock_get.assert_not_called()


def test_download_book_no_text_url(tmp_path: Path) -> None:
    book = Book(
        id=1,
        title="Audio Only",
        formats={"audio/mpeg": "https://example.com/audio.mp3"},
    )
    with pytest.raises(ValueError, match="No plain text"):
        download_book(book, tmp_path)


@patch("gutenfetch.downloader.requests.get")
def test_download_books_with_limit(mock_get: MagicMock, tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.text = "content"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    author = Author(name="Conrad, Joseph")
    books = [
        Book(
            id=i,
            title=f"Book {i}",
            authors=[author],
            formats={"text/plain; charset=utf-8": f"https://example.com/{i}.txt"},
        )
        for i in range(5)
    ]

    paths = download_books(books, tmp_path, limit=2)
    assert len(paths) == 2
