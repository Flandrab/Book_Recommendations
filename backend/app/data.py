"""Loading and cleaning the books dataset."""

import re
from pathlib import Path

import pandas as pd

# Maps lower-cased CSV column names to the names used inside the app.
COLUMN_ALIASES = {
    "title": "title",
    "authors": "authors",
    "author": "authors",
    "description": "description",
    "category": "category",
    "categories": "category",
    "genre": "category",
    "genres": "category",
    "publisher": "publisher",
    "publish date (year)": "year",
    "year": "year",
    "published_year": "year",
}

# Genre labels that carry no useful information on their own.
IGNORED_GENRES = {"general", ""}

MAX_TEXT_CHARS = 1200


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path} as UTF-8 or Latin-1")


def normalize_title(title: str) -> str:
    """Lower-case and strip punctuation so titles can be compared loosely."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def clean_authors(raw: str) -> str:
    """Turn 'By Goldsmith, Olivia and Smith, John' into 'Olivia Goldsmith, John Smith'."""
    raw = raw.strip()
    raw = re.sub(r"^by\s+", "", raw, flags=re.IGNORECASE)
    if not raw:
        return ""
    names = []
    for part in re.split(r"\s+and\s+|;|&", raw):
        part = part.strip(" ,")
        if not part:
            continue
        pieces = [p.strip() for p in part.split(",")]
        if len(pieces) == 2 and all(pieces):
            part = f"{pieces[1]} {pieces[0]}"
        names.append(part)
    return ", ".join(names)


def split_genres(raw: str) -> list[str]:
    """Turn ' Fiction , Romance , General' into ['Fiction', 'Romance']."""
    genres: list[str] = []
    seen: set[str] = set()
    for piece in re.split(r"[,/|]", raw):
        genre = piece.strip()
        key = genre.lower()
        if key in IGNORED_GENRES or key in seen:
            continue
        seen.add(key)
        genres.append(genre.title() if genre.isupper() or genre.islower() else genre)
    return genres


def _build_text(row: pd.Series) -> str:
    """The text that gets embedded for each book."""
    parts = [row["title"]]
    if row["authors"]:
        parts.append(f"by {row['authors']}")
    if row["genres"]:
        parts.append("Genres: " + ", ".join(row["genres"]))
    if row["description"]:
        parts.append(row["description"])
    return ". ".join(parts)[:MAX_TEXT_CHARS]


def clean_books(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, clean values, drop duplicates and add helper columns."""
    df = df.rename(columns={c: COLUMN_ALIASES.get(c.strip().lower(), c) for c in df.columns})
    if "title" not in df.columns:
        raise ValueError("The dataset needs a 'Title' column")

    for column in ("title", "authors", "description", "category", "publisher", "year"):
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].fillna("").astype(str).str.strip()

    df = df[df["title"] != ""].copy()
    df["authors"] = df["authors"].map(clean_authors)
    df["genres"] = df["category"].map(split_genres)
    df["year"] = pd.to_numeric(df["year"].str.extract(r"(\d{4})", expand=False), errors="coerce")
    df["norm_title"] = df["title"].map(normalize_title)

    # Same book listed more than once (different editions) - keep the one with the longest description.
    df["_desc_len"] = df["description"].str.len()
    df = df.sort_values("_desc_len", ascending=False)
    df = df.drop_duplicates(subset=["norm_title", "authors"], keep="first")
    df = df.drop(columns=["_desc_len"]).sort_index()

    df = df.reset_index(drop=True)
    df["book_id"] = df.index.astype(int)
    df["text"] = df.apply(_build_text, axis=1)
    return df[["book_id", "title", "authors", "description", "genres", "publisher", "year", "norm_title", "text"]]


def load_books(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Put BooksDataset.csv in backend/data/ or set BOOKS_CSV."
        )
    return clean_books(_read_csv(path))
