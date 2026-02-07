from __future__ import annotations

import json
import re
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .client import NotionClient, rich_text, title_text

CACHE_PATH = Path(".cache/douban_cover.json")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0 Safari/537.36"
)


def _has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return any('\u4e00' <= char <= '\u9fff' for char in text)


def _clean_title_for_search(title: str) -> str:
    """Remove book title marks and extra spaces for better search results."""
    # Remove Chinese book title marks
    cleaned = title.replace('《', '').replace('》', '')
    # Remove English quotation marks
    cleaned = cleaned.replace('"', '').replace('"', '').replace('"', '')
    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned


def _load_cache() -> Dict[str, str]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: Dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _douban_cover(title: str, author: Optional[str]) -> Optional[str]:
    """Fetch cover from Douban with improved selectors."""
    search_q = title
    if author:
        search_q = f"{title} {author}"
    url = f"https://search.douban.com/book/subject_search?search_text={quote_plus(search_q)}"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=12)
    except Exception as e:
        return None
    if resp.status_code != 200:
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    # Try multiple selectors for book link
    link_tag = (
        soup.find("a", href=re.compile(r"/subject/\d+")) or
        soup.find("a", class_=re.compile(r"cover-link")) or
        soup.select_one(".item-root a[href*='/subject/']")
    )
    if not link_tag or not link_tag.get("href"):
        return None
    
    detail_url = link_tag.get("href")
    if detail_url.startswith("//"):
        detail_url = "https:" + detail_url
    elif detail_url.startswith("/"):
        detail_url = "https://book.douban.com" + detail_url
    elif not detail_url.startswith("http"):
        detail_url = "https://book.douban.com" + detail_url

    time.sleep(1.0)  # rate limit
    try:
        detail_resp = requests.get(detail_url, headers=headers, timeout=12)
    except Exception as e:
        return None
    if detail_resp.status_code != 200:
        return None
    
    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
    
    # Try multiple methods to get cover image
    # 1. og:image meta tag
    meta = detail_soup.find("meta", attrs={"property": "og:image"})
    if meta and meta.get("content"):
        return meta.get("content")
    
    # 2. mainpic img
    img_tag = detail_soup.find("img", id="mainpic")
    if img_tag and img_tag.get("src"):
        return img_tag.get("src")
    
    # 3. nbg class (common in Douban)
    img_tag = detail_soup.find("a", class_="nbg")
    if img_tag:
        img = img_tag.find("img")
        if img and img.get("src"):
            return img.get("src")
    
    # 4. Any img with subject_img class
    img_tag = detail_soup.find("img", class_=re.compile(r"subject.*img"))
    if img_tag and img_tag.get("src"):
        return img_tag.get("src")
    
    return None


def _google_books_cover(title: str, author: Optional[str]) -> Optional[str]:
    """Fetch cover from Google Books API with fallback to title-only search."""
    url = "https://www.googleapis.com/books/v1/volumes"
    
    # Try with author first if provided
    queries = []
    if author:
        queries.append(f"{title}+inauthor:{author}")
    queries.append(title)  # Always try title-only as fallback
    
    for query in queries:
        params = {"q": query, "maxResults": 1}
        try:
            resp = requests.get(url, params=params, timeout=10)
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        
        data = resp.json()
        items = data.get("items", [])
        if not items:
            continue
        
        volume_info = items[0].get("volumeInfo", {})
        image_links = volume_info.get("imageLinks", {})
        
        # Prefer larger image
        for size in ["extraLarge", "large", "medium", "thumbnail", "smallThumbnail"]:
            if size in image_links:
                cover_url = image_links[size]
                # Google Books uses http by default, upgrade to https
                if cover_url.startswith("http://"):
                    cover_url = cover_url.replace("http://", "https://", 1)
                return cover_url
    
    return None


