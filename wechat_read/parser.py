from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .model import Note, compute_fingerprint

DATE_RE = re.compile(r"(\d{4}/\d{1,2}/\d{1,2})")


def _parse_date(text: str) -> Optional[date]:
    try:
        return datetime.strptime(text.strip(), "%Y/%m/%d").date()
    except ValueError:
        return None


def _clean(line: str) -> str:
    return line.strip("\n\r ")


def _extract_date(text: str) -> Optional[date]:
    match = DATE_RE.search(text)
    if not match:
        return None
    return _parse_date(match.group(1))


def _parse_block(
    book_title: str,
    author: Optional[str],
    section_title: Optional[str],
    block_lines: List[str],
) -> Note:
    lines = [_clean(l) for l in block_lines if _clean(l) or _clean(l) == ""]
    header = lines[0] if lines else ""
    created = _extract_date(header)
    has_thought = "发表想法" in header

    highlight_text: Optional[str] = None
    note_text: Optional[str] = None

    if has_thought:
        # Next non-empty line is the thought body
        body_line: Optional[str] = None
        original_start_idx: Optional[int] = None
        for idx, line in enumerate(lines[1:], start=1):
            if line:
                if body_line is None:
                    body_line = line
                    continue
                if line.startswith("原文："):
                    original_start_idx = idx
                    break
        if body_line:
            note_text = body_line
        if original_start_idx is not None:
            original_lines: List[str] = []
            first_line = lines[original_start_idx].partition("原文：")[2].strip()
            if first_line:
                original_lines.append(first_line)
            for extra in lines[original_start_idx + 1 :]:
                if extra:
                    original_lines.append(extra)
            if original_lines:
                highlight_text = "\n".join(original_lines)
    else:
        # Treat all non-empty lines in the block as highlight text
        hl_lines = [line for line in lines if line]
        highlight_text = "\n".join(hl_lines) if hl_lines else None

    if highlight_text and note_text:
        item_type = "mixed"
    elif note_text:
        item_type = "thought"
    else:
        item_type = "highlight"

    fingerprint = compute_fingerprint(
        book_title=book_title,
        created_date=created,
        section_title=section_title,
        highlight_text=highlight_text,
        note_text=note_text,
    )

    return Note(
        book_title=book_title,
        author=author,
        section_title=section_title,
        item_type=item_type,
        highlight_text=highlight_text,
        note_text=note_text,
        created_date=created,
        fingerprint=fingerprint,
    )


def parse_file(path: Path) -> Tuple[List[Note], Counter]:
    """Parse TXT with rules: section starts at line 6; ends on two empty lines."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    raw_lines = text.splitlines()
    lines = [_clean(l) for l in raw_lines]

    def next_non_empty(start: int) -> Tuple[Optional[str], int]:
        i = start
        while i < len(lines):
            if lines[i]:
                return lines[i], i
            i += 1
        return None, len(lines)

    book_title, idx = next_non_empty(0)
    if book_title is None:
        return [], Counter()
    author, _ = next_non_empty(idx + 1)
    # Start parsing sections from line 6 (index 5) if possible
    idx = 5 if len(lines) > 5 else (idx + 1)

    notes: List[Note] = []
    daily = Counter()

    while idx < len(lines):
        if not lines[idx]:
            idx += 1
            continue
        section_title = lines[idx]
        idx += 1

        section_lines: List[str] = []
        empty_run = 0
        while idx < len(lines):
            line = lines[idx]
            if line == "":
                empty_run += 1
                if empty_run >= 2:
                    idx += 1
                    break
            else:
                empty_run = 0
            section_lines.append(line)
            idx += 1

        # Parse notes within the section
        i = 0
        while i < len(section_lines):
            line = section_lines[i]
            if not line or not line.startswith("◆"):
                i += 1
                continue
            block = [line.lstrip("◆ ")]
            i += 1
            while i < len(section_lines) and not section_lines[i].startswith("◆"):
                block.append(section_lines[i])
                i += 1
            note = _parse_block(
                book_title=book_title,
                author=author,
                section_title=section_title,
                block_lines=block,
            )
            notes.append(note)
            if note.created_date:
                daily[note.created_date] += 1
    return notes, daily


def parse_dir(paths: Iterable[Path]) -> Tuple[List[Note], Counter]:
    all_notes: List[Note] = []
    daily = Counter()
    for path in paths:
        file_notes, file_daily = parse_file(path)
        all_notes.extend(file_notes)
        daily.update(file_daily)
    return all_notes, daily
