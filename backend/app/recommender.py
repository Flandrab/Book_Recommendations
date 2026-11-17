"""Semantic book recommender.

How it works:
1. Every book (title + authors + genres + description) is turned into an embedding vector once.
2. A request is turned into one "taste" vector: a weighted mix of the books the user liked,
   their own description, the mood and the genres.
3. Books are ranked by cosine similarity to that taste vector, the selected genres are respected,
   and Maximal Marginal Relevance (MMR) keeps the final list from being five near-identical books.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import normalize_title
from .embeddings import Embedder

MOODS: dict[str, str] = {
    "Heartwarming": "a heartwarming, uplifting, feel-good story full of kindness, love, family and hope",
    "Cozy": "a cozy, comforting, gentle and charming read with a warm small-town feel",
    "Funny": "a funny, witty, lighthearted and humorous book that makes you laugh",
    "Romantic": "a romantic, passionate love story with chemistry and longing",
    "Adventurous": "an adventurous epic journey full of exploration, quests and action",
    "Thrilling": "a fast-paced, suspenseful, gripping thriller full of tension, danger and twists",
    "Mysterious": "a mysterious, atmospheric story full of secrets, clues and puzzles to solve",
    "Dark": "a dark, gritty, intense and haunting story about the darker side of people",
    "Scary": "a scary, creepy, terrifying horror story",
    "Melancholic": "a melancholic, bittersweet, emotional and moving story about loss and memory",
    "Inspiring": "an inspiring, motivational true story of courage, growth and triumph",
    "Thought-provoking": "a thought-provoking, philosophical, intelligent book that challenges how you see the world",
}


WEIGHT_LIKED = 1.0
WEIGHT_LIKED_UNMATCHED = 0.5
WEIGHT_DESCRIPTION = 1.0
WEIGHT_MOOD = 0.6
WEIGHT_GENRES = 0.4

GENRE_BOOST = 0.1 
CANDIDATE_POOL = 100
MMR_LAMBDA = 0.75  


class EmptyQueryError(ValueError):
    pass


@dataclass
class LikedBook:
    query: str
    book_id: int | None = None


@dataclass
class RecommendationQuery:
    genres: list[str] = field(default_factory=list)
    mood: str | None = None
    liked_books: list[str] = field(default_factory=list)
    description: str = ""
    limit: int = 5
    exclude_ids: list[int] = field(default_factory=list)


class Recommender:
    def __init__(self, books: pd.DataFrame, embeddings: np.ndarray, embedder: Embedder):
        if len(books) != embeddings.shape[0]:
            raise ValueError("books and embeddings must have the same number of rows")
        self.books = books
        self.embeddings = embeddings
        self.embedder = embedder
        self._genres_joined = books["genres"].map(lambda g: " | ".join(x.lower() for x in g))
        self._title_to_ids: dict[str, list[int]] = {}
        for book_id, norm in zip(books["book_id"], books["norm_title"]):
            self._title_to_ids.setdefault(norm, []).append(int(book_id))
        mood_vectors = embedder.encode(list(MOODS.values()))
        self._mood_vectors = {name.lower(): vec for name, vec in zip(MOODS, mood_vectors)}
        self._mood_names = {name.lower(): name for name in MOODS}
        self._text_cache: dict[str, np.ndarray] = {}


    def top_genres(self, limit: int = 40) -> list[dict]:
        counts = Counter(g for genres in self.books["genres"] for g in genres)
        return [{"name": name, "count": count} for name, count in counts.most_common(limit)]

    @staticmethod
    def moods() -> list[str]:
        return list(MOODS)

    def search_titles(self, query: str, limit: int = 8) -> list[dict]:
        norm = normalize_title(query)
        if len(norm) < 2:
            return []
        titles = self.books["norm_title"]
        starts = titles.str.startswith(norm)
        contains = titles.str.contains(norm, regex=False) & ~starts
        prefix = self.books[starts]
        inner = self.books[contains]
        prefix = prefix.iloc[np.argsort(prefix["title"].str.len().to_numpy(), kind="stable")]
        inner = inner.iloc[np.argsort(inner["title"].str.len().to_numpy(), kind="stable")]
        hits = pd.concat([prefix, inner])
        return [self.book_summary(int(i)) for i in hits["book_id"].head(limit)]

    def book_summary(self, book_id: int) -> dict:
        row = self.books.iloc[book_id]
        return {
            "id": int(row["book_id"]),
            "title": row["title"],
            "authors": row["authors"],
            "year": None if pd.isna(row["year"]) else int(row["year"]),
        }

    def book_details(self, book_id: int) -> dict:
        row = self.books.iloc[book_id]
        details = self.book_summary(book_id)
        details.update(
            {
                "description": row["description"],
                "genres": list(row["genres"]),
                "publisher": row["publisher"],
            }
        )
        return details

    def resolve_liked(self, titles: list[str]) -> list[LikedBook]:
        """Match the titles the user typed to books in the dataset."""
        resolved = []
        for title in titles:
            title = title.strip()
            if not title:
                continue
            norm = normalize_title(title)
            ids = self._title_to_ids.get(norm)
            if not ids:
                matches = self.search_titles(title, limit=1)
                if matches and normalize_title(matches[0]["title"]).startswith(norm) and len(norm) >= 4:
                    ids = [matches[0]["id"]]
            resolved.append(LikedBook(query=title, book_id=ids[0] if ids else None))
        return resolved


    def _embed(self, text: str) -> np.ndarray:
        if text not in self._text_cache:
            if len(self._text_cache) > 2000:
                self._text_cache.clear()
            self._text_cache[text] = self.embedder.encode([text])[0]
        return self._text_cache[text]

    def _genre_mask(self, genres: list[str]) -> np.ndarray:
        mask = np.zeros(len(self.books), dtype=bool)
        for genre in genres:
            pattern = r"(?:^|\| )" + re.escape(genre.lower().strip())
            mask |= self._genres_joined.str.contains(pattern, regex=True).to_numpy()
        return mask

    def _components(self, query: RecommendationQuery, liked: list[LikedBook]) -> dict[str, tuple[np.ndarray, float]]:
        """Each part of the request as (unit vector, weight)."""
        components: dict[str, tuple[np.ndarray, float]] = {}

        matched_ids = [b.book_id for b in liked if b.book_id is not None]
        if matched_ids:
            components["liked"] = (_unit(self.embeddings[matched_ids].mean(axis=0)), WEIGHT_LIKED)
        unmatched = [b.query for b in liked if b.book_id is None]
        if unmatched:
            text = "A book similar to " + ", ".join(unmatched)
            components["liked_text"] = (self._embed(text), WEIGHT_LIKED_UNMATCHED)

        if query.description.strip():
            components["description"] = (self._embed(query.description.strip()), WEIGHT_DESCRIPTION)

        mood_key = (query.mood or "").strip().lower()
        if mood_key in self._mood_vectors:
            components["mood"] = (self._mood_vectors[mood_key], WEIGHT_MOOD)
        elif mood_key:
            components["mood"] = (self._embed(f"a {mood_key} book"), WEIGHT_MOOD)

        if query.genres:
            components["genres"] = (self._embed("Genres: " + ", ".join(query.genres)), WEIGHT_GENRES)
        return components

    def recommend(self, query: RecommendationQuery) -> dict:
        liked = self.resolve_liked(query.liked_books)
        components = self._components(query, liked)
        if not components:
            raise EmptyQueryError("Pick a genre or mood, add a book you liked, or describe what you want to read.")

        taste = _unit(sum(vec * weight for vec, weight in components.values()))
        scores = self.embeddings @ taste

        allowed = np.ones(len(self.books), dtype=bool)
        liked_ids = [b.book_id for b in liked if b.book_id is not None]
        for book_id in liked_ids:
            same_title = self._title_to_ids.get(self.books.iloc[book_id]["norm_title"], [])
            allowed[same_title] = False
        valid_excludes = [i for i in query.exclude_ids if 0 <= i < len(self.books)]
        allowed[valid_excludes] = False

        if query.genres:
            genre_mask = self._genre_mask(query.genres)
            if (genre_mask & allowed).sum() >= query.limit:
                allowed &= genre_mask
            else:
                scores = scores + GENRE_BOOST * genre_mask

        scores = np.where(allowed, scores, -np.inf)
        picks = self._mmr(scores, query.limit)

        selected_genres = {g.lower() for g in query.genres}
        liked_titles = [self.books.iloc[i]["title"] for i in liked_ids] or [b.query for b in liked]
        results = []
        for book_id in picks:
            details = self.book_details(book_id)
            details["score"] = round(float(scores[book_id]), 4)
            details["matched_genres"] = [g for g in details["genres"] if g.lower() in selected_genres]
            details["reason"] = self._reason(book_id, components, details["matched_genres"], query, liked_titles)
            results.append(details)

        return {
            "results": results,
            "liked": [
                {"query": b.query, "match": self.book_summary(b.book_id) if b.book_id is not None else None}
                for b in liked
            ],
        }

    def similar(self, book_id: int, limit: int = 6) -> list[dict]:
        """Books closest in meaning to one book (other editions of the same title are skipped)."""
        scores = self.embeddings @ self.embeddings[book_id]
        same_title = self._title_to_ids.get(self.books.iloc[book_id]["norm_title"], [book_id])
        scores = scores.astype(np.float64)
        scores[same_title] = -np.inf
        results = []
        for other_id in self._mmr(scores, limit):
            details = self.book_details(other_id)
            details["score"] = round(float(scores[other_id]), 4)
            results.append(details)
        return results

    def _mmr(self, scores: np.ndarray, limit: int) -> list[int]:
        finite = np.isfinite(scores)
        if not finite.any():
            return []
        pool_size = min(CANDIDATE_POOL, int(finite.sum()))
        pool = np.argpartition(-np.where(finite, scores, -1e9), pool_size - 1)[:pool_size]
        pool = pool[np.argsort(-scores[pool])]

        selected: list[int] = []
        seen_titles: set[str] = set()
        candidates = list(pool)
        while candidates and len(selected) < limit:
            if selected:
                sims = self.embeddings[candidates] @ self.embeddings[selected].T
                penalty = sims.max(axis=1)
            else:
                penalty = np.zeros(len(candidates))
            mmr = MMR_LAMBDA * scores[candidates] - (1 - MMR_LAMBDA) * penalty
            best_pos = int(np.argmax(mmr))
            best = int(candidates.pop(best_pos))
            norm = self.books.iloc[best]["norm_title"]
            if norm in seen_titles:
                continue
            seen_titles.add(norm)
            selected.append(best)
        return selected

    def _reason(
        self,
        book_id: int,
        components: dict[str, tuple[np.ndarray, float]],
        matched_genres: list[str],
        query: RecommendationQuery,
        liked_titles: list[str],
    ) -> str:
        """A short, honest explanation built from which part of the request the book matched best."""
        vector = self.embeddings[book_id]
        similarity = {name: float(vector @ vec) for name, (vec, _) in components.items() if name != "genres"}
        phrases = {
            "liked": f"Close in theme and style to {_join(liked_titles)}",
            "liked_text": f"Shares themes with {_join(liked_titles)}",
            "description": "Lines up closely with what you described",
            "mood": f"Its story fits the {self._mood_names.get((query.mood or '').lower(), query.mood or '').lower()} mood you asked for",
        }
        parts = []
        if similarity:
            strongest = max(similarity, key=similarity.get)
            parts.append(phrases[strongest])
        if matched_genres:
            parts.append(f"{_join(matched_genres)} pick")
        elif query.genres:
            parts.append(f"Related to {_join(query.genres)}")
        return ". ".join(parts) + "." if parts else "A strong overall match for your request."

    def taste_profile(self, query: RecommendationQuery) -> str:
        """Plain-language summary of the request, used in the LLM prompt."""
        lines = []
        if query.genres:
            lines.append("Favourite genres: " + ", ".join(query.genres))
        if query.mood:
            lines.append("Mood they're in: " + query.mood)
        liked = self.resolve_liked(query.liked_books)
        if liked:
            names = []
            for book in liked:
                if book.book_id is not None:
                    summary = self.book_summary(book.book_id)
                    names.append(f"{summary['title']}" + (f" by {summary['authors']}" if summary["authors"] else ""))
                else:
                    names.append(book.query)
            lines.append("Books they loved: " + "; ".join(names))
        if query.description.strip():
            lines.append("In their own words: " + query.description.strip())
        return "\n".join(lines)


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]