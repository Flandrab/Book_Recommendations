from app.data import clean_authors, normalize_title, split_genres


def test_clean_authors_flips_last_first():
    assert clean_authors("By Goldsmith, Olivia") == "Olivia Goldsmith"
    assert clean_authors("By Smith, John and Doe, Jane") == "John Smith, Jane Doe"
    assert clean_authors("") == ""


def test_split_genres_drops_general_and_duplicates():
    assert split_genres(" Fiction , Romance , General , fiction") == ["Fiction", "Romance"]


def test_normalize_title():
    assert normalize_title("  The Cruel-Prince!! ") == "the cruel prince"


def test_clean_books_dedupes_and_adds_columns(books):
    assert list(books["book_id"]) == list(range(len(books)))
    # the two "Teverton Hall" rows are merged, keeping the longer description
    teverton = books[books["title"] == "Teverton Hall"]
    assert len(teverton) == 1
    assert "heartwarming" in teverton.iloc[0]["description"]
    assert books.iloc[0]["authors"] == "Holly Black"
    assert books.iloc[0]["year"] == 2015
    assert "Genres:" in books.iloc[0]["text"]
