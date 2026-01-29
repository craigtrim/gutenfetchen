"""Strip Project Gutenberg boilerplate from downloaded texts."""

from __future__ import annotations

import re
from pathlib import Path


def clean_text(text: str) -> str:
    """Remove everything up to and including '*** START' line,
    and everything from '*** END' line onward."""
    lines = text.splitlines(keepends=True)

    start_idx: int | None = None
    end_idx: int | None = None

    for i, line in enumerate(lines):
        if start_idx is None and "*** START" in line:
            start_idx = i
        if "*** END" in line:
            end_idx = i
            break

    if start_idx is not None:
        lines = lines[start_idx + 1 :]
        if end_idx is not None:
            end_idx = end_idx - start_idx - 1
    if end_idx is not None:
        lines = lines[:end_idx]

    lines = _strip_transcriber_note(lines)
    lines = _strip_before_chapter(lines)
    lines = _strip_produced_by(lines)
    lines = _strip_toc(lines)
    lines = _strip_the_end(lines)
    lines = _strip_trailing_divider(lines)
    lines = _strip_trailing_transcriber_note(lines)
    lines = _strip_illustrations(lines)
    lines = _strip_trailing_index(lines)
    lines = _strip_trailing_footnotes(lines)

    # --- Issue #1: additional inline cleanup ---
    # Strip _italic_ underscore markup (e.g. _Les Huguenots_ → Les Huguenots)
    lines = _strip_underscore_italics(lines)
    # Remove inline [Footnote N: ...] bodies and [N] back-references
    lines = _strip_inline_footnotes(lines)
    # Normalize ALL CAPS headings to title case with blank-line isolation
    lines = _normalize_allcaps_headings(lines)

    return "".join(lines)


_BOILERPLATE_PREFIXES = (
    "produced by",
    "e-text prepared by",
)


_TRANSCRIBER_PREFIXES: list[str] = [
    "transcriber's note",
    "transcriber's notes",
    "transcribers note",
    "transcribers notes",
    "transcribers' note",
    "transcribers' notes",
    "transcriber\u2019s note",
    "transcriber\u2019s notes",
    "transcribers\u2019 note",
    "transcribers\u2019 notes",
    "transcriber note",
    "transcriber notes",
]

_ASTERISK_DIVIDER_RE = re.compile(r"^[\s*]+$")

# Matches paired underscore italic markup around words/phrases.
# Examples: _Les Huguenots_, _word_, _a long phrase_
# Requires at least one non-underscore character between the pair.
# Uses word boundaries (\b) to avoid matching snake_case identifiers.
_UNDERSCORE_ITALIC_RE = re.compile(r"\b_((?:(?!_).)+?)_\b")

# Matches inline footnote references like [1], [23], [Footnote 1: ...].
# Two patterns combined with alternation:
#   1) [Footnote N: any text]  — the full inline footnote body
#   2) [N]                      — bare numeric back-references
_INLINE_FOOTNOTE_RE = re.compile(
    r"\[Footnote\s+\d+:\s*[^\]]*\]"  # [Footnote 1: explanatory text]
    r"|\[\d+\]",                       # [1], [23], etc.
    re.IGNORECASE,
)


def _is_transcriber_line(line: str) -> bool:
    """Return True if *line* starts with any known transcriber-note prefix."""
    lower = line.strip().lower()
    return any(lower.startswith(p) for p in _TRANSCRIBER_PREFIXES)


def _strip_transcriber_note(lines: list[str]) -> list[str]:
    """Remove transcriber note blocks from the first 200 lines.

    Finds a line starting with a 'Transcriber's Note' variant, then scans
    downward for an asterisk divider line (e.g. ``*  *  *  *  *``).
    Deletes both lines and everything in between.
    """
    limit = min(200, len(lines))
    note_idx: int | None = None

    for i in range(limit):
        if _is_transcriber_line(lines[i]):
            note_idx = i
            break

    if note_idx is None:
        return lines

    for j in range(note_idx + 1, limit):
        stripped = lines[j].strip()
        if stripped and _ASTERISK_DIVIDER_RE.match(stripped):
            return lines[:note_idx] + lines[j + 1 :]

    return lines


