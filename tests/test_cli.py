"""Tests for the CLI module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gutenfetchen.cli import build_parser, main
from gutenfetchen.models import Author, Book, SearchResult


def test_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["some title"])
    assert args.title == "some title"
    assert args.author is None
    assert args.limit is None
    assert args.random is None
    assert not args.dry_run


def test_parser_random() -> None:
    parser = build_parser()
    args = parser.parse_args(["--random", "10"])
    assert args.random == 10


def test_parser_author_and_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["--author", "joseph conrad", "--n", "5"])
    assert args.author == "joseph conrad"
    assert args.limit == 5


@patch("gutenfetchen.cli.download_books")
@patch("gutenfetchen.cli.search_books")
def test_main_title_search(mock_search: MagicMock, mock_download: MagicMock) -> None:
    book = Book(
        id=219,
        title="Heart of Darkness",
        authors=[Author(name="Conrad, Joseph")],
        formats={"text/plain; charset=utf-8": "https://example.com/219.txt"},
        download_count=50000,
    )
    mock_search.return_value = SearchResult(count=1, books=[book])
    mock_download.return_value = ["/tmp/test.txt"]

    result = main(["heart of darkness"])

    assert result == 0
    mock_search.assert_called_once_with("heart of darkness")
    mock_download.assert_called_once()


@patch("gutenfetchen.cli.search_books")
def test_main_no_results(mock_search: MagicMock) -> None:
    mock_search.return_value = SearchResult(count=0, books=[])
    result = main(["nonexistent book title"])
    assert result == 1


@patch("gutenfetchen.cli.search_all_pages")
def test_main_dry_run(mock_search: MagicMock) -> None:
    book = Book(
        id=219,
        title="Heart of Darkness",
        authors=[Author(name="Conrad, Joseph")],
        formats={"text/plain; charset=utf-8": "https://example.com/219.txt"},
        download_count=50000,
    )
    mock_search.return_value = [book]

    result = main(["--author", "joseph conrad", "--dry-run"])

    assert result == 0


@patch("gutenfetchen.cli.download_books")
@patch("gutenfetchen.cli.fetch_random")
def test_main_random(mock_fetch: MagicMock, mock_download: MagicMock) -> None:
    books = [
        Book(
            id=i,
            title=f"Random Book {i}",
            authors=[Author(name="Author, Random")],
            formats={"text/plain; charset=utf-8": f"https://example.com/{i}.txt"},
        )
        for i in range(3)
    ]
    mock_fetch.return_value = books
    mock_download.return_value = [f"/tmp/{i}.txt" for i in range(3)]

    result = main(["--random", "3"])

    assert result == 0
    mock_fetch.assert_called_once()
    args, kwargs = mock_fetch.call_args
    assert args == (3,)
    assert "on_progress" in kwargs


@patch("gutenfetchen.cli.fetch_random")
def test_main_random_dry_run(mock_fetch: MagicMock) -> None:
    books = [
        Book(
            id=42,
            title="Surprise Novel",
            authors=[Author(name="Mystery, Author")],
            formats={"text/plain; charset=utf-8": "https://example.com/42.txt"},
        )
    ]
    mock_fetch.return_value = books

    result = main(["--random", "1", "--dry-run"])

    assert result == 0


# --- clean subcommand tests ---

_GUTENBERG_TEXT = (
    "The Project Gutenberg EBook of Test\n"
    "\n"
    "*** START OF THE PROJECT GUTENBERG EBOOK ***\n"
    "\n"
    "Body text line one.\n"
    "Body text line two.\n"
    "\n"
    "*** END OF THE PROJECT GUTENBERG EBOOK ***\n"
    "\n"
    "End of Project Gutenberg\n"
)


def test_clean_single_file(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text(_GUTENBERG_TEXT, encoding="utf-8")

    result = main(["clean", str(f)])

    assert result == 0
    cleaned = f.read_text(encoding="utf-8")
    assert "Project Gutenberg" not in cleaned
    assert "Body text line one." in cleaned


def test_clean_directory(tmp_path: Path) -> None:
    for name in ["a.txt", "b.txt"]:
        (tmp_path / name).write_text(_GUTENBERG_TEXT, encoding="utf-8")
    (tmp_path / "readme.md").write_text("# Not a text file\n")

    result = main(["clean", str(tmp_path)])

    assert result == 0
    for name in ["a.txt", "b.txt"]:
        cleaned = (tmp_path / name).read_text(encoding="utf-8")
        assert "Project Gutenberg" not in cleaned
        assert "Body text" in cleaned
    assert (tmp_path / "readme.md").read_text() == "# Not a text file\n"


def test_clean_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text(_GUTENBERG_TEXT, encoding="utf-8")

    result = main(["clean", "--dry-run", str(f)])

    assert result == 0
    assert f.read_text(encoding="utf-8") == _GUTENBERG_TEXT


def test_clean_nonexistent_path() -> None:
    result = main(["clean", "/nonexistent/path.txt"])
    assert result == 1


def test_clean_empty_directory(tmp_path: Path) -> None:
    result = main(["clean", str(tmp_path)])
    assert result == 1


def test_clean_idempotent(tmp_path: Path) -> None:
    """Cleaning an already-clean text should not alter it."""
    f = tmp_path / "test.txt"
    f.write_text(_GUTENBERG_TEXT, encoding="utf-8")

    # First pass: raw → clean
    main(["clean", str(f)])
    after_first = f.read_text(encoding="utf-8")

    # Second pass: clean → should be identical
    main(["clean", str(f)])
    after_second = f.read_text(encoding="utf-8")

    assert after_first == after_second
