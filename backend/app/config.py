"""Application settings, read from environment variables with sensible defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent

try:  # read a .env file in the project root, if there is one
    from dotenv import load_dotenv

    load_dotenv(PROJECT_DIR / ".env")
except ImportError:
    pass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    # Data and index
    books_csv: Path = field(
        default_factory=lambda: Path(os.getenv("BOOKS_CSV", BACKEND_DIR / "data" / "BooksDataset.csv"))
    )
    index_dir: Path = field(default_factory=lambda: Path(os.getenv("INDEX_DIR", BACKEND_DIR / "index")))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )

    # Local LLM (Ollama)
    llm_enabled: bool = field(default_factory=lambda: _env_bool("LLM_ENABLED", True))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    llm_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "90")))

    # Book covers (Open Library)
    covers_enabled: bool = field(default_factory=lambda: _env_bool("COVERS_ENABLED", True))
    covers_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("COVERS_TIMEOUT_SECONDS", "6")))
    covers_cache_file: Path = field(
        default_factory=lambda: Path(os.getenv("COVERS_CACHE_FILE", BACKEND_DIR / "index" / "covers_cache.json"))
    )
    contact_email: str = field(default_factory=lambda: os.getenv("CONTACT_EMAIL", "you@example.com"))

    # Ratings (Google Books + Open Library). A free Google API key raises Google's request limit.
    ratings_enabled: bool = field(default_factory=lambda: _env_bool("RATINGS_ENABLED", True))
    ratings_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("RATINGS_TIMEOUT_SECONDS", "8")))
    google_books_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_BOOKS_API_KEY", ""))

    # User accounts (SQLite database file). Set COOKIE_SECURE=true when the site runs on HTTPS.
    database_path: Path = field(
        default_factory=lambda: Path(os.getenv("DATABASE_PATH", BACKEND_DIR / "db" / "booktag.db"))
    )
    cookie_secure: bool = field(default_factory=lambda: _env_bool("COOKIE_SECURE", False))

    # Web
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _env_list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )
    frontend_dist: Path = field(
        default_factory=lambda: Path(os.getenv("FRONTEND_DIST", PROJECT_DIR / "frontend" / "dist"))
    )


def get_settings() -> Settings:
    return Settings()