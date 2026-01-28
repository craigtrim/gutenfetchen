"""Tests for the cleaner module."""

from __future__ import annotations

from pathlib import Path

from gutenfetchen.cleaner import _strip_produced_by, _strip_toc, clean_file, clean_text


def test_clean_text_strips_start_and_end() -> None:
    text = (
        "The Project Gutenberg EBook\n"
        "*** START of this Project Gutenberg EBook ***\n"
        "Call me Ishmael.\n"
        "Some years ago...\n"
        "*** END of this Project Gutenberg EBook ***\n"
        "More boilerplate here.\n"
    )
    result = clean_text(text)
    assert result == "Call me Ishmael.\nSome years ago...\n"


def test_clean_text_no_markers() -> None:
    text = "Just plain text.\nNo markers here.\n"
    result = clean_text(text)
    assert result == text


def test_clean_text_start_only() -> None:
    text = "Header stuff\n" "*** START of something ***\n" "Actual content.\n"
    result = clean_text(text)
    assert result == "Actual content.\n"


def test_clean_text_end_only() -> None:
    text = "Actual content.\n" "*** END of something ***\n" "Footer stuff\n"
    result = clean_text(text)
    assert result == "Actual content.\n"


def test_clean_text_strips_produced_by() -> None:
    text = (
        "*** START of this Project Gutenberg EBook ***\n"
        "Produced by Juliet Sutherland, Josephine Paolucci and the\n"
        "Online Distributed Proofreading Team at https://www.pgdp.net\n"
        "\n"
        "Then Marched the Brave...\n"
        "*** END of this Project Gutenberg EBook ***\n"
    )
    result = clean_text(text)
    assert result == "\nThen Marched the Brave...\n"


def test_strip_produced_by_multiline() -> None:
    lines = [
        "Produced by Someone\n",
        "and Another Person\n",
        "\n",
        "Chapter 1\n",
    ]
    result = _strip_produced_by(lines)
    assert result == ["\n", "Chapter 1\n"]


def test_strip_produced_by_not_present() -> None:
    lines = ["Chapter 1\n", "It was a dark night.\n"]
    result = _strip_produced_by(lines)
    assert result == lines


def test_strip_produced_by_beyond_100_lines() -> None:
    lines = [f"Line {i}\n" for i in range(100)]
    lines.append("Produced by Someone\n")
    lines.append("\n")
    lines.append("Content\n")
    result = _strip_produced_by(lines)
    assert result == lines  # unchanged, Produced by is past line 100


def test_strip_etext_prepared_by() -> None:
    lines = [
        "E-text prepared by John Smith and\n",
        "the Project Gutenberg team\n",
        "\n",
        "THE EDUCATION OF CATHOLIC GIRLS\n",
    ]
    result = _strip_produced_by(lines)
    assert result == ["\n", "THE EDUCATION OF CATHOLIC GIRLS\n"]


def test_strip_produced_by_case_insensitive() -> None:
    lines = [
        "PRODUCED BY Jane Doe\n",
        "\n",
        "Chapter 1\n",
    ]
    result = _strip_produced_by(lines)
    assert result == ["\n", "Chapter 1\n"]


def test_strip_toc_contents_to_chapter_i() -> None:
    lines = [
        "Preface\n",
        "\n",
        "CONTENTS\n",
        "I. The Beginning\n",
        "II. The Middle\n",
        "III. The End\n",
        "CHAPTER I.\n",
        "It was the best of times.\n",
    ]
    result = _strip_toc(lines)
    assert result == ["Preface\n", "\n", "It was the best of times.\n"]


def test_strip_toc_table_of_contents_to_chapter_1() -> None:
    lines = [
        "TABLE OF CONTENTS\n",
        "1. Intro\n",
        "2. Body\n",
        "Chapter 1\n",
        "Once upon a time.\n",
    ]
    result = _strip_toc(lines)
    assert result == ["Once upon a time.\n"]


def test_strip_toc_case_insensitive() -> None:
    lines = [
        "contents\n",
        "Some entry\n",
        "chapter i\n",
        "The story begins.\n",
    ]
    result = _strip_toc(lines)
    assert result == ["The story begins.\n"]


def test_strip_toc_marker_with_period() -> None:
    lines = [
        "CONTENTS\n",
        "First entry\n",
        "CHAPTER I.\n",
        "Body text.\n",
    ]
    result = _strip_toc(lines)
    assert result == ["Body text.\n"]


def test_strip_toc_dash_markers() -> None:
    lines = [
        "Contents\n",
        "Entry one\n",
        "-1-\n",
        "The first chapter.\n",
    ]
    result = _strip_toc(lines)
    assert result == ["The first chapter.\n"]


def test_strip_toc_no_header() -> None:
    lines = ["CHAPTER I\n", "Body text.\n"]
    result = _strip_toc(lines)
    assert result == lines


def test_strip_toc_no_chapter_marker() -> None:
    lines = [
        "CONTENTS\n",
        "Some entry\n",
        "Another entry\n",
        "Body text with no chapter marker.\n",
    ]
    result = _strip_toc(lines)
    assert result == lines


def test_strip_toc_beyond_1000_lines() -> None:
    lines = [f"Line {i}\n" for i in range(1000)]
    lines.append("CONTENTS\n")
    lines.append("Entry\n")
    lines.append("CHAPTER I\n")
    lines.append("Body\n")
    result = _strip_toc(lines)
    assert result == lines  # unchanged, CONTENTS is past line 1000


def test_clean_file(tmp_path: Path) -> None:
    filepath = tmp_path / "book.txt"
    filepath.write_text(
        "Header\n" "*** START ***\n" "Body text.\n" "*** END ***\n" "Footer\n",
        encoding="utf-8",
    )
    clean_file(filepath)
    assert filepath.read_text(encoding="utf-8") == "Body text.\n"
