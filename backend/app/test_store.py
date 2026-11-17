import pytest

from app.auth import LoginThrottle, hash_password, verify_password
from app.db import Database
from app.store import EmailTakenError, UserStore


@pytest.fixture
def store(tmp_path):
    db = Database(tmp_path / "test.db")
    yield UserStore(db)
    db.close()


def entry(**overrides):
    base = {"bookId": 1, "title": "The Cruel Prince", "authors": "Holly Black", "finishedOn": "2026-11-01"}
    return {**base, **overrides}


def test_password_hashing():
    stored = hash_password("correct horse")
    assert stored.startswith("scrypt$")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("anything", "garbage")


def test_signup_login_and_sessions(store):
    user = store.create_user("  Flandra@Example.com ", "Flandra", "secret123")
    assert user["email"] == "flandra@example.com"
    with pytest.raises(EmailTakenError):
        store.create_user("flandra@example.com", "Someone", "another123")

    assert store.authenticate("FLANDRA@example.com", "secret123")["id"] == user["id"]
    assert store.authenticate("flandra@example.com", "wrong") is None
    assert store.authenticate("nobody@example.com", "secret123") is None

    token = store.create_session(user["id"])
    assert store.user_for_token(token)["name"] == "Flandra"
    store.delete_session(token)
    assert store.user_for_token(token) is None


def test_reading_list(store):
    uid = store.create_user("a@example.com", "A", "password1")["id"]
    store.save_to_list(uid, {"id": 5, "title": "Book Five", "authors": "X", "year": 2001, "savedAt": 1000})
    store.save_to_list(uid, {"id": 6, "title": "Book Six", "savedAt": 2000})
    # newest first
    assert [b["id"] for b in store.get_data(uid)["readingList"]] == [6, 5]
    store.remove_from_list(uid, 5)
    assert [b["id"] for b in store.get_data(uid)["readingList"]] == [6]
    store.clear_list(uid)
    assert store.get_data(uid)["readingList"] == []


def test_reading_log_and_goal(store):
    uid = store.create_user("b@example.com", "B", "password1")["id"]
    added = store.add_log_entry(uid, entry(id="entry-1", rating=4))
    assert added == {
        "id": "entry-1",
        "bookId": 1,
        "title": "The Cruel Prince",
        "authors": "Holly Black",
        "year": None,
        "cover_url": None,
        "finishedOn": "2026-11-01",
        "rating": 4,
        "notes": "",
    }
    updated = store.update_log_entry(uid, "entry-1", {"rating": 5, "notes": "Loved it", "ignored": "x"})
    assert updated["rating"] == 5 and updated["notes"] == "Loved it"
    assert store.update_log_entry(uid, "missing", {"rating": 1}) is None

    assert store.set_goal(uid, 24) == 24
    assert store.get_data(uid)["goal"] == 24
    assert store.remove_log_entry(uid, "entry-1") is True
    assert store.remove_log_entry(uid, "entry-1") is False


def test_users_cannot_touch_each_others_data(store):
    alice = store.create_user("alice@example.com", "Alice", "password1")["id"]
    bob = store.create_user("bob@example.com", "Bob", "password1")["id"]
    store.add_log_entry(alice, entry(id="shared-id"))
    # Bob reuses the same id: it is stored under a new id instead of clashing
    bob_entry = store.add_log_entry(bob, entry(id="shared-id"))
    assert bob_entry["id"] != "shared-id"
    assert store.update_log_entry(bob, "shared-id", {"rating": 1}) is None
    assert store.remove_log_entry(bob, "shared-id") is False
    assert len(store.get_data(alice)["readingLog"]) == 1


def test_import_merges_without_duplicates(store):
    uid = store.create_user("c@example.com", "C", "password1")["id"]
    store.save_to_list(uid, {"id": 1, "title": "Already saved"})
    guest = {
        "readingList": [{"id": 1, "title": "Already saved"}, {"id": 2, "title": "New one"}],
        "readingLog": [entry(id="g1"), entry(id="g2")],  # same book and date twice
        "goal": 12,
    }
    data = store.import_data(uid, guest)
    assert sorted(b["id"] for b in data["readingList"]) == [1, 2]
    assert len(data["readingLog"]) == 1
    assert data["goal"] == 12
    # importing again changes nothing
    again = store.import_data(uid, guest)
    assert len(again["readingLog"]) == 1 and len(again["readingList"]) == 2


def test_login_throttle():
    throttle = LoginThrottle(max_failures=3, window_seconds=60)
    for _ in range(3):
        assert not throttle.is_blocked("x@example.com")
        throttle.record_failure("x@example.com")
    assert throttle.is_blocked("x@example.com")
    throttle.reset("x@example.com")
    assert not throttle.is_blocked("x@example.com")