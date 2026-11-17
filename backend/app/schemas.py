"""Request and response models for the API."""

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    genres: list[str] = Field(default_factory=list, max_length=10)
    mood: str | None = Field(default=None, max_length=50)
    liked_books: list[str] = Field(default_factory=list, max_length=10)
    description: str = Field(default="", max_length=1000)
    limit: int = Field(default=6, ge=1, le=20)
    exclude_ids: list[int] = Field(default_factory=list, max_length=200)


class ExplainRequest(RecommendRequest):
    book_ids: list[int] = Field(min_length=1, max_length=20)


class BookSummary(BaseModel):
    id: int
    title: str
    authors: str
    year: int | None = None


class Book(BookSummary):
    description: str
    genres: list[str]
    publisher: str
    cover_url: str | None = None
    score: float | None = None
    matched_genres: list[str] = Field(default_factory=list)
    reason: str | None = None


class LikedMatch(BaseModel):
    query: str
    match: BookSummary | None


class RecommendResponse(BaseModel):
    results: list[Book]
    liked: list[LikedMatch]


class ExplainResponse(BaseModel):
    reasons: dict[int, str]
    source: str  


class RatingSource(BaseModel):
    source: str
    average: float
    count: int
    url: str


class RatingsResponse(BaseModel):
    google: RatingSource | None = None
    open_library: RatingSource | None = None
    goodreads_url: str


class Genre(BaseModel):
    name: str
    count: int


class OptionsResponse(BaseModel):
    genres: list[Genre]
    moods: list[str]


class HealthResponse(BaseModel):
    status: str
    books: int
    llm_available: bool
    llm_model: str | None