"""Tests for data models."""

from gutenfetchen.models import Author, Book, SearchResult


def test_author_display_name_last_first() -> None:
    author = Author(name="Conrad, Joseph")
    assert author.display_name == "Joseph Conrad"


def test_author_display_name_no_comma() -> None:
    author = Author(name="Anonymous")
    assert author.display_name == "Anonymous"


def test_book_text_url_prefers_utf8() -> None:
    book = Book(
        id=1,
        title="Test",
        formats={
            "text/plain; charset=us-ascii": "https://example.com/ascii.txt",
            "text/plain; charset=utf-8": "https://example.com/utf8.txt",
        },
    )
    assert book.text_url == "https://example.com/utf8.txt"


def test_book_text_url_falls_back_to_ascii() -> None:
    book = Book(
        id=1,
        title="Test",
        formats={"text/plain; charset=us-ascii": "https://example.com/ascii.txt"},
    )
    assert book.text_url == "https://example.com/ascii.txt"


def test_book_text_url_none_when_no_text() -> None:
    book = Book(
        id=1,
        title="Test",
        formats={"text/html": "https://example.com/test.html"},
    )
    assert book.text_url is None


def test_search_result_defaults() -> None:
    result = SearchResult(count=0)
    assert result.books == []
    assert result.next_url is None