def _openlibrary_cover(title: str, author: Optional[str]) -> Optional[str]:
    """Search by title (optional author), then derive cover via ISBN/OLID/cover_i."""
    query = {"title": title}
    if author:
        query["author"] = author
    try:
        resp = requests.get(
            "https://openlibrary.org/search.json",
            params=query,
            timeout=10,
        )
    except Exception:
        return None
    if resp.status_code != 200:
        return None

    data = resp.json()
    docs = data.get("docs", [])
    if not docs:
        return None

    # Pick the first doc; could be improved with scoring if needed
    doc = docs[0]

    # Prefer ISBN if available
    isbns = doc.get("isbn") or []
    if isbns:
        return f"https://covers.openlibrary.org/b/isbn/{isbns[0]}-L.jpg"

    # Next: edition_key (OLID for edition)
    editions = doc.get("edition_key") or []
    if editions:
        return f"https://covers.openlibrary.org/b/olid/{editions[0]}-L.jpg"

    # Fallback: cover_i id
    cover_id = doc.get("cover_i")
    if cover_id:
        return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

    return None


def fetch_cover_url(title: str, author: Optional[str]) -> Optional[str]:
    """Fetch cover with priority based on book language."""
    cache = _load_cache()
    key = f"{title}|{author or ''}"
    if key in cache:
        cached = cache[key]
        return cached or None

    cover_url = None
    is_chinese = _has_chinese(title) or (author and _has_chinese(author))
    
    if is_chinese:
        # Chinese books: Douban → Google Books → Open Library
        cover_url = _douban_cover(title, author)
        if not cover_url:
            cover_url = _google_books_cover(title, author)
        if not cover_url:
            cover_url = _openlibrary_cover(title, author)
    else:
        # Non-Chinese: Open Library → Google Books → Douban
        cover_url = _openlibrary_cover(title, author)
        if not cover_url:
            cover_url = _google_books_cover(title, author)
        if not cover_url:
            cover_url = _douban_cover(title, author)

    cache[key] = cover_url or ""
    _save_cache(cache)
    return cover_url


def _book_properties(
    title: str,
    author: Optional[str],
    cover_url: Optional[str],
    last_note_date: Optional[date],
) -> Dict:
    # Align with daily logic: use current import date for Last Import Time
    last_date = datetime.utcnow().date()
    props: Dict[str, Dict] = {
        "Name": title_text(title),
        "Source": {"select": {"name": "WeChat Read"}},
        "Last Import Time": {"date": {"start": last_date.isoformat()}},
    }
    if author:
        props["Author"] = rich_text(author)
    if cover_url is not None:
        props["CoverUrl"] = {"url": cover_url}
    if last_note_date:
        props["Annual Book List"] = {
            "rich_text": [
                {"type": "text", "text": {"content": str(last_note_date.year)}}
            ]
        }
    return props


def upsert_book(
    client: NotionClient,
    database_id: str,
    title: str,
    author: Optional[str],
    last_note_date: Optional[date],
    allow_cover_fetch: bool = True,
) -> Tuple[str, Optional[str]]:
    filter_payload = {
        "property": "Name",
        "title": {"equals": title},
    }
    query = client.query_database(database_id, filter=filter_payload)
    results = query.get("results", [])
    cover_url: Optional[str] = None

    if allow_cover_fetch:
        # Clean title for better search results (remove book marks)
        search_title = _clean_title_for_search(title)
        cover_url = fetch_cover_url(search_title, author)

    properties = _book_properties(title, author, cover_url, last_note_date)
    cover_payload = None
    if cover_url:
        cover_payload = {"type": "external", "external": {"url": cover_url}}

    if results:
        page_id = results[0]["id"]
        client.update_page(page_id, properties=properties, cover=cover_payload)
        return page_id, cover_url

    created = client.create_page(
        database_id,
        properties=properties,
        cover=cover_payload,
        icon={"type": "emoji", "emoji": "📖"},
    )
    return created["id"], cover_url
