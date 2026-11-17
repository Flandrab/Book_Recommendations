"""Build (or rebuild) the embedding index ahead of time.

Run from the backend/ folder:
    python -m scripts.build_index           # builds only if missing or out of date
    python -m scripts.build_index --force   # always rebuilds
"""

import argparse
import logging
import time

from app.config import get_settings
from app.data import load_books
from app.embeddings import SentenceTransformerEmbedder, build_index, load_or_build_index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="rebuild even if a valid index exists")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    start = time.time()

    books = load_books(settings.books_csv)
    print(f"Loaded {len(books)} books from {settings.books_csv}")
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    if args.force:
        embeddings = build_index(books, embedder, settings.index_dir, settings.embedding_model)
    else:
        embeddings = load_or_build_index(books, embedder, settings.index_dir, settings.embedding_model)

    print(f"Index ready: {embeddings.shape[0]} books x {embeddings.shape[1]} dims in {settings.index_dir}")
    print(f"Took {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
