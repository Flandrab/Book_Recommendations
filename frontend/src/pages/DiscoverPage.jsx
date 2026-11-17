import { useCallback, useRef, useState } from "react";
import { api } from "../api.js";
import BookCard from "../components/BookCard.jsx";
import SearchForm from "../components/SearchForm.jsx";
import "./discover.css";

const PAGE_SIZE = 6;
const EMPTY_FORM = { genres: [], mood: null, likedBooks: [], description: "" };

function toQuery(form) {
  return {
    genres: form.genres,
    mood: form.mood,
    liked_books: form.likedBooks,
    description: form.description,
    limit: PAGE_SIZE,
  };
}

// The recommendation page: search form on the left, results on the right.
export default function DiscoverPage({
  options,
  llmAvailable,
  bookCount,
  backendError,
  savedIds,
  onToggleSave,
  loggedIds,
  onToggleLogged,
}) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [lastQuery, setLastQuery] = useState(null);
  const [results, setResults] = useState([]);
  const [likedMatches, setLikedMatches] = useState([]);
  const [aiReasons, setAiReasons] = useState({});
  const [explainingIds, setExplainingIds] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const searchId = useRef(0);
  const resultsRef = useRef(null);

  // Ask the local LLM for personal explanations; results already show while this runs.
  const explain = useCallback(
    (query, books, id) => {
      if (!llmAvailable || books.length === 0) return;
      const ids = books.map((b) => b.id);
      setExplainingIds((prev) => new Set([...prev, ...ids]));
      api
        .explain(query, ids)
        .then(({ reasons }) => {
          if (searchId.current === id) setAiReasons((prev) => ({ ...prev, ...reasons }));
        })
        .catch(() => {})
        .finally(() => {
          if (searchId.current !== id) return;
          setExplainingIds((prev) => {
            const next = new Set(prev);
            ids.forEach((i) => next.delete(i));
            return next;
          });
        });
    },
    [llmAvailable]
  );

  const search = async () => {
    const id = ++searchId.current;
    const query = toQuery(form);
    setLoading(true);
    setError(null);
    setAiReasons({});
    setExplainingIds(new Set());
    try {
      const data = await api.recommend(query);
      if (searchId.current !== id) return;
      setResults(data.results);
      setLikedMatches(data.liked);
      setLastQuery(query);
      explain(query, data.results, id);
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) {
      if (searchId.current === id) setError(err.message);
    } finally {
      if (searchId.current === id) setLoading(false);
    }
  };

  const loadMore = async () => {
    if (!lastQuery) return;
    const id = searchId.current;
    setLoadingMore(true);
    try {
      const data = await api.recommend({ ...lastQuery, exclude_ids: results.map((b) => b.id) });
      if (searchId.current !== id) return;
      setResults((prev) => [...prev, ...data.results]);
      explain(lastQuery, data.results, id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingMore(false);
    }
  };

  const unmatchedLiked = likedMatches.filter((l) => !l.match).map((l) => l.query);

  return (
    <main className="layout">
      <section className="panel">
        <h1>
          Find your <em>next book.</em>
        </h1>
        <p className="lede">
          Tell us what you love and how you feel, and we'll search{" "}
          {bookCount ? `${bookCount.toLocaleString()} books` : "the whole catalogue"} for the ones that fit.
        </p>
        {backendError ? (
          <p className="alert">{backendError}</p>
        ) : (
          <SearchForm options={options} form={form} onChange={setForm} onSubmit={search} loading={loading} />
        )}
        {options && (
          <p className="ai-status">
            <span className={`dot ${llmAvailable ? "on" : ""}`} />
            {llmAvailable ? "Personal notes by a local AI model" : "AI notes are off (Ollama not running)"}
          </p>
        )}
      </section>

      <section className="results" ref={resultsRef} aria-live="polite">
        {error && <p className="alert">{error}</p>}

        {!results.length && !loading && !error && (
          <div className="empty-state">
            <div className="stack" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <h2>Your recommendations will appear here</h2>
            <p>Try a mood like "Cozy" with a book you loved, or describe exactly what you're craving.</p>
          </div>
        )}

        {loading && (
          <div className="thinking-state" role="status">
            <p className="hmm">
              Hmm
              <span className="hmm-dots" aria-hidden="true">
                <span>.</span>
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            </p>
            <p className="hint">Looking through the shelves for books you'll love</p>
            <div className="grid">
              {Array.from({ length: PAGE_SIZE }, (_, i) => (
                <div key={i} className="book-card skeleton" />
              ))}
            </div>
          </div>
        )}

        {!loading && results.length > 0 && (
          <>
            <div className="results-header">
              <h2>Picked for you</h2>
              {unmatchedLiked.length > 0 && (
                <p className="hint">
                  We couldn't find {unmatchedLiked.map((t) => `"${t}"`).join(", ")} in our catalogue, so we used the
                  title as a hint instead.
                </p>
              )}
            </div>
            <div className="grid">
              {results.map((book) => (
                <BookCard
                  key={book.id}
                  book={book}
                  aiReason={aiReasons[book.id]}
                  explaining={explainingIds.has(book.id)}
                  saved={savedIds.has(book.id)}
                  onToggleSave={onToggleSave}
                  logged={loggedIds.has(book.id)}
                  onToggleLogged={onToggleLogged}
                />
              ))}
            </div>
            <div className="more">
              <button type="button" className="secondary" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Show me more"}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}