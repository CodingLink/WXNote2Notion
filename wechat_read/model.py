from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Optional


def _safe_text(text: Optional[str]) -> str:
    return text or ""


def compute_fingerprint(
    book_title: str,
    created_date: Optional[date],
    section_title: Optional[str],
    highlight_text: Optional[str],
    note_text: Optional[str],
) -> str:
    """Compute a stable SHA256 fingerprint for idempotency."""
    book = _safe_text(book_title)
    highlight = _safe_text(highlight_text)
    note = _safe_text(note_text)
    section = _safe_text(section_title)
    if created_date:
        key = f"{book}|{created_date.isoformat()}|{highlight}|{note}"
    else:
        key = f"{book}|{section}|{highlight}|{note}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass
class Note:
    book_title: str
    author: Optional[str]
    section_title: Optional[str]
    item_type: str  # highlight | thought | mixed
    highlight_text: Optional[str]
    note_text: Optional[str]
    created_date: Optional[date]
    source: str = "WeChat Read"
    fingerprint: Optional[str] = None

    def ensure_fingerprint(self) -> str:
        if not self.fingerprint:
            self.fingerprint = compute_fingerprint(
                book_title=self.book_title,
                created_date=self.created_date,
                section_title=self.section_title,
                highlight_text=self.highlight_text,
                note_text=self.note_text,
            )
        return self.fingerprint
