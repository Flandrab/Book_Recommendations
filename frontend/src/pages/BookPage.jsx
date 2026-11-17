import { useEffect, useState } from "react";
import { api } from "../api.js";
import BookCover from "../components/BookCover.jsx";
import BookLinks from "../components/BookLinks.jsx";
import "./bookpage.css";

function goBack() {
  if (window.history.length > 1) window.history.back();
  else window.location.hash = "#/discover";
}

function Stars({ average }) {
  const rounded = Math.round(average * 2) / 2;
  return (
    <span className="rating-stars" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= rounded ? "on" : n - 0.5 === rounded ? "half" : ""}>
          ★
        </span>
      ))}
    </span>
  );
}

function RatingCard({ name, rating, loading }) {
  return (
    <div className="rating-card">
      <span className="rating-source">{name}</span>
      {loading ? (
        <p className="rating-empty">Checking ratings...</p>
      ) : rating ? (
        <>
          <div className="rating-score">
            <strong>{rating.average.toFixed(1)}</strong>
            <span>/ 5</span>
          </div>
          <Stars average={rating.average} />
          <p className="rating-count">
            from {rating.count.toLocaleString()} rating{rating.count === 1 ? "" : "s"}
          </p>
          <a href={rating.url} target="_blank" rel="noopener noreferrer">
            View on {name}
          </a>
        </>
      ) : (
        <p className="rating-empty">No ratings found on {name}.</p>
      )}
    </div>
  );
}

export default function BookPage({ bookId, savedIds, onToggleSave, loggedIds, onToggleLogged }) {
  const [book, setBook] = useState(null);
  const [error, setError] = useState(null);
  const [ratings, setRatings] = useState(null);
  const [ratingsLoading, setRatingsLoading] = useState(true);
  const [similar, setSimilar] = useState([]);

  useEffect(() => {
    let active = true;
    api
      .book(bookId)
      .then((data) => active && setBook(data))
      .catch((err) => active && setError(err.message));
    api
      .ratings(bookId)
      .then((data) => active && setRatings(data))
      .catch(() => {})
      .finally(() => active && setRatingsLoading(false));
    api
      .similarBooks(bookId)
      .then((data) => active && setSimilar(data))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [bookId]);

  if (error) {
    return (
      <main className="book-page">
        <button type="button" className="back-button" onClick={goBack}>
          Back
        </button>
        <p className="alert">{error === "Book not found" ? "We couldn't find that book." : error}</p>
      </main>
    );
  }

  if (!book) {
    return (
      <main className="book-page">
        <div className="book-hero skeleton-block" />
      </main>
    );
  }

  const saved = savedIds.has(book.id);
  const logged = loggedIds.has(book.id);

  return (
    <main className="book-page">
      <button type="button" className="back-button" onClick={goBack}>
        Back
      </button>

      <section className="book-hero">
        <div className="book-hero-cover">
          <BookCover title={book.title} authors={book.authors} coverUrl={book.cover_url} />
        </div>

        <div className="book-hero-info">
          {book.genres?.length > 0 && (
            <ul className="genre-tags">
              {book.genres.map((genre) => (
                <li key={genre}>{genre}</li>
              ))}
            </ul>
          )}
          <h1>{book.title}</h1>
          <p className="book-author">{book.authors || "Unknown author"}</p>

          <dl className="book-facts">
            {book.year && (
              <div>
                <dt>Published</dt>
                <dd>{book.year}</dd>
              </div>
            )}
            {book.publisher && (
              <div>
                <dt>Publisher</dt>
                <dd>{book.publisher}</dd>
              </div>
            )}
          </dl>

          <div className="card-actions">
            <button
              type="button"
              className={`save ${saved ? "saved" : ""}`}
              aria-pressed={saved}
              onClick={() => onToggleSave(book)}
            >
              {saved ? "On your list" : "Save to reading list"}
            </button>
            <button
              type="button"
              className={`log-button ${logged ? "logged" : ""}`}
              aria-pressed={logged}
              onClick={() => onToggleLogged(book)}
            >
              {logged ? "Read ✓" : "I've read this"}
            </button>
          </div>

          <BookLinks title={book.title} authors={book.authors} year={book.year} />
        </div>
      </section>

      <section className="book-section">
        <h2>About this book</h2>
        <p className="book-description">{book.description || "No description available for this book."}</p>
      </section>

      <section className="book-section">
        <h2>Ratings</h2>
        <div className="rating-grid">
          <RatingCard name="Google Books" rating={ratings?.google} loading={ratingsLoading} />
          <RatingCard name="Open Library" rating={ratings?.open_library} loading={ratingsLoading} />
        </div>
      </section>

      {similar.length > 0 && (
        <section className="book-section">
          <h2>If you like this, try</h2>
          <ul className="similar-grid">
            {similar.map((other) => (
              <li key={other.id}>
                <a href={`#/book/${other.id}`}>
                  <BookCover title={other.title} authors={other.authors} coverUrl={other.cover_url} />
                  <strong>{other.title}</strong>
                  <span>{other.authors || "Unknown author"}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}