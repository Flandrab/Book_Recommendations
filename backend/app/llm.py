"""Personalised 'why you'll like it' explanations from a local LLM served by Ollama."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a warm, knowledgeable librarian. You explain in one or two sentences why a specific reader "
    "would enjoy a specific book. Use only the book information you are given; never invent plot details, "
    "awards or facts. Speak directly to the reader as 'you'. Keep each explanation under 45 words."
)


def build_prompt(profile: str, books: list[dict]) -> str:
    book_blocks = []
    for book in books:
        description = (book.get("description") or "No description available.")[:700]
        genres = ", ".join(book.get("genres") or []) or "unknown"
        authors = book.get("authors") or "unknown author"
        book_blocks.append(f"[id={book['id']}] {book['title']} by {authors}\nGenres: {genres}\n{description}")
    return (
        f"The reader:\n{profile}\n\n"
        "Books recommended to them:\n\n" + "\n\n".join(book_blocks) + "\n\n"
        'Reply with JSON only, in this exact shape: {"reasons": [{"id": <book id>, "reason": "<explanation>"}]} '
        "with one entry per book."
    )


def parse_reasons(content: str, valid_ids: set[int]) -> dict[int, str]:
    """Pull {id: reason} out of the model's JSON reply, ignoring anything malformed."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    items = data.get("reasons", []) if isinstance(data, dict) else data
    reasons: dict[int, str] = {}
    if not isinstance(items, list):
        return reasons
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            book_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        reason = str(item.get("reason", "")).strip()
        if book_id in valid_ids and reason:
            reasons[book_id] = reason
    return reasons


class OllamaExplainer:
    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str, timeout: float):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def is_available(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=3)
            response.raise_for_status()
            names = {m.get("name", "") for m in response.json().get("models", [])}
            return self.model in names or f"{self.model}:latest" in names
        except (httpx.HTTPError, ValueError):
            return False

    async def explain(self, profile: str, books: list[dict]) -> dict[int, str]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(profile, books)},
            ],
        }
        try:
            response = await self.client.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama request failed: %s", exc)
            return {}
        return parse_reasons(content, {int(b["id"]) for b in books})
