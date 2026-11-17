import { useState } from "react";
import BookCover from "./BookCover.jsx";
import BookLinks from "./BookLinks.jsx";

const DESCRIPTION_PREVIEW = 220;

export default function BookCard({ book, aiReason, explaining, saved, onToggleSave, logged, onToggleLogged }) {
  const [expanded, setExpanded] = useState(false);
  const description = book.description || "";
  const long = description.length > DESCRIPTION_PREVIEW;
  const shownDescription =
    expanded || !long ? description : `${description.slice(0, DESCRIPTION_PREVIEW).trimEnd()}...`;

  return (
    <article className="book-card">
      <a className="cover-link" href={`#/book/${book.id}`} aria-label={`Open ${book.title}`}>
        <BookCover title={book.title} authors={book.authors} coverUrl={book.cover_url} />
      </a>

      <div className="book-body">
        <header>
          <h3>
            <a className="title-link" href={`#/book/${book.id}`}>
              {book.title}
            </a>
          </h3>
          <p className="byline">
            {[book.authors, book.year].filter(Boolean).join(" · ") || "Unknown author"}
          </p>
        </header>

        <div className={`reason ${aiReason ? "reason-ai" : ""}`}>
          <span className="reason-label">{aiReason ? "Why you'll like it" : "Why it matches"}</span>
          <p>{aiReason || book.reason}</p>
          {explaining && !aiReason && <span className="thinking">Writing a personal note...</span>}
        </div>

        {book.genres?.length > 0 && (
          <ul className="genre-tags">
            {book.genres.slice(0, 4).map((genre) => (
              <li key={genre} className={book.matched_genres?.includes(genre) ? "matched" : ""}>
                {genre}
              </li>
            ))}
          </ul>
        )}

        {description && (
          <p className="description">
            {shownDescription}
            {long && (
              <button type="button" className="link" onClick={() => setExpanded((v) => !v)}>
                {expanded ? "Show less" : "Read more"}
              </button>
            )}
          </p>
        )}

        <BookLinks title={book.title} authors={book.authors} year={book.year} />

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
      </div>
    </article>
  );
}