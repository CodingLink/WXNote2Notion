from __future__ import annotations

from typing import Optional

from .client import NotionClient, title_text


def ensure_dashboard(
    client: NotionClient,
    parent_page_id: str,
    heatmap_url: str,
    title: str = "WeChat Read Dashboard",
) -> str:
    # Lightweight helper that creates a dashboard page with an embed block for the heatmap.
    payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {"Title": title_text(title)},
        "children": [
            {
                "object": "block",
                "type": "embed",
                "embed": {"url": heatmap_url},
            }
        ],
    }
    created = client._request("POST", "pages", json=payload)
    return created["id"]
