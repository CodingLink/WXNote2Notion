from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .client import NotionClient
from wechat_read.model import Note


def _note_summary(note: Note) -> str:
    text = note.highlight_text or note.note_text or note.section_title or note.book_title
    first_line = text.splitlines()[0] if text else note.book_title
    return first_line[:180]


def _note_blocks(note: Note) -> Dict:
    body_blocks = []
    if note.highlight_text:
        body_blocks.append(
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"text": {"content": note.highlight_text}}]},
            }
        )
    if note.note_text:
        body_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": note.note_text}}]},
            }
        )

    meta_parts = []
    if note.created_date:
        meta_parts.append(f"Date: {note.created_date.isoformat()}")
    if note.section_title:
        meta_parts.append(f"Section: {note.section_title}")
    if note.item_type:
        meta_parts.append(f"Type: {note.item_type}")
    if meta_parts:
        body_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": " | ".join(meta_parts)}}]},
            }
        )

    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": {"content": _note_summary(note)}}],
            "children": body_blocks,
        },
    }


def _group_by_section(notes: List[Note]) -> Dict[str, List[Note]]:
    grouped: Dict[str, List[Note]] = defaultdict(list)
    for note in notes:
        grouped[note.section_title or ""].append(note)
    return grouped


def _book_children(book_title: str, notes: List[Note]) -> List[Dict]:
    children: List[Dict] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": book_title}}]},
        }
    ]
    grouped = _group_by_section(notes)
    for section, items in grouped.items():
        if section:
            children.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"text": {"content": section}}]},
                }
            )
        for note in items:
            children.append(_note_blocks(note))
    return children


def _replace_page_children(client: NotionClient, page_id: str, children: List[Dict]) -> None:
    cursor = None
    while True:
        result = client.list_block_children(page_id, start_cursor=cursor)
        for child in result.get("results", []):
            client.delete_block(child["id"])
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")

    BATCH = 50
    for i in range(0, len(children), BATCH):
        client.append_block_children(page_id, children[i : i + BATCH])


def embed_notes_in_book_page(
    client: NotionClient,
    book_page_id: str,
    book_title: str,
    notes: List[Note],
) -> None:
    if not notes:
        return
    content = _book_children(book_title, notes)
    _replace_page_children(client, book_page_id, content)
