import { useMemo, useState } from "react";
import BookCover from "../components/BookCover.jsx";
import BookLinks from "../components/BookLinks.jsx";
import BookSearchInput from "../components/BookSearchInput.jsx";
import StarRating from "../components/StarRating.jsx";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function todayISO() {
  return new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

function formatDate(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function monthLabel(key) {
  const [year, month] = key.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export default function ReadingLogPage({ readingLog, goal, onGoalChange, onAdd, onUpdate, onRemove }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [book, setBook] = useState(null);
  const [finishedOn, setFinishedOn] = useState(todayISO);
  const [rating, setRating] = useState(0);
  const [notes, setNotes] = useState("");

  const years = useMemo(() => {
    const set = new Set(readingLog.map((e) => Number(e.finishedOn.slice(0, 4))));
    set.add(currentYear);
    return [...set].sort((a, b) => b - a);
  }, [readingLog, currentYear]);

  const yearEntries = readingLog.filter((e) => e.finishedOn.startsWith(String(year)));
  const thisMonthKey = todayISO().slice(0, 7);
  const thisMonth = readingLog.filter((e) => e.finishedOn.startsWith(thisMonthKey)).length;
  const rated = yearEntries.filter((e) => e.rating > 0);
  const averageRating = rated.length ? (rated.reduce((sum, e) => sum + e.rating, 0) / rated.length).toFixed(1) : "-";

  const perMonth = MONTHS.map((_, i) => yearEntries.filter((e) => Number(e.finishedOn.slice(5, 7)) === i + 1).length);
  const maxPerMonth = Math.max(1, ...perMonth);

  const goalPercent = goal > 0 ? Math.min(100, Math.round((yearEntries.length / goal) * 100)) : 0;

  const groups = useMemo(() => {
    const sorted = [...yearEntries].sort((a, b) => b.finishedOn.localeCompare(a.finishedOn));
    const byMonth = new Map();
    sorted.forEach((entry) => {
      const key = entry.finishedOn.slice(0, 7);
      if (!byMonth.has(key)) byMonth.set(key, []);
      byMonth.get(key).push(entry);
    });
    return [...byMonth.entries()];
  }, [yearEntries]);

  const submit = (event) => {
    event.preventDefault();
    if (!book?.title) return;
    onAdd({
      bookId: book.id ?? null,
      title: book.title,
      authors: book.authors || "",
      year: book.year ?? null,
      finishedOn,
      rating,
      notes: notes.trim(),
    });
    setBook(null);
    setRating(0);
    setNotes("");
    setFinishedOn(todayISO());
    setYear(Number(finishedOn.slice(0, 4)));
  };

  return (
    <main className="log-page">
      <header className="page-header">
        <div>
          <h1>
            Reading <em>log.</em>
          </h1>
          <p className="lede">Every book you finish, in one place.</p>
        </div>
        {years.length > 1 && (
          <label className="year-select">
            Year
            <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      <section className="stat-strip" aria-label="Reading stats">
        <div className="stat">
          <span className="stat-value">{yearEntries.length}</span>
          <span className="stat-label">books read in {year}</span>
        </div>
        <div className="stat">
          <span className="stat-value">{thisMonth}</span>
          <span className="stat-label">this month</span>
        </div>
        <div className="stat">
          <span className="stat-value">{readingLog.length}</span>
          <span className="stat-label">books logged in total</span>
        </div>
        <div className="stat">
          <span className="stat-value">{averageRating}</span>
          <span className="stat-label">average rating in {year}</span>
        </div>
      </section>

      <div className="log-grid">
        <div className="log-side">
          <section className="card-panel">
            <h2>Yearly goal</h2>
            <div className="goal-row">
              <label htmlFor="goal-input">Books to read in {currentYear}</label>
              <input
                id="goal-input"
                type="number"
                min="0"
                max="1000"
                value={goal || ""}
                placeholder="e.g. 24"
                onChange={(e) => onGoalChange(Math.max(0, Math.min(1000, Number(e.target.value) || 0)))}
              />
            </div>
            {goal > 0 && year === currentYear && (
              <>
                <div className="progress large" aria-hidden="true">
                  <span style={{ width: `${goalPercent}%` }} />
                </div>
                <p className="hint">
                  {yearEntries.length >= goal
                    ? `Goal reached. ${yearEntries.length} of ${goal} books.`
                    : `${yearEntries.length} of ${goal} books, ${goal - yearEntries.length} to go.`}
                </p>
              </>
            )}
          </section>

          <section className="card-panel">
            <h2>Log a finished book</h2>
            <form className="log-form" onSubmit={submit}>
              <label>
                Book
                <BookSearchInput value={book} onChange={setBook} placeholder="Start typing the title" />
              </label>
              <label>
                Finished on
                <input
                  type="date"
                  value={finishedOn}
                  max={todayISO()}
                  onChange={(e) => setFinishedOn(e.target.value || todayISO())}
                />
              </label>
              <div className="field">
                <span>Your rating</span>
                <StarRating value={rating} onChange={setRating} />
              </div>
              <label>
                <span>
                  Notes <span className="hint">optional</span>
                </span>
                <textarea
                  rows={2}
                  maxLength={500}
                  value={notes}
                  placeholder="What did you think?"
                  onChange={(e) => setNotes(e.target.value)}
                />
              </label>
              <button type="submit" className="primary" disabled={!book?.title}>
                Add to log
              </button>
            </form>
          </section>
        </div>

        <div className="log-main">
          <section className="card-panel">
            <h2>Books per month in {year}</h2>
            <div className="month-chart" role="img" aria-label={`Books read per month in ${year}`}>
              {perMonth.map((count, i) => (
                <div key={MONTHS[i]} className="month-bar">
                  <span className="bar-value">{count || ""}</span>
                  <span className="bar" style={{ height: `${(count / maxPerMonth) * 100}%` }} />
                  <span className="bar-label">{MONTHS[i]}</span>
                </div>
              ))}
            </div>
          </section>

          {groups.length === 0 ? (
            <div className="empty-state small">
              <h2>No books logged in {year} yet</h2>
              <p>Add the last book you finished, or press "I've read this" on any recommendation.</p>
            </div>
          ) : (
            groups.map(([monthKey, entries]) => (
              <section key={monthKey} className="log-month">
                <h3>
                  {monthLabel(monthKey)} <span className="hint">{entries.length} book{entries.length > 1 ? "s" : ""}</span>
                </h3>
                <ul className="log-list">
                  {entries.map((entry) => (
                    <li key={entry.id}>
                      <BookCover title={entry.title} authors={entry.authors} coverUrl={entry.cover_url} size="small" />
                      <div className="log-entry">
                        <div className="log-entry-top">
                          <div>
                            <strong>{entry.title}</strong>
                            <span className="byline">
                              {entry.authors || "Unknown author"} · finished {formatDate(entry.finishedOn)}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="link danger"
                            onClick={() => {
                              if (window.confirm(`Remove "${entry.title}" from your log?`)) onRemove(entry.id);
                            }}
                          >
                            Remove
                          </button>
                        </div>
                        <StarRating
                          value={entry.rating}
                          size="small"
                          onChange={(value) => onUpdate(entry.id, { rating: value })}
                        />
                        {entry.notes && <p className="log-notes">{entry.notes}</p>}
                        <BookLinks title={entry.title} authors={entry.authors} year={entry.year} />
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))
          )}
        </div>
      </div>
    </main>
  );
}