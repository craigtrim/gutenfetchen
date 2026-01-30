"""Strip Project Gutenberg boilerplate from downloaded texts."""

from __future__ import annotations

import re
from pathlib import Path

_BOILERPLATE_DIR = Path(__file__).parent / "boilerplate"


def _load_boilerplate_blocks() -> list[str]:
    """Load all .txt files from the boilerplate/ directory.

    Each file contains a block of text that must be stripped from
    downloaded books.  Returns a list of normalised block strings
    (whitespace-collapsed, lowercased) used for fuzzy matching.
    """
    blocks: list[str] = []
    if _BOILERPLATE_DIR.is_dir():
        for path in sorted(_BOILERPLATE_DIR.glob("*.txt")):
            blocks.append(path.read_text(encoding="utf-8"))
    return blocks


def _normalize_ws(text: str) -> str:
    """Collapse all whitespace to single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_boilerplate_blocks(text: str) -> str:
    """Remove any block of text that matches a file in boilerplate/.

    Matching is whitespace-insensitive and case-insensitive: both the
    source text and the boilerplate templates are normalised before
    comparison.  When a match is found the *original* lines covering
    that block are removed.

    This function runs on the raw text (before line splitting) and
    must be the very first cleaning step.
    """
    for block in _load_boilerplate_blocks():
        norm_block = _normalize_ws(block)
        if not norm_block:
            continue

        norm_text = _normalize_ws(text)
        if norm_block not in norm_text:
            continue

        # Walk the original text to find the span that matches.
        # Build a mapping from normalised-char-index → original-char-index.
        # Instead, use a simpler line-based approach: find the first line
        # of the block in the original text, then consume forward.
        block_lines = [ln.strip().lower() for ln in block.splitlines() if ln.strip()]
        if not block_lines:
            continue

        text_lines = text.splitlines(keepends=True)
        first_target = block_lines[0]

        for i, line in enumerate(text_lines):
            if first_target not in line.strip().lower():
                continue

            # Try to match all block lines starting from line i.
            bi = 0  # index into block_lines
            ti = i  # index into text_lines
            while bi < len(block_lines) and ti < len(text_lines):
                tl = text_lines[ti].strip().lower()
                if not tl:
                    ti += 1
                    continue
                if block_lines[bi] in tl:
                    bi += 1
                    ti += 1
                else:
                    break

            if bi == len(block_lines):
                # Matched the full block from line i to ti-1.
                text = "".join(text_lines[:i] + text_lines[ti:])
                break  # restart outer loop implicitly on next block

    return text


def clean_text(text: str) -> str:
    """Remove everything up to and including '*** START' line,
    and everything from '*** END' line onward."""

    # First pass: strip known boilerplate blocks (coarse-grained,
    # runs before line splitting so multi-line blocks are matched).
    text = _strip_boilerplate_blocks(text)

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
    lines = _strip_end_of_project(lines)
    # Issue #2: disabled — greedy match on `* * * * *` truncates legitimate
    # content dividers mid-book (e.g. pg588 loses ~500 lines).
    # lines = _strip_trailing_divider(lines)
    lines = _strip_trailing_transcriber_note(lines)
    lines = _strip_illustrations(lines)
    lines = _strip_multiline_brackets(lines)
    lines = _strip_trailing_index(lines)
    lines = _strip_trailing_footnotes(lines)

    # --- Issue #1: additional inline cleanup ---
    # Strip _italic_ underscore markup (e.g. _Les Huguenots_ → Les Huguenots)
    lines = _strip_underscore_italics(lines)
    # Remove inline [Footnote N: ...] bodies and [N] back-references
    lines = _strip_inline_footnotes(lines)
    # Normalize ALL CAPS headings to title case with blank-line isolation
    lines = _normalize_allcaps_headings(lines)

    lines = _strip_ebook_usage_notice(lines)
    lines = _strip_decorative_lines(lines)
    lines = _strip_url_or_email_lines(lines)
    lines = _strip_internet_archive_lines(lines)

    # --- Final pass: must always run last ---
    lines = _strip_project_gutenberg_lines(lines)

    # Strip leading/trailing blank lines left over after all removals
    lines = _strip_leading_blanks(lines)
    lines = _strip_trailing_blanks(lines)

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
    r"|\[\d+\]",  # [1], [23], etc.
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


_END_OF_PROJECT_PREFIXES = (
    "end of project",
    "end of the project",
)


def _strip_end_of_project(lines: list[str]) -> list[str]:
    """Remove a standalone 'End of Project' line and everything after it.

    Matches lines starting with 'End of Project' or 'End of the Project'
    (case-insensitive). Scans the last 1000 lines backward.
    """
    total = len(lines)
    start = max(0, total - 1000)
    for i in range(total - 1, start - 1, -1):
        lower = lines[i].strip().lower()
        if any(lower.startswith(p) for p in _END_OF_PROJECT_PREFIXES):
            return lines[:i]
    return lines


# Issue #2: disabled — greedy match on `* * * * *` truncates legitimate
# content dividers mid-book (e.g. pg588 loses ~500 lines). The *** END
# marker and _strip_project_gutenberg_lines catch-all now handle this.
#
# def _strip_trailing_divider(lines: list[str]) -> list[str]:
#     """Remove a trailing asterisk divider and everything after it.
#
#     Scans the last 1000 lines for a line composed solely of asterisks and
#     whitespace. If found, truncates that line and everything below it.
#     """
#     total = len(lines)
#     start = max(0, total - 1000)
#     for i in range(total - 1, start - 1, -1):
#         stripped = lines[i].strip()
#         if stripped and _ASTERISK_DIVIDER_RE.match(stripped):
#             return lines[:i]
#     return lines


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


