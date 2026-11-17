import { useEffect } from "react";
import BookCover from "./BookCover.jsx";

export default function ReadingList({ open, books, onClose, onRemove, onToggleRead, onClear }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const unread = books.filter((b) => !b.read).length;

  return (
    <>
      <div className={`backdrop ${open ? "visible" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside className={`drawer ${open ? "open" : ""}`} aria-label="Reading list" aria-hidden={!open}>
        <div className="drawer-header">
          <div>
            <h2>Reading list</h2>
            <p className="hint">
              {books.length === 0 ? "Nothing saved yet" : `${books.length} saved · ${unread} to read`}
            </p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close reading list">
            ×
          </button>
        </div>

        {books.length === 0 ? (
          <p className="empty-list">Save books from your recommendations and they'll wait for you here.</p>
        ) : (
          <ul className="saved-list">
            {books.map((book) => (
              <li key={book.id} className={book.read ? "read" : ""}>
                <BookCover title={book.title} authors={book.authors} coverUrl={book.cover_url} size="small" />
                <div className="saved-info">
                  <strong>{book.title}</strong>
                  <span>{book.authors || "Unknown author"}</span>
                  <div className="saved-actions">
                    <label>
                      <input type="checkbox" checked={!!book.read} onChange={() => onToggleRead(book.id)} />
                      Read
                    </label>
                    <button type="button" className="link" onClick={() => onRemove(book.id)}>
                      Remove
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}

        {books.length > 0 && (
          <button type="button" className="link danger clear-all" onClick={onClear}>
            Clear list
          </button>
        )}
      </aside>
    </>
  );
}
