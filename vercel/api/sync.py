from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from scripts.sync_repo import _gather_files, _load_notes, generate_heatmap, sync_notes


def _json(status: int, body: Dict[str, Any]):
    return status, {"Content-Type": "application/json"}, body


def handler(request):
    expected = os.getenv("SYNC_TOKEN")
    provided = None
    if hasattr(request, "args"):
        provided = request.args.get("token")
    if expected and provided != expected:
        return _json(401, {"error": "unauthorized"})

    notes_dir = Path("notes")
    files = _gather_files(notes_dir)
    notes, daily_counts = _load_notes(files)

    notion_token = os.getenv("NOTION_TOKEN")
    notes_db = os.getenv("NOTION_NOTES_DB")
    books_db = os.getenv("NOTION_BOOKS_DB")
    daily_db = os.getenv("NOTION_DAILY_DB")
    missing = [k for k, v in {
        "NOTION_TOKEN": notion_token,
        "NOTION_NOTES_DB": notes_db,
        "NOTION_BOOKS_DB": books_db,
        "NOTION_DAILY_DB": daily_db,
    }.items() if not v]
    if missing:
        return _json(500, {"error": f"missing env: {', '.join(missing)}"})

    sync_notes(
        notes=notes,
        daily_counts=daily_counts,
        notion_token=notion_token,  # type: ignore[arg-type]
        notes_db=notes_db,  # type: ignore[arg-type]
        books_db=books_db,  # type: ignore[arg-type]
        daily_db=daily_db,  # type: ignore[arg-type]
        allow_cover_fetch=True,
        dry_run=False,
    )
    generate_heatmap(daily_counts, Path("site"))
    return _json(200, {"status": "ok", "notes": len(notes)})
