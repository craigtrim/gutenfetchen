"""Integration tests that hit the live Gutendex API.

Run with: poetry run pytest -m integration
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gutenfetchen.cli import main


@pytest.mark.integration
def test_random_download_one_book() -> None:
    """Download 1 random book to /tmp and verify the file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = main(["--random", "1", "--output-dir", tmpdir])
        assert result == 0
        txt_files = list(Path(tmpdir).glob("*.txt"))
        assert len(txt_files) == 1, f"Expected 1 .txt file, got {len(txt_files)}: {txt_files}"
