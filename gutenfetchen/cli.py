"""Command-line interface for gutenfetchen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from gutenfetchen.api import fetch_random, search_all_pages, search_books
from gutenfetchen.dedup import (
    deduplicate,
    filter_by_author,
    filter_has_text,
    filter_text_only,
    filter_volumes,
)
from gutenfetchen.downloader import download_books

console = Console()


def _cfg(label: str, value: object) -> str:
    """Format a config line with dim label and bold value."""
    return f"  [dim]{label:<14}:[/dim] [bold]{value}[/bold]"


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
    parser.add_argument(
        "--include-volumes",
        action="store_true",
        help="Include volume splits (e.g. Vol. 1, Vol. 2) even when the whole book exists",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Ignore cached catalog pages and re-fetch from the Gutendex API",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.title and not args.author and not args.random:
        parser.error("Provide a title, --author, or --random")

    # Banner
    console.rule("[bold cyan]gutenfetchen[/bold cyan]", style="cyan")
    if args.random:
        console.print(_cfg("mode", f"random ({args.random} texts)"))
    elif args.title and not args.author:
        console.print(_cfg("mode", "title search"))
        console.print(_cfg("title", args.title))
    else:
        console.print(_cfg("mode", "author search"))
        if args.title:
            console.print(_cfg("title", args.title))
        console.print(_cfg("author", args.author))
    console.print(_cfg("limit", args.limit or "none"))
    console.print(_cfg("output dir", args.output_dir.resolve()))
    console.print(_cfg("dry run", args.dry_run))
    console.print(_cfg("clean texts", not args.no_clean))
    console.print(_cfg("incl. volumes", args.include_volumes))
    console.rule(style="cyan")
    console.print()

    if args.random:
        # Random mode: fetch N random books
        console.print(f"[yellow]Fetching {args.random} random e-text(s)...[/yellow]")
        books = fetch_random(args.random)
    elif args.title and not args.author:
        # Title search: find best match
        console.print(f"[yellow]Searching for '{args.title}'...[/yellow]")
        result = search_books(args.title)
        if not result.books:
            console.print(f"[bold red]No results for '{args.title}'[/bold red]")
            return 1
        books = filter_text_only(filter_has_text(result.books))
        if not books:
            console.print("[bold red]No plain-text versions available[/bold red]")
            return 1
        books = [books[0]]
    else:
        # Author search (optionally combined with title)
        query = args.author
        if args.title:
            query = f"{args.author} {args.title}"
        console.print(f"[yellow]Searching for works by '{args.author}'...[/yellow]")
        all_books = search_all_pages(query, refresh=args.refresh_cache)
        books = filter_by_author(all_books, args.author)
        books = filter_text_only(filter_has_text(books))
        books = deduplicate(books)
        if not args.include_volumes:
            books = filter_volumes(books)

    if not books:
        console.print("[bold red]No matching books found[/bold red]")
        return 1

    display_books = books[: args.limit] if args.limit else books

    if args.dry_run:
        console.print(f"Found [bold]{len(books)}[/bold] book(s):")
        for i, book in enumerate(display_books, 1):
            authors = ", ".join(a.display_name for a in book.authors)
            console.print(f"  {i}. [bold]{book.title}[/bold] [dim]— {authors} (id={book.id})[/dim]")
        return 0

    paths = download_books(books, args.output_dir, limit=args.limit, clean=not args.no_clean)
    console.print(
        f"\n[bold green]Downloaded {len(paths)} text(s) to {args.output_dir}/[/bold green]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
