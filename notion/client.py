from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_HEADERS = {
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


class NotionClient:
    def __init__(self, token: str, max_retries: int = 3, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.max_retries = max_retries
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{NOTION_API_BASE}/{path.lstrip('/') }"
        for attempt in range(1, self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue
            if 500 <= response.status_code < 600 and attempt < self.max_retries:
                time.sleep(1.5 * attempt)
                continue
            if not response.ok:
                raise RuntimeError(
                    f"Notion API error {response.status_code}: {response.text}"
                )
            return response.json()
        raise RuntimeError("Exceeded retry attempts for Notion API")

    def query_database(
        self,
        database_id: str,
        filter: Optional[Dict[str, Any]] = None,
        sorts: Optional[Any] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"page_size": page_size}
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
        return self._request("POST", f"databases/{database_id}/query", json=payload)

    def create_page(
        self,
        database_id: str,
        properties: Dict[str, Any],
        children: Optional[Any] = None,
        cover: Optional[Any] = None,
        icon: Optional[Any] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        if children:
            payload["children"] = children
        if cover:
            payload["cover"] = cover
        if icon:
            payload["icon"] = icon
        return self._request("POST", "pages", json=payload)

    def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        cover: Optional[Any] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if properties:
            payload["properties"] = properties
        if cover:
            payload["cover"] = cover
        return self._request("PATCH", f"pages/{page_id}", json=payload)


def rich_text(content: str) -> Dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": content}}]}


def title_text(content: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": content}}]}
