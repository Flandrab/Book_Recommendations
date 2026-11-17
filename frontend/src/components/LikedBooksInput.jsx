import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const MAX_LIKED = 5;

// Text input with title suggestions from the dataset. Added books show as removable tags.
export default function LikedBooksInput({ books, onChange }) {
  const [text, setText] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [highlight, setHighlight] = useState(-1);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const query = text.trim();
    if (query.length < 2) {
      setSuggestions([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api
        .searchBooks(query, controller.signal)
        .then((results) => {
          setSuggestions(results);
          setHighlight(-1);
        })
        .catch(() => {});
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [text]);

  useEffect(() => {
    const close = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const add = (title) => {
    const clean = title.trim();
    if (!clean || books.length >= MAX_LIKED) return;
    if (!books.some((b) => b.toLowerCase() === clean.toLowerCase())) onChange([...books, clean]);
    setText("");
    setSuggestions([]);
    setOpen(false);
  };

  const onKeyDown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((h) => Math.max(h - 1, -1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      add(highlight >= 0 && suggestions[highlight] ? suggestions[highlight].title : text);
    } else if (event.key === "Escape") {
      setOpen(false);
    } else if (event.key === "Backspace" && !text && books.length) {
      onChange(books.slice(0, -1));
    }
  };

  const full = books.length >= MAX_LIKED;

  return (
    <div className="liked" ref={wrapperRef}>
      {books.length > 0 && (
        <ul className="tag-list">
          {books.map((title) => (
            <li key={title} className="tag">
              <span>{title}</span>
              <button
                type="button"
                aria-label={`Remove ${title}`}
                onClick={() => onChange(books.filter((b) => b !== title))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="autocomplete">
        <input
          type="text"
          value={text}
          disabled={full}
          placeholder={full ? `Up to ${MAX_LIKED} books` : "Start typing a title, press Enter to add"}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          role="combobox"
          aria-expanded={open && suggestions.length > 0}
          aria-controls="liked-suggestions"
          aria-autocomplete="list"
        />
        {open && suggestions.length > 0 && (
          <ul className="suggestions" id="liked-suggestions" role="listbox">
            {suggestions.map((book, index) => (
              <li
                key={book.id}
                role="option"
                aria-selected={index === highlight}
                className={index === highlight ? "active" : ""}
                onMouseDown={(e) => {
                  e.preventDefault();
                  add(book.title);
                }}
                onMouseEnter={() => setHighlight(index)}
              >
                <span className="suggestion-title">{book.title}</span>
                <span className="suggestion-meta">
                  {[book.authors, book.year].filter(Boolean).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
