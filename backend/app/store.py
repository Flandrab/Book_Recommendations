"""Everything the app saves per user: accounts, sessions, reading list, reading log and yearly goal."""

import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

from .auth import DUMMY_HASH, SESSION_DAYS, hash_password, hash_token, new_session_token, verify_password
from .db import Database


class EmailTakenError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _user(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def _list_item(row: sqlite3.Row) -> dict:
    return {
        "id": row["book_id"],
        "title": row["title"],
        "authors": row["authors"],
        "year": row["year"],
        "cover_url": row["cover_url"],
        "savedAt": row["saved_at"],
    }


def _log_entry(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "bookId": row["book_id"],
        "title": row["title"],
        "authors": row["authors"],
        "year": row["year"],
        "cover_url": row["cover_url"],
        "finishedOn": row["finished_on"],
        "rating": row["rating"],
        "notes": row["notes"],
    }


class UserStore:
    def __init__(self, db: Database):
        self.db = db

    # ----- accounts and sessions -----------------------------------------------------------

    def create_user(self, email: str, name: str, password: str) -> dict:
        email = email.strip().lower()
        try:
            cursor = self.db.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                (email, name.strip(), hash_password(password)),
            )
        except sqlite3.IntegrityError as exc:
            raise EmailTakenError("An account with this email already exists.") from exc
        return {"id": cursor.lastrowid, "email": email, "name": name.strip()}

    def authenticate(self, email: str, password: str) -> dict | None:
        rows = self.db.query("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
        if not rows:
            verify_password(password, DUMMY_HASH)  # same timing whether or not the email exists
            return None
        row = rows[0]
        return _user(row) if verify_password(password, row["password_hash"]) else None

    def create_session(self, user_id: int) -> str:
        token = new_session_token()
        expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hash_token(token), user_id, expires),
        )
        return token

    def user_for_token(self, token: str) -> dict | None:
        rows = self.db.query(
            "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (hash_token(token), _now_iso()),
        )
        return _user(rows[0]) if rows else None

    def delete_session(self, token: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))

    def delete_expired_sessions(self) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now_iso(),))

    # ----- reading data ----------------------------------------------------------------------

    def get_data(self, user_id: int) -> dict:
        reading_list = self.db.query(
            "SELECT * FROM reading_list WHERE user_id = ? ORDER BY saved_at DESC", (user_id,)
        )
        reading_log = self.db.query(
            "SELECT * FROM reading_log WHERE user_id = ? ORDER BY finished_on DESC, rowid DESC", (user_id,)
        )
        return {
            "readingList": [_list_item(r) for r in reading_list],
            "readingLog": [_log_entry(r) for r in reading_log],
            "goal": self.get_goal(user_id),
        }

    def save_to_list(self, user_id: int, book: dict) -> dict:
        saved_at = int(book.get("savedAt") or time.time() * 1000)
        self.db.execute(
            "INSERT INTO reading_list (user_id, book_id, title, authors, year, cover_url, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, book_id) DO UPDATE SET title = excluded.title, authors = excluded.authors, "
            "year = excluded.year, cover_url = excluded.cover_url",
            (user_id, book["id"], book["title"], book.get("authors") or "", book.get("year"), book.get("cover_url"), saved_at),
        )
        rows = self.db.query("SELECT * FROM reading_list WHERE user_id = ? AND book_id = ?", (user_id, book["id"]))
        return _list_item(rows[0])

    def remove_from_list(self, user_id: int, book_id: int) -> None:
        self.db.execute("DELETE FROM reading_list WHERE user_id = ? AND book_id = ?", (user_id, book_id))

    def clear_list(self, user_id: int) -> None:
        self.db.execute("DELETE FROM reading_list WHERE user_id = ?", (user_id,))

    def add_log_entry(self, user_id: int, entry: dict) -> dict:
        entry_id = entry.get("id") or str(uuid.uuid4())
        try:
            self.db.execute(
                "INSERT INTO reading_log (id, user_id, book_id, title, authors, year, cover_url, finished_on, rating, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry_id,
                    user_id,
                    entry.get("bookId"),
                    entry["title"],
                    entry.get("authors") or "",
                    entry.get("year"),
                    entry.get("cover_url"),
                    entry["finishedOn"],
                    int(entry.get("rating") or 0),
                    entry.get("notes") or "",
                ),
            )
        except sqlite3.IntegrityError:
            # The id is already used (e.g. by another account) - store it under a fresh id instead.
            return self.add_log_entry(user_id, {**entry, "id": str(uuid.uuid4())})
        rows = self.db.query("SELECT * FROM reading_log WHERE id = ?", (entry_id,))
        return _log_entry(rows[0])

    def update_log_entry(self, user_id: int, entry_id: str, changes: dict) -> dict | None:
        columns = {"rating": "rating", "notes": "notes", "finishedOn": "finished_on", "cover_url": "cover_url"}
        sets = [(columns[k], v) for k, v in changes.items() if k in columns]
        if sets:
            assignments = ", ".join(f"{column} = ?" for column, _ in sets)
            self.db.execute(
                f"UPDATE reading_log SET {assignments} WHERE id = ? AND user_id = ?",
                (*[value for _, value in sets], entry_id, user_id),
            )
        rows = self.db.query("SELECT * FROM reading_log WHERE id = ? AND user_id = ?", (entry_id, user_id))
        return _log_entry(rows[0]) if rows else None

    def remove_log_entry(self, user_id: int, entry_id: str) -> bool:
        cursor = self.db.execute("DELETE FROM reading_log WHERE id = ? AND user_id = ?", (entry_id, user_id))
        return cursor.rowcount > 0

    def get_goal(self, user_id: int) -> int:
        rows = self.db.query("SELECT yearly_goal FROM user_settings WHERE user_id = ?", (user_id,))
        return rows[0]["yearly_goal"] if rows else 0

    def set_goal(self, user_id: int, goal: int) -> int:
        self.db.execute(
            "INSERT INTO user_settings (user_id, yearly_goal) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET yearly_goal = excluded.yearly_goal",
            (user_id, goal),
        )
        return goal

    def import_data(self, user_id: int, data: dict) -> dict:
        """Merge reading data a guest saved in their browser into their account, skipping duplicates."""
        existing_list = {r["book_id"] for r in self.db.query("SELECT book_id FROM reading_list WHERE user_id = ?", (user_id,))}
        for book in data.get("readingList", []):
            if book["id"] not in existing_list:
                self.save_to_list(user_id, book)

        existing_log = {
            (r["book_id"], r["title"].lower(), r["finished_on"])
            for r in self.db.query("SELECT book_id, title, finished_on FROM reading_log WHERE user_id = ?", (user_id,))
        }
        for entry in data.get("readingLog", []):
            key = (entry.get("bookId"), entry["title"].lower(), entry["finishedOn"])
            if key not in existing_log:
                self.add_log_entry(user_id, {**entry, "id": str(uuid.uuid4())})
                existing_log.add(key)

        goal = int(data.get("goal") or 0)
        if goal > 0 and self.get_goal(user_id) == 0:
            self.set_goal(user_id, goal)
        return self.get_data(user_id)