def _strip_before_chapter(lines: list[str]) -> list[str]:
    """Delete everything up to and including a line that is exactly a chapter marker.

    Scans the entire file for a line whose stripped, lowercased, period-stripped
    content matches one of ``_CHAPTER_START_MARKERS``. If found, removes that
    line and all preceding lines.
    """
    for i, line in enumerate(lines):
        lower = line.strip().lower()
        if lower in _CHAPTER_START_MARKERS or lower.rstrip(".") in _CHAPTER_START_MARKERS:
            return lines[i + 1 :]
    return lines


def _strip_produced_by(lines: list[str]) -> list[str]:
    """Remove boilerplate credit blocks from the first 100 lines.

    Finds a line starting with a known prefix (case-insensitive),
    deletes it and every following line until hitting a blank line.
    The blank line is kept.
    """
    limit = min(100, len(lines))
    for i in range(limit):
        lower = lines[i].lower()
        if any(lower.startswith(p) for p in _BOILERPLATE_PREFIXES):
            end = i + 1
            while end < len(lines) and lines[end].strip():
                end += 1
            return lines[:i] + lines[end:]
    return lines


_TOC_HEADERS: list[str] = [
    "contents",
    "table of contents",
]

_CHAPTER_START_MARKERS: list[str] = [
    "chapter i",
    "chapter 1",
    "*chapter i*",
    "*chapter 1*",
    "chapter one",
    "- chapter one -",
    "1.",
    "i.",
    "-1-",
    "-i-",
]


def _strip_toc(lines: list[str]) -> list[str]:
    """Remove table of contents block from the first 1000 lines.

    Finds a line matching a known ToC header (case-insensitive), then scans
    downward for a line starting with a chapter marker. If both are found,
    deletes the header, the marker, and everything in between.
    """
    limit = min(1000, len(lines))
    toc_idx: int | None = None

    for i in range(limit):
        stripped = lines[i].strip().lower()
        if stripped in _TOC_HEADERS:
            toc_idx = i
            break

    if toc_idx is None:
        return lines

    for j in range(toc_idx + 1, len(lines)):
        stripped = lines[j].strip().lower().rstrip(".")
        if stripped in _CHAPTER_START_MARKERS:
            return lines[:toc_idx] + lines[j + 1 :]

    return lines


def _strip_the_end(lines: list[str]) -> list[str]:
    """Remove everything after a standalone 'THE END' line.

    Scans the last 1000 lines for a line that, after stripping whitespace
    and lowercasing, equals 'the end'. If found, truncates everything
    after that line (the marker itself is also removed).
    """
    total = len(lines)
    start = max(0, total - 1000)
    for i in range(total - 1, start - 1, -1):
        if lines[i].strip().lower() == "the end":
            return lines[:i]
    return lines


def _strip_trailing_divider(lines: list[str]) -> list[str]:
    """Remove a trailing asterisk divider and everything after it.

    Scans the last 1000 lines for a line composed solely of asterisks and
    whitespace. If found, truncates that line and everything below it.
    """
    total = len(lines)
    start = max(0, total - 1000)
    for i in range(total - 1, start - 1, -1):
        stripped = lines[i].strip()
        if stripped and _ASTERISK_DIVIDER_RE.match(stripped):
            return lines[:i]
    return lines


def _strip_trailing_transcriber_note(lines: list[str]) -> list[str]:
    """Remove a trailing transcriber note block and everything after it.

    Scans the last 1000 lines for a line matching the transcriber note
    pattern. If found, truncates that line and everything below it.
    """
    total = len(lines)
    start = max(0, total - 1000)
    for i in range(total - 1, start - 1, -1):
        if _is_transcriber_line(lines[i]):
            return lines[:i]
    return lines


def _strip_illustrations(lines: list[str]) -> list[str]:
    """Remove single lines that are illustration markers like [Illustration ...]."""
    return [
        line
        for line in lines
        if not (line.strip().lower().startswith("[illustration") and line.strip().endswith("]"))
    ]


