from __future__ import annotations

import argparse
import os
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

from notion.client import NotionClient
from notion.repo_books import upsert_book
from notion.repo_daily import upsert_daily
from notion.repo_notes import upsert_note
from viz.heatmap import write_heatmap
from wechat_read.model import Note
from wechat_read import parser as wx_parser


def _load_notes(paths: Iterable[Path]) -> Tuple[List[Note], Counter]:
    return wx_parser.parse_dir(paths)


def _gather_files(notes_dir: Path) -> List[Path]:
    return sorted(notes_dir.glob("**/*.txt"))


def _unique_books(notes: List[Note]) -> Dict[str, Tuple[Optional[str], Optional[date]]]:
    books: Dict[str, Tuple[Optional[str], Optional[date]]] = {}
    for note in notes:
        current_author, current_date = books.get(note.book_title, (None, None))
        author = current_author or note.author
        # track latest created_date
        latest_date = current_date
        if note.created_date:
            if not latest_date or note.created_date > latest_date:
                latest_date = note.created_date
        books[note.book_title] = (author, latest_date)
    return books


def sync_notes(
    notes: List[Note],
    daily_counts: Counter,
    notion_token: str,
    notes_db: str,
    books_db: str,
    daily_db: str,
    allow_cover_fetch: bool,
    dry_run: bool,
) -> None:
    if dry_run:
        print("[dry-run] Skipping Notion sync")
        return
    client = NotionClient(notion_token)

    book_map: Dict[str, str] = {}
    cover_map: Dict[str, str] = {}

    for title, (author, last_note_date) in _unique_books(notes).items():
        page_id, cover_url = upsert_book(
            client,
            database_id=books_db,
            title=title,
            author=author,
            last_note_date=last_note_date,
            allow_cover_fetch=allow_cover_fetch,
        )
        book_map[title] = page_id
        if cover_url:
            cover_map[title] = cover_url
    print(f"Upserted {len(book_map)} books")

    for note in notes:
        book_page_id = book_map[note.book_title]
        upsert_note(client, database_id=notes_db, note=note, book_page_id=book_page_id)
    print(f"Upserted {len(notes)} notes")

    for day, count in daily_counts.items():
        upsert_daily(client, database_id=daily_db, day=day, count=count)
    print(f"Upserted {len(daily_counts)} daily activity rows")


def generate_heatmap(daily_counts: Counter, output_dir: Path) -> None:
    write_heatmap(daily_counts, output_dir)
    print(f"Generated heatmap in {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync WeChat Read notes to Notion")
    parser.add_argument("--notes-dir", default="notes", help="Directory containing TXT exports")
    parser.add_argument("--mode", choices=["parse", "sync", "heatmap", "all"], default="all")
    parser.add_argument("--year", type=int, help="Year for heatmap (defaults to current year)")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes to Notion")
    parser.add_argument("--no-cover", action="store_true", help="Disable Douban/OpenLibrary cover fetch")
    parser.add_argument("--notion-token", help="Override NOTION_TOKEN env")
    parser.add_argument("--notes-db", help="Override NOTION_NOTES_DB env")
    parser.add_argument("--books-db", help="Override NOTION_BOOKS_DB env")
    parser.add_argument("--daily-db", help="Override NOTION_DAILY_DB env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    notes_dir = Path(args.notes_dir)
    files = _gather_files(notes_dir)
    if not files:
        print(f"No TXT files found in {notes_dir}")
        return

    notes, daily_counts = _load_notes(files)
    print(f"Parsed {len(notes)} notes across {len(files)} files")

    if args.mode in {"sync", "all"}:
        notion_token = args.notion_token or os.getenv("NOTION_TOKEN")
        notes_db = args.notes_db or os.getenv("NOTION_NOTES_DB")
        books_db = args.books_db or os.getenv("NOTION_BOOKS_DB")
        daily_db = args.daily_db or os.getenv("NOTION_DAILY_DB")
        missing = [
            ("NOTION_TOKEN", notion_token),
            ("NOTES_DB", notes_db),
            ("BOOKS_DB", books_db),
            ("DAILY_DB", daily_db),
        ]
        missing_keys = [k for k, v in missing if not v]
        if missing_keys:
            raise SystemExit(f"Missing Notion config: {', '.join(missing_keys)}")
        sync_notes(
            notes,
            daily_counts,
            notion_token=notion_token,  # type: ignore[arg-type]
            notes_db=notes_db,  # type: ignore[arg-type]
            books_db=books_db,  # type: ignore[arg-type]
            daily_db=daily_db,  # type: ignore[arg-type]
            allow_cover_fetch=not args.no_cover,
            dry_run=args.dry_run,
        )

    if args.mode in {"heatmap", "all"}:
        generate_heatmap(daily_counts, Path("site"))


if __name__ == "__main__":
    main()
