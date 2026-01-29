"""Tests for the cleaner module."""

from __future__ import annotations

from pathlib import Path

from gutenfetchen.cleaner import (
    _normalize_allcaps_headings,
    _strip_inline_footnotes,
    _strip_produced_by,
    _strip_toc,
    _strip_underscore_italics,
    clean_file,
    clean_text,
)


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


# ---------------------------------------------------------------------------
# _strip_underscore_italics
# ---------------------------------------------------------------------------


def test_strip_underscore_italics_basic() -> None:
    """Paired underscores around a word are removed."""
    lines = ["He read _Hamlet_ last night.\n"]
    result = _strip_underscore_italics(lines)
    assert result == ["He read Hamlet last night.\n"]


def test_strip_underscore_italics_phrase() -> None:
    """Paired underscores around a multi-word phrase are removed."""
    lines = ["She mentioned _Les Huguenots_ in passing.\n"]
    result = _strip_underscore_italics(lines)
    assert result == ["She mentioned Les Huguenots in passing.\n"]


def test_strip_underscore_italics_multiple_on_one_line() -> None:
    """Multiple italic pairs on the same line are each stripped."""
    lines = ["Read _Hamlet_ and _Othello_ today.\n"]
    result = _strip_underscore_italics(lines)
    assert result == ["Read Hamlet and Othello today.\n"]


def test_strip_underscore_italics_at_sentence_end() -> None:
    """Underscore adjacent to punctuation (e.g. _word_.) is cleaned."""
    lines = ["He performed _Les Huguenots_.\n"]
    result = _strip_underscore_italics(lines)
    assert result == ["He performed Les Huguenots.\n"]


def test_strip_underscore_italics_no_match() -> None:
    """Plain text without underscores is returned unchanged."""
    lines = ["No italics here.\n"]
    result = _strip_underscore_italics(lines)
    assert result == ["No italics here.\n"]


# ---------------------------------------------------------------------------
# _normalize_allcaps_headings
# ---------------------------------------------------------------------------


def test_normalize_allcaps_heading_basic() -> None:
    """A standalone ALL CAPS line is converted to title case."""
    lines = ["CHAPTER XII.\n"]
    result = _normalize_allcaps_headings(lines)
    # Title case applied; blank-line isolation added after if next line exists
    assert "Chapter Xii.\n" in result


def test_normalize_allcaps_heading_isolation() -> None:
    """Blank lines are inserted around an ALL CAPS heading when absent."""
    lines = [
        "Some body text.\n",
        "THE COUNCIL OF ELROND\n",
        "More body text.\n",
    ]
    result = _normalize_allcaps_headings(lines)
    # Should have blank lines inserted before and after the heading
    assert result == [
        "Some body text.\n",
        "\n",
        "The Council Of Elrond\n",
        "\n",
        "More body text.\n",
    ]


def test_normalize_allcaps_heading_already_isolated() -> None:
    """No extra blank lines are added if heading is already isolated."""
    lines = [
        "\n",
        "THE END OF THE AFFAIR\n",
        "\n",
    ]
    result = _normalize_allcaps_headings(lines)
    # Blank lines before/after already present — no duplicates
    assert result == [
        "\n",
        "The End Of The Affair\n",
        "\n",
    ]


def test_normalize_allcaps_single_letter_not_heading() -> None:
    """A single uppercase letter (e.g. Roman numeral 'I') is not treated as a heading."""
    lines = ["I\n", "went to the store.\n"]
    result = _normalize_allcaps_headings(lines)
    # Single letter does not qualify (needs >= 2 letters)
    assert result[0] == "I\n"


def test_normalize_allcaps_mixed_case_unchanged() -> None:
    """Lines that are not entirely uppercase pass through unchanged."""
    lines = ["Chapter XII. The Council\n"]
    result = _normalize_allcaps_headings(lines)
    assert result == ["Chapter XII. The Council\n"]


# ---------------------------------------------------------------------------
# _strip_inline_footnotes
# ---------------------------------------------------------------------------


def test_strip_inline_footnotes_full_body() -> None:
    """[Footnote N: text] is removed from the line."""
    lines = ["He sailed west[Footnote 1: Columbus, 1492] across the sea.\n"]
    result = _strip_inline_footnotes(lines)
    assert result == ["He sailed west across the sea.\n"]


def test_strip_inline_footnotes_bare_reference() -> None:
    """Bare [N] reference markers are removed."""
    lines = ["The council met[1] on Thursday.\n"]
    result = _strip_inline_footnotes(lines)
    assert result == ["The council met on Thursday.\n"]


def test_strip_inline_footnotes_multiple() -> None:
    """Multiple footnote markers on one line are all removed."""
    lines = ["First[1] and second[2] references.\n"]
    result = _strip_inline_footnotes(lines)
    assert result == ["First and second references.\n"]


def test_strip_inline_footnotes_case_insensitive() -> None:
    """[footnote ...] in different cases is still matched."""
    lines = ["Text[footnote 3: some note] here.\n"]
    result = _strip_inline_footnotes(lines)
    assert result == ["Text here.\n"]


def test_strip_inline_footnotes_no_match() -> None:
    """Lines without footnote markers are returned unchanged."""
    lines = ["Just regular text.\n"]
    result = _strip_inline_footnotes(lines)
    assert result == ["Just regular text.\n"]


# ---------------------------------------------------------------------------
# Integration: clean_text includes new strip functions
# ---------------------------------------------------------------------------


def test_clean_text_strips_italics_and_footnotes() -> None:
    """End-to-end: clean_text removes underscore italics and inline footnotes."""
    text = (
        "*** START ***\n"
        "He read _Hamlet_[1] in the evening.\n"
        "*** END ***\n"
    )
    result = clean_text(text)
    assert result == "He read Hamlet in the evening.\n"


def test_clean_text_normalizes_allcaps() -> None:
    """End-to-end: clean_text converts ALL CAPS headings to title case."""
    text = (
        "*** START ***\n"
        "Some prose.\n"
        "THE COUNCIL OF ELROND\n"
        "More prose.\n"
        "*** END ***\n"
    )
    result = clean_text(text)
    assert "The Council Of Elrond\n" in result


def test_clean_file(tmp_path: Path) -> None:
    filepath = tmp_path / "book.txt"
    filepath.write_text(
        "Header\n" "*** START ***\n" "Body text.\n" "*** END ***\n" "Footer\n",
        encoding="utf-8",
    )
    clean_file(filepath)
    assert filepath.read_text(encoding="utf-8") == "Body text.\n"
