"""Tests for deduplication and author filtering."""

from gutenfetchen.dedup import (
    _normalize_title,
    deduplicate,
    filter_by_author,
    filter_has_text,
    filter_text_only,
    filter_volumes,
)
from gutenfetchen.models import Author, Book


def test_normalize_title_strips_subtitle() -> None:
    assert _normalize_title("The Secret Agent: A Simple Tale") == "secret agent"


def test_normalize_title_strips_articles() -> None:
    assert _normalize_title("The Old Man and the Sea") == "old man and the sea"


def test_normalize_title_strips_punctuation() -> None:
    assert _normalize_title("Hello, World!") == "hello world"


def test_deduplicate_keeps_highest_downloads(duplicate_books: list[Book]) -> None:
    result = deduplicate(duplicate_books)
    titles = [b.title for b in result]
    # Should keep "Heart of Darkness" (50000) not "Heart of Darkness: A Novella" (1000)
    assert len(result) == 2
    assert "Heart of Darkness" in titles
    assert "Heart of Darkness: A Novella" not in titles


def test_deduplicate_sorts_by_downloads(duplicate_books: list[Book]) -> None:
    result = deduplicate(duplicate_books)
    assert result[0].download_count >= result[1].download_count


def test_deduplicate_empty() -> None:
    assert deduplicate([]) == []


def test_filter_by_author() -> None:
    conrad = Author(name="Conrad, Joseph")
    other = Author(name="Smith, John")
    books = [
        Book(id=1, title="Heart of Darkness", authors=[conrad]),
        Book(id=2, title="Joseph Conrad: A Biography", authors=[other]),
    ]
    result = filter_by_author(books, "joseph conrad")
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_text_only() -> None:
    books = [
        Book(
            id=675,
            title="American Notes",
            formats={"text/plain; charset=utf-8": "https://example.com/675.txt"},
            media_type="Text",
        ),
        Book(
            id=9693,
            title="American Notes",
            formats={"text/plain; charset=us-ascii": "https://example.com/9693.txt"},
            media_type="Sound",
        ),
    ]
    result = filter_text_only(books)
    assert len(result) == 1
    assert result[0].id == 675


def test_filter_has_text() -> None:
    books = [
        Book(
            id=1,
            title="With Text",
            formats={"text/plain; charset=utf-8": "https://example.com/1.txt"},
        ),
        Book(
            id=2,
            title="Audio Only",
            formats={"audio/mpeg": "https://example.com/2.mp3"},
        ),
    ]
    result = filter_has_text(books)
    assert len(result) == 1
    assert result[0].id == 1


# ---------------------------------------------------------------------------
# filter_volumes
# ---------------------------------------------------------------------------


def test_filter_volumes_removes_when_whole_exists() -> None:
    """Volume splits are dropped when the whole book is present."""
    books = [
        Book(id=1, title="Oliver Twist"),
        Book(id=2, title="Oliver Twist, Vol. 1 (of 3)"),
        Book(id=3, title="Oliver Twist, Vol. 2 (of 3)"),
        Book(id=4, title="Oliver Twist, Vol. 3 (of 3)"),
    ]
    result = filter_volumes(books)
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_volumes_keeps_when_no_whole() -> None:
    """Volume splits are kept when no whole-book edition exists."""
    books = [
        Book(id=2, title="The Pickwick Papers, v. 1 (of 2)"),
        Book(id=3, title="The Pickwick Papers, v. 2 (of 2)"),
    ]
    result = filter_volumes(books)
    assert len(result) == 2


def test_filter_volumes_mixed() -> None:
    """Whole books coexist with volume-only titles."""
    books = [
        Book(id=1, title="Oliver Twist"),
        Book(id=2, title="Oliver Twist, Vol. 1 (of 3)"),
        Book(id=3, title="Oliver Twist, Vol. 2 (of 3)"),
        Book(id=4, title="Great Expectations"),
        Book(id=5, title="Bleak House, Volume 1"),
        Book(id=6, title="Bleak House, Volume 2"),
    ]
    result = filter_volumes(books)
    titles = [b.title for b in result]
    assert "Oliver Twist" in titles
    assert "Oliver Twist, Vol. 1 (of 3)" not in titles
    assert "Great Expectations" in titles
    # Bleak House has no whole edition, so volumes are kept
    assert "Bleak House, Volume 1" in titles
    assert "Bleak House, Volume 2" in titles


def test_filter_volumes_part_pattern() -> None:
    """'Part N' pattern is also detected."""
    books = [
        Book(id=1, title="Don Quixote"),
        Book(id=2, title="Don Quixote, Part 1"),
        Book(id=3, title="Don Quixote, Part 2"),
    ]
    result = filter_volumes(books)
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_volumes_empty() -> None:
    assert filter_volumes([]) == []
