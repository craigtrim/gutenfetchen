"""Tests for filename generation."""

from gutenfetchen.models import Book
from gutenfetchen.naming import make_filename, slugify


def test_slugify_basic() -> None:
    assert slugify("Heart of Darkness") == "heart-of-darkness"


def test_slugify_special_chars() -> None:
    assert slugify("Hello, World! (2024)") == "hello-world-2024"


def test_slugify_collapses_whitespace() -> None:
    assert slugify("  multiple   spaces  ") == "multiple-spaces"


def test_slugify_caps_length() -> None:
    long_text = "a" * 100
    assert len(slugify(long_text)) == 80


def test_make_filename(sample_book: Book) -> None:  # type: ignore[type-arg]
    result = make_filename(sample_book)
    assert result == "joseph-conrad--heart-of-darkness.txt"


def test_make_filename_no_author() -> None:
    book = Book(id=1, title="Anonymous Work", authors=[])
    result = make_filename(book)
    assert result == "unknown--anonymous-work.txt"
