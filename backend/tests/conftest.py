"""Shared test fixtures: a tiny dataset and a fake embedder, so tests run without torch or the real CSV."""

import re
import zlib

import numpy as np
import pandas as pd
import pytest

from app.data import clean_books
from app.recommender import Recommender

DIM = 512


class FakeEmbedder:
    """Bag-of-words hashing embedder: texts that share words get similar vectors."""

    def encode(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        vectors = np.zeros((len(texts), DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"[a-z]{3,}", text.lower()):
                vectors[row, zlib.crc32(word.encode()) % DIM] += 1.0
            norm = np.linalg.norm(vectors[row])
            if norm:
                vectors[row] /= norm
        return vectors


RAW_BOOKS = [
    ("The Cruel Prince", "By Black, Holly", "A mortal girl in the faerie court schemes against a cruel prince.", " Fiction , Fantasy , Young Adult"),
    ("The Wicked King", "By Black, Holly", "Faerie court intrigue continues as the mortal girl controls the wicked king.", " Fiction , Fantasy , Young Adult"),
    ("Court of Thorns", "By Writer, Anna", "A huntress is taken to a faerie court and falls for a cursed prince.", " Fiction , Fantasy , Romance"),
    ("Teverton Hall", "By Author, Some", "A heartwarming romance of love, family and hope in an english manor.", " Fiction , Romance , Historical"),
    ("Summer Letters", "By Author, Other", "A heartwarming love story told in letters, full of hope and kindness.", " Fiction , Romance , General"),
    ("Cold Case Files", "By Detective, Dan", "A detective hunts a murder suspect through a dark city full of crime.", " Fiction , Thrillers , Crime"),
    ("Silent Witness", "By Detective, Dan", "A murder trial and a detective racing against a killer.", " Fiction , Thrillers , Suspense"),
    ("Galaxy Run", "By Star, Sam", "Spaceships, alien empires and a pilot crossing the galaxy.", " Fiction , Science Fiction"),
    ("Cooking With Joy", "By Chef, Julia", "Simple recipes for family dinners.", " Cooking , General"),
    ("Teverton Hall", "By Author, Some", "Short duplicate edition.", " Fiction , Romance"),
]


@pytest.fixture
def books() -> pd.DataFrame:
    raw = pd.DataFrame(RAW_BOOKS, columns=["Title", "Authors", "Description", "Category"])
    raw["Publish Date (Year)"] = "2015"
    raw["Publisher"] = "Test House"
    return clean_books(raw)


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def recommender(books, embedder) -> Recommender:
    embeddings = embedder.encode(books["text"].tolist())
    return Recommender(books, embeddings, embedder)
