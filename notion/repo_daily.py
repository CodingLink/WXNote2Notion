from __future__ import annotations

from datetime import datetime, date
from typing import Dict

from .client import NotionClient


def _properties(day: date, count: int) -> Dict:
    return {
        "Date": {"date": {"start": day.isoformat()}},
        "Notes Count": {"number": count},
        "Source": {"select": {"name": "WeChat Read"}},
        "Last Import Time": {"date": {"start": datetime.utcnow().date().isoformat()}},
    }


def upsert_daily(client: NotionClient, database_id: str, day: date, count: int) -> str:
    filter_payload = {"property": "Date", "date": {"equals": day.isoformat()}}
    query = client.query_database(database_id, filter=filter_payload)
    props = _properties(day, count)
    results = query.get("results", [])
    if results:
        page_id = results[0]["id"]
        client.update_page(page_id, properties=props)
        return page_id
    created = client.create_page(
        database_id,
        properties=props,
        icon={"type": "emoji", "emoji": "📅"},
    )
    return created["id"]
