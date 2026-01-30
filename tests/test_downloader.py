"""Tests for the download module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gutenfetchen.downloader import _validate_content, download_book, download_books
from gutenfetchen.models import Author, Book

# Valid Gutenberg-style content for mocking downloads.
_VALID_BOOK = (
    "Header\n"
    "*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    + "This is a line of prose.\n" * 100
    + "*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    "Footer\n"
)


@pytest.fixture
def text_book() -> Book:
    return Book(
        id=219,
        title="Heart of Darkness",
        authors=[Author(name="Conrad, Joseph")],
        formats={"text/plain; charset=utf-8": "https://example.com/219.txt"},
        download_count=50000,
    )


@patch("gutenfetchen.downloader.requests.get")
def test_download_book(mock_get: MagicMock, text_book: Book, tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.text = _VALID_BOOK
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    path, cached = download_book(text_book, tmp_path)

    assert not cached
    assert path.exists()
    assert path.name == "joseph-conrad--heart-of-darkness.txt"


@patch("gutenfetchen.downloader.requests.get")
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


@patch("gutenfetchen.downloader.requests.get")
def test_download_books_with_limit(mock_get: MagicMock, tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.text = _VALID_BOOK
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


# --- _validate_content tests (Issue #3) ---


def test_validate_content_accepts_valid_book() -> None:
    _validate_content(_VALID_BOOK, "Test Book")


def test_validate_content_rejects_no_start_marker() -> None:
    text = "Just some text\n" * 200
    with pytest.raises(ValueError, match="no \\*\\*\\* START marker"):
        _validate_content(text, "Bad Book")


def test_validate_content_rejects_too_few_lines() -> None:
    text = (
        "*** START ***\n"
        "One line.\n"
        "*** END ***\n"
    )
    with pytest.raises(ValueError, match="only 1 content lines"):
        _validate_content(text, "Tiny Book")


def test_validate_content_rejects_media_listing() -> None:
    lines = ["*** START ***\n"]
    lines += [f"  track-{i:03d}.mp3\n" for i in range(100)]
    lines += ["*** END ***\n"]
    text = "".join(lines)
    with pytest.raises(ValueError, match="media file references"):
        _validate_content(text, "Audio Index")
