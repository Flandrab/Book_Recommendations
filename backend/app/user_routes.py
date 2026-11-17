"""API routes for accounts and each user's saved data.

Sign-in uses an HttpOnly session cookie, so the browser sends it automatically and JavaScript can't read it.
"""

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import SESSION_DAYS, LoginThrottle
from .store import EmailTakenError, UserStore

SESSION_COOKIE = "booktag_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api")
throttle = LoginThrottle()


# ----- request models ----------------------------------------------------------------------


class SignupIn(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter your name.")
        return value


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ListItemIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=500)
    authors: str = Field(default="", max_length=500)
    year: int | None = None
    cover_url: str | None = Field(default=None, max_length=1000)
    saved_at: int | None = Field(default=None, alias="savedAt")

    def to_store(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "cover_url": self.cover_url,
            "savedAt": self.saved_at,
        }


class LogEntryIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, max_length=64)
    book_id: int | None = Field(default=None, alias="bookId")
    title: str = Field(min_length=1, max_length=500)
    authors: str = Field(default="", max_length=500)
    year: int | None = None
    cover_url: str | None = Field(default=None, max_length=1000)
    finished_on: date = Field(alias="finishedOn")
    rating: int = Field(default=0, ge=0, le=5)
    notes: str = Field(default="", max_length=500)

    def to_store(self) -> dict:
        return {
            "id": self.id,
            "bookId": self.book_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "cover_url": self.cover_url,
            "finishedOn": self.finished_on.isoformat(),
            "rating": self.rating,
            "notes": self.notes,
        }


class LogEntryPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rating: int | None = Field(default=None, ge=0, le=5)
    notes: str | None = Field(default=None, max_length=500)
    finished_on: date | None = Field(default=None, alias="finishedOn")
    cover_url: str | None = Field(default=None, max_length=1000)

    def to_store(self) -> dict:
        changes = {}
        if self.rating is not None:
            changes["rating"] = self.rating
        if self.notes is not None:
            changes["notes"] = self.notes
        if self.finished_on is not None:
            changes["finishedOn"] = self.finished_on.isoformat()
        if self.cover_url is not None:
            changes["cover_url"] = self.cover_url
        return changes


class GoalIn(BaseModel):
    goal: int = Field(ge=0, le=1000)


class ImportIn(BaseModel):
    reading_list: list[ListItemIn] = Field(default_factory=list, alias="readingList", max_length=2000)
    reading_log: list[LogEntryIn] = Field(default_factory=list, alias="readingLog", max_length=5000)
    goal: int = Field(default=0, ge=0, le=1000)


# ----- helpers -----------------------------------------------------------------------------


def get_store(request: Request) -> UserStore:
    return request.app.state.users


def current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    user = get_store(request).user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


def _start_session(request: Request, response: Response, user: dict) -> None:
    token = get_store(request).create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.cookie_secure,
        path="/",
    )


# ----- auth routes -------------------------------------------------------------------------


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response) -> dict:
    try:
        user = get_store(request).create_user(body.email, body.name, body.password)
    except EmailTakenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _start_session(request, response, user)
    return user


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    key = body.email.strip().lower()
    if throttle.is_blocked(key):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    user = get_store(request).authenticate(body.email, body.password)
    if user is None:
        throttle.record_failure(key)
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    throttle.reset(key)
    _start_session(request, response, user)
    return user


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        get_store(request).delete_session(token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


# ----- per-user data routes ----------------------------------------------------------------


@router.get("/me/data")
def my_data(request: Request, user: dict = Depends(current_user)) -> dict:
    return get_store(request).get_data(user["id"])


@router.put("/me/reading-list/{book_id}")
def save_book(book_id: int, body: ListItemIn, request: Request, user: dict = Depends(current_user)) -> dict:
    if body.id != book_id:
        raise HTTPException(status_code=400, detail="Book id in the URL and the body don't match.")
    return get_store(request).save_to_list(user["id"], body.to_store())


@router.delete("/me/reading-list/{book_id}")
def unsave_book(book_id: int, request: Request, user: dict = Depends(current_user)) -> dict:
    get_store(request).remove_from_list(user["id"], book_id)
    return {"ok": True}


@router.delete("/me/reading-list")
def clear_reading_list(request: Request, user: dict = Depends(current_user)) -> dict:
    get_store(request).clear_list(user["id"])
    return {"ok": True}


@router.post("/me/reading-log", status_code=201)
def add_log_entry(body: LogEntryIn, request: Request, user: dict = Depends(current_user)) -> dict:
    return get_store(request).add_log_entry(user["id"], body.to_store())


@router.patch("/me/reading-log/{entry_id}")
def update_log_entry(entry_id: str, body: LogEntryPatch, request: Request, user: dict = Depends(current_user)) -> dict:
    entry = get_store(request).update_log_entry(user["id"], entry_id, body.to_store())
    if entry is None:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    return entry


@router.delete("/me/reading-log/{entry_id}")
def delete_log_entry(entry_id: str, request: Request, user: dict = Depends(current_user)) -> dict:
    if not get_store(request).remove_log_entry(user["id"], entry_id):
        raise HTTPException(status_code=404, detail="Log entry not found.")
    return {"ok": True}


@router.put("/me/goal")
def set_goal(body: GoalIn, request: Request, user: dict = Depends(current_user)) -> dict:
    return {"goal": get_store(request).set_goal(user["id"], body.goal)}


@router.post("/me/import")
def import_guest_data(body: ImportIn, request: Request, user: dict = Depends(current_user)) -> dict:
    data = {
        "readingList": [item.to_store() for item in body.reading_list],
        "readingLog": [entry.to_store() for entry in body.reading_log],
        "goal": body.goal,
    }
    return get_store(request).import_data(user["id"], data)