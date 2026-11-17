"""Public ratings for a book from Google Books and Open Library, plus a Goodreads search link.

Goodreads stopped issuing API keys in December 2020, so we only link to it.
"""

import asyncio
import logging
import re
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
MAX_CACHE = 5000


def _norm(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _titles_match(wanted: str, found: str) -> bool:
    a, b = _norm(wanted), _norm(found)
    return bool(a and b) and (a == b or a.startswith(b) or b.startswith(a))


def parse_google(data: dict, title: str) -> dict | None:
    """Pick the first result with the same title that actually has ratings."""
    for item in data.get("items", []) or []:
        info = item.get("volumeInfo", {})
        if not _titles_match(title, info.get("title", "")):
            continue
        average = info.get("averageRating")
        count = info.get("ratingsCount")
        if average and count:
            return {
                "source": "Google Books",
                "average": round(float(average), 2),
                "count": int(count),
                "url": info.get("infoLink") or f"https://books.google.com/books?id={item.get('id', '')}",
            }
    return None


def parse_open_library(data: dict, title: str) -> dict | None:
    for doc in data.get("docs", []) or []:
        if not _titles_match(title, doc.get("title", "")):
            continue
        average = doc.get("ratings_average")
        count = doc.get("ratings_count")
        if average and count:
            return {
                "source": "Open Library",
                "average": round(float(average), 2),
                "count": int(count),
                "url": f"https://openlibrary.org{doc.get('key', '')}",
            }
    return None


def goodreads_search_url(title: str, authors: str) -> str:
    first_author = (authors or "").split(",")[0].strip()
    return f"https://www.goodreads.com/search?q={quote_plus(' '.join(filter(None, [title, first_author])))}"


class RatingsService:
    def __init__(self, client: httpx.AsyncClient, timeout: float, google_api_key: str, contact_email: str):
        self.client = client
        self.timeout = timeout
        self.google_api_key = google_api_key
        self.headers = {"User-Agent": f"BookTag/2.0 ({contact_email})"}
        self._cache: dict[str, dict] = {}

    async def _google(self, title: str, author: str) -> dict | None:
        query = f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else "")
        params = {
            "q": query,
            "maxResults": 5,
            "printType": "books",
            "fields": "items(id,volumeInfo(title,averageRating,ratingsCount,infoLink))",
        }
        if self.google_api_key:
            params["key"] = self.google_api_key
        try:
            response = await self.client.get(GOOGLE_BOOKS_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            return parse_google(response.json(), title)
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Google Books lookup failed for %r: %s", title, exc)
            return None

    async def _open_library(self, title: str, author: str) -> dict | None:
        params = {"title": title, "limit": 3, "fields": "key,title,ratings_average,ratings_count"}
        if author:
            params["author"] = author
        try:
            response = await self.client.get(
                OPEN_LIBRARY_SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            return parse_open_library(response.json(), title)
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Open Library ratings lookup failed for %r: %s", title, exc)
            return None

    async def ratings_for(self, title: str, authors: str) -> dict:
        key = f"{_norm(title)}|{_norm(authors)}"
        if key in self._cache:
            return self._cache[key]
        author = (authors or "").split(",")[0].strip()
        google, open_library = await asyncio.gather(self._google(title, author), self._open_library(title, author))
        result = {
            "google": google,
            "open_library": open_library,
            "goodreads_url": goodreads_search_url(title, authors),
        }
        
        if google or open_library:
            if len(self._cache) >= MAX_CACHE:
                self._cache.clear()
            self._cache[key] = result
        return result