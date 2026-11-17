import pytest

from app.recommender import EmptyQueryError, RecommendationQuery


def titles(result):
    return [book["title"] for book in result["results"]]


def test_empty_query_raises(recommender):
    with pytest.raises(EmptyQueryError):
        recommender.recommend(RecommendationQuery())


def test_liked_book_is_resolved_and_excluded(recommender):
    result = recommender.recommend(RecommendationQuery(liked_books=["the cruel prince"], limit=3))
    assert result["liked"][0]["match"]["title"] == "The Cruel Prince"
    assert "The Cruel Prince" not in titles(result)
    # the closest book is the sequel set in the same faerie court
    assert titles(result)[0] == "The Wicked King"


def test_unknown_liked_book_still_works(recommender):
    result = recommender.recommend(RecommendationQuery(liked_books=["A book that does not exist"], limit=2))
    assert result["liked"][0]["match"] is None
    assert len(result["results"]) == 2


def test_genres_are_respected(recommender):
    result = recommender.recommend(RecommendationQuery(genres=["Thrillers"], limit=2))
    assert set(titles(result)) == {"Cold Case Files", "Silent Witness"}
    assert all(book["matched_genres"] == ["Thrillers"] for book in result["results"])


def test_genre_falls_back_to_boost_when_too_few_matches(recommender):
    result = recommender.recommend(RecommendationQuery(genres=["Science Fiction"], limit=3))
    assert titles(result)[0] == "Galaxy Run"
    assert len(result["results"]) == 3


def test_mood_and_description_steer_results(recommender):
    result = recommender.recommend(
        RecommendationQuery(mood="Heartwarming", description="a love story full of hope", limit=2)
    )
    assert set(titles(result)) == {"Teverton Hall", "Summer Letters"}


def test_exclude_ids_and_no_duplicates(recommender, books):
    first = recommender.recommend(RecommendationQuery(genres=["Romance"], limit=2))
    seen = [b["id"] for b in first["results"]]
    second = recommender.recommend(RecommendationQuery(genres=["Romance"], limit=2, exclude_ids=seen))
    assert not set(seen) & {b["id"] for b in second["results"]}
    assert len(titles(second)) == len(set(titles(second)))


def test_reason_mentions_liked_book(recommender):
    result = recommender.recommend(RecommendationQuery(liked_books=["The Cruel Prince"], genres=["Fantasy"], limit=1))
    reason = result["results"][0]["reason"]
    assert "The Cruel Prince" in reason
    assert "Fantasy" in reason


def test_search_titles_prefix_first(recommender):
    hits = recommender.search_titles("the")
    assert hits[0]["title"] in {"The Cruel Prince", "The Wicked King"}
    assert recommender.search_titles("x") == []


def test_top_genres_and_moods(recommender):
    genres = {g["name"]: g["count"] for g in recommender.top_genres()}
    assert genres["Fiction"] == 8
    assert "General" not in genres
    assert "Heartwarming" in recommender.moods()


def test_taste_profile(recommender):
    profile = recommender.taste_profile(
        RecommendationQuery(genres=["Fantasy"], mood="Dark", liked_books=["The Cruel Prince"], description="faeries")
    )
    assert "Fantasy" in profile and "Dark" in profile
    assert "The Cruel Prince by Holly Black" in profile
    assert "faeries" in profile


def test_similar_books(recommender, books):
    cruel = int(books[books["title"] == "The Cruel Prince"]["book_id"].iloc[0])
    similar = recommender.similar(cruel, limit=2)
    titles = [b["title"] for b in similar]
    assert "The Cruel Prince" not in titles
    assert titles[0] == "The Wicked King"
    assert len(titles) == 2