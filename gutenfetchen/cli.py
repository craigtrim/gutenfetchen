"""Command-line interface for gutenfetchen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gutenfetchen.api import fetch_random, search_all_pages, search_books
from gutenfetchen.dedup import deduplicate, filter_by_author, filter_has_text, filter_text_only
from gutenfetchen.downloader import download_books


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="gutenfetchen",
        description="Download e-texts from Project Gutenberg",
    )
    parser.add_argument(
        "title",
        nargs="?",
        help="Search by title (e.g., 'tale of two cities')",
    )
    parser.add_argument(
        "--author",
        help="Search by author name (e.g., 'joseph conrad')",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        dest="limit",
        help="Maximum number of texts to download",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("./gutenberg_texts"),
        help="Output directory (default: ./gutenberg_texts/)",
    )
    parser.add_argument(
        "--random",
        type=int,
        default=None,
        metavar="N",
        help="Download N random e-texts (any author, any text)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching books without downloading",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip stripping Project Gutenberg boilerplate from texts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.title and not args.author and not args.random:
        parser.error("Provide a title, --author, or --random")

    # Banner
    print("=" * 60)
    print("  gutenfetchen")
    print("=" * 60)
    if args.random:
        print(f"  mode        : random ({args.random} texts)")
    elif args.title and not args.author:
        print("  mode        : title search")
        print(f"  title       : {args.title}")
    else:
        print("  mode        : author search")
        if args.title:
            print(f"  title       : {args.title}")
        print(f"  author      : {args.author}")
    print(f"  limit       : {args.limit or 'none'}")
    print(f"  output dir  : {args.output_dir.resolve()}")
    print(f"  dry run     : {args.dry_run}")
    print(f"  clean texts : {not args.no_clean}")
    print("=" * 60)
    print()

    if args.random:
        # Random mode: fetch N random books
        print(f"Fetching {args.random} random e-text(s)...")
        books = fetch_random(args.random)
    elif args.title and not args.author:
        # Title search: find best match
        print(f"Searching for '{args.title}'...")
        result = search_books(args.title)
        if not result.books:
            print(f"No results for '{args.title}'")
            return 1
        books = filter_text_only(filter_has_text(result.books))
        if not books:
            print("No plain-text versions available")
            return 1
        books = [books[0]]
    else:
        # Author search (optionally combined with title)
        query = args.author
        if args.title:
            query = f"{args.author} {args.title}"
        print(f"Searching for works by '{args.author}'...")
        all_books = search_all_pages(query)
        books = filter_by_author(all_books, args.author)
        books = filter_text_only(filter_has_text(books))
        books = deduplicate(books)

    if not books:
        print("No matching books found")
        return 1

    display_books = books[: args.limit] if args.limit else books

    if args.dry_run:
        print(f"Found {len(books)} book(s):")
        for i, book in enumerate(display_books, 1):
            authors = ", ".join(a.display_name for a in book.authors)
            print(f"  {i}. {book.title} — {authors} (id={book.id})")
        return 0

    paths = download_books(books, args.output_dir, limit=args.limit, clean=not args.no_clean)
    print(f"\nDownloaded {len(paths)} text(s) to {args.output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
