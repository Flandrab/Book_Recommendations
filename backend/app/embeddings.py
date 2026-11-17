"""Sentence embeddings for books and queries, plus an on-disk index cache."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EMBEDDINGS_FILE = "embeddings.npy"
META_FILE = "meta.json"


class Embedder(Protocol):
    """Anything that turns a list of texts into L2-normalised vectors."""

    def encode(self, texts: list[str], show_progress: bool = False) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        # Imported here so the rest of the app (and the tests) don't need torch installed.
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s", model_name)
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
        )
        return vectors.astype(np.float32)


def dataset_fingerprint(df: pd.DataFrame, model_name: str) -> str:
    """Changes whenever the books or the model change, so a stale index gets rebuilt."""
    digest = hashlib.sha256()
    digest.update(model_name.encode())
    for text in df["text"]:
        digest.update(text.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_index(df: pd.DataFrame, embedder: Embedder, index_dir: Path, model_name: str) -> np.ndarray:
    logger.info("Embedding %d books (this runs once and is then cached)...", len(df))
    embeddings = embedder.encode(df["text"].tolist(), show_progress=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    np.save(index_dir / EMBEDDINGS_FILE, embeddings)
    meta = {
        "model": model_name,
        "num_books": len(df),
        "dim": int(embeddings.shape[1]),
        "fingerprint": dataset_fingerprint(df, model_name),
    }
    (index_dir / META_FILE).write_text(json.dumps(meta, indent=2))
    logger.info("Saved index to %s", index_dir)
    return embeddings


def load_or_build_index(df: pd.DataFrame, embedder: Embedder, index_dir: Path, model_name: str) -> np.ndarray:
    emb_path = index_dir / EMBEDDINGS_FILE
    meta_path = index_dir / META_FILE
    if emb_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("fingerprint") == dataset_fingerprint(df, model_name):
            embeddings = np.load(emb_path)
            if embeddings.shape[0] == len(df):
                logger.info("Loaded cached index (%d books)", len(df))
                return embeddings
        logger.info("Cached index is out of date, rebuilding")
    return build_index(df, embedder, index_dir, model_name)
