import pytest

pytest.importorskip("httpx")

from app.ratings import goodreads_search_url, parse_google, parse_open_library  # noqa: E402


def test_parse_google_picks_matching_title_with_ratings():
    data = {
        "items": [
            {"id": "a", "volumeInfo": {"title": "Something Else", "averageRating": 5, "ratingsCount": 9}},
            {"id": "b", "volumeInfo": {"title": "The Cruel Prince", "averageRating": 4.1, "ratingsCount": 230}},
        ]
    }
    result = parse_google(data, "The Cruel Prince")
    assert result["average"] == 4.1 and result["count"] == 230
    assert result["url"].endswith("id=b")


def test_parse_google_without_ratings():
    assert parse_google({"items": [{"volumeInfo": {"title": "The Cruel Prince"}}]}, "The Cruel Prince") is None
    assert parse_google({}, "Anything") is None


def test_parse_open_library():
    data = {"docs": [{"key": "/works/OL1W", "title": "The Cruel Prince", "ratings_average": 4.0, "ratings_count": 50}]}
    result = parse_open_library(data, "the cruel prince")
    assert result == {
        "source": "Open Library",
        "average": 4.0,
        "count": 50,
        "url": "https://openlibrary.org/works/OL1W",
    }


def test_goodreads_search_url():
    assert goodreads_search_url("The Cruel Prince", "Holly Black, Someone") == (
        "https://www.goodreads.com/search?q=The+Cruel+Prince+Holly+Black"
    )