def _strip_multiline_brackets(lines: list[str]) -> list[str]:
    """Remove multi-line bracketed blocks (up to 5 continuation lines).

    Detects a line starting with ``[`` that does not close with ``]`` on the
    same line, then looks ahead up to 5 lines for the closing ``]``.  If
    found, all lines from the opener through the closer are removed.

    This catches multi-line illustration captions, editor notes, etc.::

        [Illustration: signed: Yours sincerely,

        Jerome K. Jerome]
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("[") and not stripped.endswith("]"):
            # Look ahead up to 5 lines for closing ]
            found_end = False
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].rstrip().endswith("]"):
                    # Skip lines i..j (inclusive)
                    i = j + 1
                    found_end = True
                    break
            if found_end:
                continue
        result.append(lines[i])
        i += 1
    return result


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


def _strip_decorative_lines(lines: list[str]) -> list[str]:
    """Remove standalone decorative lines wrapped in asterisks.

    Matches lines like ``***Finis***``, ``*** THE END ***``, etc. — any
    single line whose content starts with ``***`` and ends with ``***``
    (ignoring surrounding whitespace).
    """
    return [
        line
        for line in lines
        if not (
            line.strip().startswith("***")
            and line.strip().endswith("***")
            and len(line.strip()) > 6
        )
    ]


_URL_OR_EMAIL_RE = re.compile(
    r"https?://\S+"  # http:// or https:// URLs
    r"|www\.\S+"  # www. URLs without scheme
    r"|\S+@\S+\.\S+",  # email addresses
)


def _strip_url_or_email_lines(lines: list[str]) -> list[str]:
    """Remove lines that contain a URL or email address."""
    return [line for line in lines if not _URL_OR_EMAIL_RE.search(line)]


def _strip_internet_archive_lines(lines: list[str]) -> list[str]:
    """Remove lines that mention the Internet Archive."""
    return [line for line in lines if "internet archive" not in line.lower()]


def _strip_ebook_usage_notice(lines: list[str]) -> list[str]:
    """Remove the Gutenberg eBook usage/license notice block.

    Detects a paragraph starting with 'This eBook is for the use of anyone
    anywhere' and removes it through the end of that paragraph (next blank
    line or end of file).
    """
    trigger = "this ebook is for the use of anyone anywhere"
    for i, line in enumerate(lines):
        if line.strip().lower().startswith(trigger):
            # Find end of paragraph (next blank line or EOF)
            end = i + 1
            while end < len(lines) and lines[end].strip():
                end += 1
            return lines[:i] + lines[end:]
    return lines


def _strip_leading_blanks(lines: list[str]) -> list[str]:
    """Remove all leading blank lines."""
    for i, line in enumerate(lines):
        if line.strip():
            return lines[i:]
    return lines


def _strip_trailing_blanks(lines: list[str]) -> list[str]:
    """Remove all trailing blank lines."""
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            return lines[: i + 1]
    return lines


def _strip_project_gutenberg_lines(lines: list[str]) -> list[str]:
    """Remove any line that contains 'Project Gutenberg' (case-insensitive).

    This is a catch-all safety net for residual boilerplate that survives
    earlier, more targeted stripping passes.  It MUST always run last in
    the ``clean_text`` pipeline so it never masks a bug in an upstream step.
    """
    return [line for line in lines if "project gutenberg" not in line.lower()]


def clean_file(filepath: Path) -> None:
    """Clean a downloaded text file in place."""
    text = filepath.read_text(encoding="utf-8")
    cleaned = clean_text(text)
    filepath.write_text(cleaned, encoding="utf-8")
