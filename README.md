# Next Chapter - AI Book Recommendations

Tell it the genres you like, the mood you're in and the books you loved, and it finds books that fit. It explains each pick in plain language with a local LLM.

- **Semantic search, not keyword matching.** Every book is embedded with a sentence-transformer model. Your request is turned into a "taste vector" and books are ranked by meaning, so "a cozy mystery in a small village" finds books that never use those exact words.
- **Personal explanations.** A local LLM (via [Ollama](https://ollama.com)) writes a short "why you'll like it" note for each book. It runs on your machine: no API key and no cost.
- **Real covers** from the free [Open Library](https://openlibrary.org) API, with generated covers as a fallback.
- **Reading list** saved in your browser, with read/unread tracking.
- **Varied results.** Maximal Marginal Relevance keeps you from getting five copies of the same book.

## How it works

```
Your request                       Offline (once)
-------------                      ---------------
genres, mood,                      BooksDataset.csv
books you loved,                         |
your own words                     clean + embed every book
      |                                  |
      v                                  v
 taste vector  -- cosine similarity -->  index (embeddings.npy)
                                         |
                       genre filter -> MMR diversity -> top N books
                                         |
                    +--------------------+--------------------+
                    v                                         v
         Open Library covers                    Ollama: "why you'll like it"
```

1. **Data** (`backend/app/data.py`) cleans the CSV: fixes author names ("By Black, Holly" becomes "Holly Black"), splits genres, removes duplicate editions and builds one text per book.
2. **Index** (`backend/app/embeddings.py`) embeds every book with `all-MiniLM-L6-v2` once and caches the result in `backend/index/`. It is rebuilt automatically if the dataset or model changes.
3. **Recommender** (`backend/app/recommender.py`) mixes the parts of your request into one vector. The weights are: liked books 1.0, your description 1.0, mood 0.6, genres 0.4. It ranks all books by cosine similarity, keeps your chosen genres, skips books you already named and diversifies the list with MMR.
4. **Explanations** (`backend/app/llm.py`): the results show immediately, then the frontend asks the LLM for personal notes and swaps them in when they're ready. If Ollama isn't running, you still get a short reason based on what matched.

## Tech stack

| Part      | Tech                                                                     |
| --------- | ------------------------------------------------------------------------ |
| Frontend  | React 19, Vite, plain CSS (light + dark mode, responsive)                |
| Backend   | FastAPI, pandas, NumPy                                                   |
| AI        | sentence-transformers (`all-MiniLM-L6-v2`), Ollama (`llama3.2:3b`)      |
| Data      | Books dataset CSV + Open Library covers API                              |
| Deploy    | Docker (multi-stage), docker compose with Ollama                         |

## Project structure

```
Book_Recommendations/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app and API routes
│   │   ├── config.py        # settings from environment variables / .env
│   │   ├── data.py          # load + clean the CSV
│   │   ├── embeddings.py    # embedding model + cached index
│   │   ├── recommender.py   # ranking, genre filter, MMR, reasons
│   │   ├── llm.py           # Ollama explanations
│   │   ├── covers.py        # Open Library covers (cached)
│   │   └── schemas.py       # request/response models
│   ├── data/BooksDataset.csv
│   ├── scripts/build_index.py
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── styles.css
│   │   ├── hooks/useLocalStorage.js
│   │   └── components/      # SearchForm, LikedBooksInput, BookCard, BookCover, ReadingList
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Run it locally

You need **Python 3.11+**, **Node.js 20+** and, for the AI notes, **[Ollama](https://ollama.com/download)**.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt
python -m scripts.build_index        # first time only: embeds every book, takes a while on CPU
uvicorn app.main:app --reload --port 8000
```

When it's ready you'll see `Application startup complete`. Check http://localhost:8000/api/health.

### 2. Local LLM (optional, but it's the fun part)

```bash
ollama pull llama3.2:3b
```

Ollama runs in the background after installing. The app finds it at `http://localhost:11434` automatically. You can use any other model too, by setting `OLLAMA_MODEL` in `.env`.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Tests

```bash
cd backend
pytest
```

The tests use a tiny fake dataset and a fake embedder, so they run in under a second without downloading any model.

## Run with Docker

```bash
cp .env.example .env              # optional, set CONTACT_EMAIL
docker compose up --build
```

Open http://localhost:8000. The first start embeds the whole dataset before the app answers; later starts reuse the saved index. The `ollama-pull` service downloads the LLM once and exits.

## Deploy online

The full stack (app and Ollama) needs about **4-6 GB of RAM**, so a small VPS works best (Hetzner, DigitalOcean, AWS Lightsail and similar):

1. Create an Ubuntu server with at least 4 GB RAM and install Docker.
2. `git clone` this repo onto it.
3. Run `docker compose up -d --build`.
4. Point a domain at the server and put a reverse proxy with HTTPS in front of port 8000. [Caddy](https://caddyserver.com) does this in two lines.

For a host with less memory, run only the `app` service with `LLM_ENABLED=false`. Recommendations, covers and the reading list all still work; the cards show the built-in reasons instead of LLM notes.

## API

| Method | Path                      | What it does                                         |
| ------ | ------------------------- | ---------------------------------------------------- |
| GET    | `/api/health`             | status, number of books, whether the LLM is reachable |
| GET    | `/api/options`            | top genres and the list of moods                      |
| GET    | `/api/books/search?q=`    | title autocomplete                                    |
| GET    | `/api/books/{id}`         | one book with its cover                               |
| POST   | `/api/recommend`          | recommendations (`genres`, `mood`, `liked_books`, `description`, `limit`, `exclude_ids`) |
| POST   | `/api/explain`            | LLM explanations for a list of `book_ids`             |

Interactive docs: http://localhost:8000/docs

## Author

Flandra Bytyqi
