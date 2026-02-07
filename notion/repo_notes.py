from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .client import NotionClient, rich_text, title_text
from wechat_read.model import Note


def _date_payload(dt) -> Optional[Dict]:
    if not dt:
        return None
    return {"date": {"start": dt.isoformat()}}


def _build_children(note: Note) -> list:
    blocks = []
    blocks.append(
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"text": {"content": note.book_title}}]},
        }
    )
    if note.section_title:
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": f"Section: {note.section_title}"}}]},
            }
        )
    if note.highlight_text:
        blocks.append(
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"text": {"content": note.highlight_text}}]},
            }
        )
    if note.note_text:
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": note.note_text}}]},
            }
        )
    return blocks


def _note_properties(note: Note, book_page_id: str) -> Dict:
    note.ensure_fingerprint()
    title_val = note.highlight_text or note.note_text or note.section_title or note.book_title
    props = {
        "Title": title_text(title_val[:2000]),
        "Book": {"relation": [{"id": book_page_id}]},
        "Type": {"select": {"name": note.item_type}},
        "Source": {"select": {"name": note.source}},
        "Fingerprint": rich_text(note.fingerprint),
        "Import Time": {"date": {"start": datetime.utcnow().date().isoformat()}},
    }
    if note.section_title:
        props["Section"] = rich_text(note.section_title)
    if note.highlight_text:
        props["Highlight"] = rich_text(note.highlight_text)
    if note.note_text:
        props["Note"] = rich_text(note.note_text)
    if note.created_date:
        props["Created Date"] = {"date": {"start": note.created_date.isoformat()}}
    return props


def upsert_note(
    client: NotionClient,
    database_id: str,
    note: Note,
    book_page_id: str,
) -> str:
    note.ensure_fingerprint()
    filter_payload = {
        "property": "Fingerprint",
        "rich_text": {"equals": note.fingerprint},
    }
    query = client.query_database(database_id, filter=filter_payload)
    results = query.get("results", [])
    props = _note_properties(note, book_page_id)
    children = _build_children(note)

    if results:
        page_id = results[0]["id"]
        client.update_page(page_id, properties=props)
        return page_id

    created = client.create_page(
        database_id,
        properties=props,
        children=children,
        icon={"type": "emoji", "emoji": "📝"},
    )
    return created["id"]
