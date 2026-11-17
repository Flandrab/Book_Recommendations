"""Book cover lookups via the free Open Library API, cached on disk."""

import asyncio
import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SEARCH_URL = "https://openlibrary.org/search.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


class CoverService:
    def __init__(self, client: httpx.AsyncClient, cache_file: Path, timeout: float, contact_email: str):
        self.client = client
        self.cache_file = cache_file
        self.timeout = timeout
        self.headers = {"User-Agent": f"BookRecommendations/2.0 ({contact_email})"}
        self._cache: dict[str, str | None] = self._load_cache()
        self._dirty = False

    def _load_cache(self) -> dict[str, str | None]:
        try:
            return json.loads(self.cache_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_cache(self) -> None:
        if not self._dirty:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._cache))
            self._dirty = False
        except OSError as exc:
            logger.warning("Could not save cover cache: %s", exc)

    @staticmethod
    def _key(title: str, authors: str) -> str:
        return f"{title.lower().strip()}|{authors.lower().strip()}"

    async def _lookup(self, title: str, authors: str) -> str | None:
        params = {"title": title, "limit": 1, "fields": "cover_i"}
        first_author = authors.split(",")[0].strip()
        if first_author:
            params["author"] = first_author
        response = await self.client.get(SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        docs = response.json().get("docs", [])
        if docs and docs[0].get("cover_i"):
            return COVER_URL.format(cover_id=docs[0]["cover_i"])
        return None

    async def cover_for(self, title: str, authors: str) -> str | None:
        key = self._key(title, authors)
        if key in self._cache:
            return self._cache[key]
        try:
            url = await self._lookup(title, authors)
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Cover lookup failed for %r: %s", title, exc)
            return None  # don't cache failures, try again next time
        self._cache[key] = url
        self._dirty = True
        return url

    async def add_covers(self, books: list[dict]) -> None:
        """Set book['cover_url'] on every book, in parallel."""
        urls = await asyncio.gather(*(self.cover_for(b["title"], b.get("authors", "")) for b in books))
        for book, url in zip(books, urls):
            book["cover_url"] = url
        self.save_cache()
