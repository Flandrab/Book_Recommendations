"""API tests. Uses the fake recommender from conftest.py, with covers and the LLM switched off."""

import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client(recommender, tmp_path):
    os.environ["COVERS_ENABLED"] = "false"
    os.environ["LLM_ENABLED"] = "false"
    os.environ["RATINGS_ENABLED"] = "false"
    os.environ["FRONTEND_DIST"] = str(tmp_path / "no-frontend")
    os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
    try:
        settings = Settings()
    finally:
        for key in ("COVERS_ENABLED", "LLM_ENABLED", "RATINGS_ENABLED", "FRONTEND_DIST", "DATABASE_PATH"):
            os.environ.pop(key, None)
    with TestClient(create_app(settings=settings, recommender=recommender)) as test_client:
        yield test_client


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm_available"] is False


def test_options(client):
    body = client.get("/api/options").json()
    assert any(g["name"] == "Fantasy" for g in body["genres"])
    assert "Cozy" in body["moods"]


def test_search(client):
    body = client.get("/api/books/search", params={"q": "wicked"}).json()
    assert body[0]["title"] == "The Wicked King"


def test_book_detail_and_404(client):
    assert client.get("/api/books/0").json()["title"]
    assert client.get("/api/books/9999").status_code == 404


def test_recommend(client):
    response = client.post("/api/recommend", json={"liked_books": ["The Cruel Prince"], "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["reason"]


def test_recommend_empty_is_422(client):
    response = client.post("/api/recommend", json={})
    assert response.status_code == 422
    assert "Pick a genre" in response.json()["detail"]


def test_explain_without_llm(client):
    response = client.post("/api/explain", json={"book_ids": [0], "mood": "Cozy"})
    assert response.json() == {"reasons": {}, "source": "unavailable"}


def test_similar_endpoint(client):
    body = client.get("/api/books/0/similar", params={"limit": 2}).json()
    assert len(body) == 2
    assert all(book["id"] != 0 for book in body)


def test_ratings_endpoint_without_lookups(client):
    body = client.get("/api/books/0/ratings").json()
    assert body["google"] is None and body["open_library"] is None
    assert body["goodreads_url"].startswith("https://www.goodreads.com/search?q=")


def signup(client, email="reader@example.com"):
    return client.post("/api/auth/signup", json={"email": email, "name": "Reader", "password": "password123"})


def test_signup_sets_cookie_and_me_works(client):
    response = signup(client)
    assert response.status_code == 201
    assert "booktag_session" in response.cookies
    assert client.get("/api/auth/me").json()["email"] == "reader@example.com"


def test_signup_validation_and_duplicates(client):
    assert client.post("/api/auth/signup", json={"email": "bad", "name": "X", "password": "password123"}).status_code == 422
    assert client.post("/api/auth/signup", json={"email": "a@b.co", "name": "X", "password": "short"}).status_code == 422
    signup(client)
    assert signup(client).status_code == 409


def test_login_logout(client):
    signup(client)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "reader@example.com", "password": "nope"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "READER@example.com", "password": "password123"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_data_requires_login(client):
    assert client.get("/api/me/data").status_code == 401
    assert client.put("/api/me/goal", json={"goal": 5}).status_code == 401


def test_reading_data_round_trip(client):
    signup(client)
    book = {"id": 3, "title": "Some Book", "authors": "A", "year": 2001, "cover_url": None, "savedAt": 1}
    assert client.put("/api/me/reading-list/3", json=book).json()["id"] == 3
    assert client.put("/api/me/reading-list/4", json=book).status_code == 400

    log = {"id": "e1", "bookId": 3, "title": "Some Book", "finishedOn": "2026-10-01", "rating": 3}
    assert client.post("/api/me/reading-log", json=log).status_code == 201
    assert client.patch("/api/me/reading-log/e1", json={"rating": 5}).json()["rating"] == 5
    assert client.put("/api/me/goal", json={"goal": 20}).json() == {"goal": 20}

    data = client.get("/api/me/data").json()
    assert [b["id"] for b in data["readingList"]] == [3]
    assert data["readingLog"][0]["rating"] == 5
    assert data["goal"] == 20

    assert client.delete("/api/me/reading-log/e1").json() == {"ok": True}
    assert client.delete("/api/me/reading-log/e1").status_code == 404
    client.delete("/api/me/reading-list")
    assert client.get("/api/me/data").json()["readingList"] == []


def test_import_guest_data(client):
    signup(client)
    guest = {
        "readingList": [{"id": 1, "title": "Saved as guest", "authors": "", "year": None, "cover_url": None}],
        "readingLog": [{"id": "g1", "bookId": None, "title": "Typed title", "finishedOn": "2026-09-09"}],
        "goal": 10,
    }
    data = client.post("/api/me/import", json=guest).json()
    assert len(data["readingList"]) == 1 and len(data["readingLog"]) == 1 and data["goal"] == 10