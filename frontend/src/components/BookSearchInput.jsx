import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";


export default function BookSearchInput({ value, onChange, placeholder = "Search for a book" }) {
  const [text, setText] = useState(value?.title ?? "");
  const [suggestions, setSuggestions] = useState([]);
  const [highlight, setHighlight] = useState(-1);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  
  useEffect(() => {
    if (!value) setText("");
  }, [value]);

  useEffect(() => {
    const query = text.trim();
   
    if (query.length < 2 || (value?.id != null && value.title === text)) {
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
  }, [text, value]);

  useEffect(() => {
    const close = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const choose = (book) => {
    setText(book.title);
    setSuggestions([]);
    setOpen(false);
    onChange(book);
  };

  const onKeyDown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((h) => Math.max(h - 1, -1));
    } else if (event.key === "Enter" && open && highlight >= 0 && suggestions[highlight]) {
      event.preventDefault();
      choose(suggestions[highlight]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="autocomplete" ref={wrapperRef}>
      <input
        type="text"
        value={text}
        placeholder={placeholder}
        onChange={(e) => {
          const next = e.target.value;
          setText(next);
          setOpen(true);
          onChange(next.trim() ? { id: null, title: next.trim(), authors: "", year: null } : null);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-controls="book-search-suggestions"
        aria-autocomplete="list"
      />
      {open && suggestions.length > 0 && (
        <ul className="suggestions" id="book-search-suggestions" role="listbox">
          {suggestions.map((book, index) => (
            <li
              key={book.id}
              role="option"
              aria-selected={index === highlight}
              className={index === highlight ? "active" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(book);
              }}
              onMouseEnter={() => setHighlight(index)}
            >
              <span className="suggestion-title">{book.title}</span>
              <span className="suggestion-meta">{[book.authors, book.year].filter(Boolean).join(" · ")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}