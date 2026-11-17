"""FastAPI application: the JSON API, plus the built React frontend when it exists."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .covers import CoverService
from .db import Database
from .llm import OllamaExplainer
from .ratings import RatingsService, goodreads_search_url
from .recommender import EmptyQueryError, RecommendationQuery, Recommender
from .schemas import (
    Book,
    BookSummary,
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    OptionsResponse,
    RatingsResponse,
    RecommendRequest,
    RecommendResponse,
)
from .store import UserStore
from .user_routes import router as user_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_recommender(settings: Settings) -> Recommender:
    from .data import load_books
    from .embeddings import SentenceTransformerEmbedder, load_or_build_index

    books = load_books(settings.books_csv)
    logger.info("Loaded %d books", len(books))
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    embeddings = load_or_build_index(books, embedder, settings.index_dir, settings.embedding_model)
    return Recommender(books, embeddings, embedder)


def _to_query(request: RecommendRequest) -> RecommendationQuery:
    return RecommendationQuery(
        genres=[g.strip() for g in request.genres if g.strip()],
        mood=request.mood,
        liked_books=request.liked_books,
        description=request.description,
        limit=request.limit,
        exclude_ids=request.exclude_ids,
    )


def create_app(settings: Settings | None = None, recommender: Recommender | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.db = Database(settings.database_path)
        app.state.users = UserStore(app.state.db)
        app.state.users.delete_expired_sessions()
        app.state.recommender = recommender or await run_in_threadpool(build_recommender, settings)
        app.state.http = httpx.AsyncClient(follow_redirects=True)
        app.state.covers = (
            CoverService(app.state.http, settings.covers_cache_file, settings.covers_timeout_seconds, settings.contact_email)
            if settings.covers_enabled
            else None
        )
        app.state.ratings = (
            RatingsService(
                app.state.http, settings.ratings_timeout_seconds, settings.google_books_api_key, settings.contact_email
            )
            if settings.ratings_enabled
            else None
        )
        app.state.explainer = (
            OllamaExplainer(app.state.http, settings.ollama_url, settings.ollama_model, settings.llm_timeout_seconds)
            if settings.llm_enabled
            else None
        )
        yield
        await app.state.http.aclose()
        app.state.db.close()

    app = FastAPI(title="BookTag API", version="2.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(user_router)

    def get_book_or_404(rec: Recommender, book_id: int) -> dict:
        if not 0 <= book_id < len(rec.books):
            raise HTTPException(status_code=404, detail="Book not found")
        return rec.book_details(book_id)

    @app.get("/api/health", response_model=HealthResponse)
    async def health():
        explainer = app.state.explainer
        available = await explainer.is_available() if explainer else False
        return HealthResponse(
            status="ok",
            books=len(app.state.recommender.books),
            llm_available=available,
            llm_model=settings.ollama_model if explainer else None,
        )

    @app.get("/api/options", response_model=OptionsResponse)
    async def options():
        rec: Recommender = app.state.recommender
        return OptionsResponse(genres=rec.top_genres(40), moods=rec.moods())

    @app.get("/api/books/search", response_model=list[BookSummary])
    async def search_books(q: str = Query(min_length=1, max_length=200), limit: int = Query(8, ge=1, le=20)):
        return await run_in_threadpool(app.state.recommender.search_titles, q, limit)

    @app.get("/api/books/{book_id}", response_model=Book)
    async def get_book(book_id: int):
        book = get_book_or_404(app.state.recommender, book_id)
        if app.state.covers:
            await app.state.covers.add_covers([book])
        return book

    @app.get("/api/books/{book_id}/similar", response_model=list[Book])
    async def similar_books(book_id: int, limit: int = Query(6, ge=1, le=20)):
        rec: Recommender = app.state.recommender
        get_book_or_404(rec, book_id)
        books = await run_in_threadpool(rec.similar, book_id, limit)
        if app.state.covers:
            await app.state.covers.add_covers(books)
        return books

    @app.get("/api/books/{book_id}/ratings", response_model=RatingsResponse)
    async def book_ratings(book_id: int):
        book = get_book_or_404(app.state.recommender, book_id)
        if app.state.ratings is None:
            return RatingsResponse(goodreads_url=goodreads_search_url(book["title"], book["authors"]))
        return await app.state.ratings.ratings_for(book["title"], book["authors"])

    @app.post("/api/recommend", response_model=RecommendResponse)
    async def recommend(request: RecommendRequest):
        try:
            result = await run_in_threadpool(app.state.recommender.recommend, _to_query(request))
        except EmptyQueryError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if app.state.covers:
            await app.state.covers.add_covers(result["results"])
        return result

    @app.post("/api/explain", response_model=ExplainResponse)
    async def explain(request: ExplainRequest):
        explainer: OllamaExplainer | None = app.state.explainer
        if explainer is None:
            return ExplainResponse(reasons={}, source="unavailable")
        rec: Recommender = app.state.recommender
        books = [get_book_or_404(rec, i) for i in request.book_ids]
        profile = await run_in_threadpool(rec.taste_profile, _to_query(request))
        reasons = await explainer.explain(profile, books)
        return ExplainResponse(reasons=reasons, source="llm" if reasons else "unavailable")

    # Serve the built React app (npm run build) from the same server, if it exists.
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")

    return app


app = create_app()