def _strip_trailing_index(lines: list[str]) -> list[str]:
    """Remove an INDEX section and everything after it.

    Scans the entire file for a line that is exactly 'INDEX'
    (case-insensitive, ignoring whitespace). Truncates that line
    and everything below it.
    """
    for i, line in enumerate(lines):
        if line.strip().lower() == "index":
            return lines[:i]
    return lines


def _strip_trailing_footnotes(lines: list[str]) -> list[str]:
    """Remove a FOOTNOTES section and everything after it.

    Scans the last 1000 lines for a line that is exactly 'FOOTNOTES'
    (case-insensitive, ignoring whitespace). Truncates that line
    and everything below it.
    """
    total = len(lines)
    start = max(0, total - 1000)
    for i in range(total - 1, start - 1, -1):
        if lines[i].strip().lower() == "footnotes":
            return lines[:i]
    return lines


def _strip_underscore_italics(lines: list[str]) -> list[str]:
    """Remove underscore italic markup from all lines.

    Converts ``_word_`` → ``word`` and ``_long phrase_`` → ``long phrase``.
    Uses a regex with word boundaries so that snake_case identifiers
    (unlikely in Gutenberg prose but theoretically possible) are left alone.

    Returns a new list of lines with underscores stripped.
    """
    return [_UNDERSCORE_ITALIC_RE.sub(r"\1", line) for line in lines]


def _normalize_allcaps_headings(lines: list[str]) -> list[str]:
    """Convert ALL CAPS heading lines to title case and ensure blank-line isolation.

    A line qualifies as an ALL CAPS heading when:
      - it contains at least one letter,
      - every letter on the line is uppercase (ignoring digits, punctuation,
        whitespace, and Roman-numeral decorations like periods or dashes), and
      - it is not *only* whitespace/punctuation (must have alphabetic content).

    Qualifying lines are converted to title case.  If the line above or below
    is non-blank, a blank line is inserted so downstream tools treat the
    heading as a separate paragraph.

    Returns a new list of lines.
    """
    result: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip blank lines — pass through unchanged.
        if not stripped:
            result.append(line)
            continue

        # Check whether every letter on the line is uppercase.
        letters = [ch for ch in stripped if ch.isalpha()]
        is_allcaps = len(letters) >= 2 and all(ch.isupper() for ch in letters)

        if is_allcaps:
            # Convert to title case, preserving original trailing whitespace.
            title_line = stripped.title() + "\n"

            # Ensure a blank line *before* the heading if the previous line
            # is non-blank (and we already emitted at least one line).
            if result and result[-1].strip():
                result.append("\n")

            result.append(title_line)

            # Ensure a blank line *after* the heading if the next line exists
            # and is non-blank.
            next_idx = i + 1
            if next_idx < len(lines) and lines[next_idx].strip():
                result.append("\n")
        else:
            result.append(line)

    return result


def _strip_inline_footnotes(lines: list[str]) -> list[str]:
    """Remove inline footnote markers and footnote bodies from text lines.

    Strips two kinds of patterns:
      1. Full inline footnotes:  ``[Footnote 1: explanatory text here]``
      2. Bare reference markers: ``[1]``, ``[23]``, etc.

    The trailing FOOTNOTES *section* is already removed by
    ``_strip_trailing_footnotes()``; this function handles references
    that appear inline within body paragraphs.

    Returns a new list of lines with footnote artifacts removed.
    """
    return [_INLINE_FOOTNOTE_RE.sub("", line) for line in lines]


def _strip_leading_blanks(lines: list[str]) -> list[str]:
    """Remove all leading blank lines."""
    for i, line in enumerate(lines):
        if line.strip():
            return lines[i:]
    return lines


def clean_file(filepath: Path) -> None:
    """Clean a downloaded text file in place."""
    text = filepath.read_text(encoding="utf-8")
    cleaned = clean_text(text)
    filepath.write_text(cleaned, encoding="utf-8")
