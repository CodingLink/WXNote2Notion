from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion.client import NotionClient
from notion.repo_books import upsert_book
from notion.repo_daily import upsert_daily
from notion.repo_notes import embed_notes_in_book_page
from viz.heatmap import write_heatmap
from wechat_read.model import Note
from wechat_read import parser as wx_parser


def _load_notes(paths: Iterable[Path]) -> Tuple[List[Note], Counter]:
    return wx_parser.parse_dir(paths)


def _gather_files(notes_dir: Path) -> List[Path]:
    return sorted(notes_dir.glob("**/*.txt"))


def _group_notes(notes: List[Note]) -> Dict[str, Dict[str, object]]:
    grouped: Dict[str, Dict[str, object]] = defaultdict(lambda: {"notes": [], "author": None, "latest": None})
    for note in notes:
        entry = grouped[note.book_title]
        entry["notes"].append(note)
        entry["author"] = entry["author"] or note.author
        if note.created_date:
            current = entry["latest"]
            if current is None or note.created_date > current:
                entry["latest"] = note.created_date
    return grouped


def _extract_title(properties: Dict[str, object], prop_name: str) -> Optional[str]:
    prop = properties.get(prop_name) or {}
    if not isinstance(prop, dict):
        return None
    titles = prop.get("title") or []
    if not titles:
        return None
    first = titles[0]
    if not isinstance(first, dict):
        return None
    text = first.get("plain_text")
    return text


def _index_database_by_title(client: NotionClient, database_id: str, title_prop: str) -> Dict[str, Dict[str, Optional[str]]]:
    pages = client.query_all(database_id)
    index: Dict[str, Dict[str, Optional[str]]] = {}
    for page in pages:
        props = page.get("properties", {})
        title = _extract_title(props, title_prop)
        if not title:
            continue
        index[title] = {
            "page_id": page.get("id"),
        }
    return index


def sync_notes(
    notes: List[Note],
    daily_counts: Counter,
    notion_token: str,
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

    grouped_notes = _group_notes(notes)

    existing_books = _index_database_by_title(client, books_db, title_prop="Name")

    for title, payload in grouped_notes.items():
        author = payload["author"]
        last_note_date = payload["latest"]
        existing_book_id = existing_books.get(title, {}).get("page_id") if title in existing_books else None
        page_id, cover_url = upsert_book(
            client,
            database_id=books_db,
            title=title,
            author=author,  # type: ignore[arg-type]
            last_note_date=last_note_date,  # type: ignore[arg-type]
            allow_cover_fetch=allow_cover_fetch,
            existing_page_id=existing_book_id,
        )
        book_map[title] = page_id
    print(f"Upserted {len(book_map)} books")

    for title, payload in grouped_notes.items():
        book_page_id = book_map[title]
        embed_notes_in_book_page(
            client,
            book_page_id=book_page_id,
            book_title=title,
            notes=payload["notes"],  # type: ignore[arg-type]
        )
    print(f"Embedded notes into {len(grouped_notes)} book pages")

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
        books_db = args.books_db or os.getenv("NOTION_BOOKS_DB")
        daily_db = args.daily_db or os.getenv("NOTION_DAILY_DB")
        missing = [
            ("NOTION_TOKEN", notion_token),
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
            books_db=books_db,  # type: ignore[arg-type]
            daily_db=daily_db,  # type: ignore[arg-type]
            allow_cover_fetch=not args.no_cover,
            dry_run=args.dry_run,
        )

    if args.mode in {"heatmap", "all"}:
        generate_heatmap(daily_counts, Path("site"))


if __name__ == "__main__":
    main()
