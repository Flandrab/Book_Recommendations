import BookCover from "../components/BookCover.jsx";
import StarRating from "../components/StarRating.jsx";

const STEPS = [
  {
    title: "Tell us your taste",
    text: "Pick genres and a mood, add books you loved, or just describe what you're craving.",
  },
  {
    title: "Get picks that fit",
    text: "BookTag searches the whole catalogue by meaning, and explains why each book suits you.",
  },
  {
    title: "Track your reading",
    text: "Save books for later, log the ones you finish, rate them and watch your yearly goal fill up.",
  },
];

export default function HomePage({ readingList, readingLog, goal, bookCount, onOpenList }) {
  const year = new Date().getFullYear();
  const readThisYear = readingLog.filter((e) => e.finishedOn?.startsWith(String(year))).length;
  const goalPercent = goal > 0 ? Math.min(100, Math.round((readThisYear / goal) * 100)) : 0;
  const recent = [...readingLog].sort((a, b) => b.finishedOn.localeCompare(a.finishedOn)).slice(0, 4);
  const loggedIds = new Set(readingLog.map((e) => e.bookId).filter((id) => id !== null && id !== undefined));
  const upNext = readingList.filter((b) => !loggedIds.has(b.id)).slice(0, 4);

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">Your reading, tagged and tracked</p>
          <h1>
            Read more of <em>what you love.</em>
          </h1>
          <p className="lede">
            BookTag recommends books from your favourite genres, your mood and the books you've loved, then helps you
            keep track of everything you read.
          </p>
          <div className="hero-actions">
            <a className="primary button-link" href="#/discover">
              Get recommendations
            </a>
            <a className="secondary button-link" href="#/log">
              Log a book
            </a>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <span className="spine s1">Mystery</span>
          <span className="spine s2">Fantasy</span>
          <span className="spine s3">Romance</span>
          <span className="spine s4">History</span>
          <span className="spine s5">Sci-Fi</span>
          <span className="hero-tag">BookTag</span>
        </div>
      </section>

      <section className="stat-strip" aria-label="Your reading at a glance">
        <a className="stat" href="#/log">
          <span className="stat-value">{readThisYear}</span>
          <span className="stat-label">books read in {year}</span>
        </a>
        <a className="stat" href="#/log">
          <span className="stat-value">{goal > 0 ? `${goalPercent}%` : "-"}</span>
          <span className="stat-label">{goal > 0 ? `of your ${goal}-book goal` : "set a yearly goal"}</span>
          {goal > 0 && (
            <span className="progress" aria-hidden="true">
              <span style={{ width: `${goalPercent}%` }} />
            </span>
          )}
        </a>
        <button type="button" className="stat" onClick={onOpenList}>
          <span className="stat-value">{readingList.length}</span>
          <span className="stat-label">on your reading list</span>
        </button>
        <a className="stat" href="#/discover">
          <span className="stat-value">{bookCount ? bookCount.toLocaleString() : "-"}</span>
          <span className="stat-label">books to discover</span>
        </a>
      </section>

      <section className="steps">
        <h2>How it works</h2>
        <ol>
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <span className="step-number">{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="home-columns">
        <div className="home-column">
          <div className="column-header">
            <h2>Up next</h2>
            {readingList.length > 0 && (
              <button type="button" className="link" onClick={onOpenList}>
                See all
              </button>
            )}
          </div>
          {upNext.length === 0 ? (
            <p className="muted">
              Nothing waiting yet. <a href="#/discover">Find something to read</a> and save it to your list.
            </p>
          ) : (
            <ul className="mini-list">
              {upNext.map((book) => (
                <li key={book.id}>
                  <BookCover title={book.title} authors={book.authors} coverUrl={book.cover_url} size="small" />
                  <div>
                    <strong>{book.title}</strong>
                    <span>{book.authors || "Unknown author"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="home-column">
          <div className="column-header">
            <h2>Recently finished</h2>
            {readingLog.length > 0 && (
              <a className="link" href="#/log">
                Reading log
              </a>
            )}
          </div>
          {recent.length === 0 ? (
            <p className="muted">
              No books logged yet. <a href="#/log">Log the last book you finished</a>.
            </p>
          ) : (
            <ul className="mini-list">
              {recent.map((entry) => (
                <li key={entry.id}>
                  <BookCover title={entry.title} authors={entry.authors} coverUrl={entry.cover_url} size="small" />
                  <div>
                    <strong>{entry.title}</strong>
                    <span>
                      {new Date(`${entry.finishedOn}T00:00:00`).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <StarRating value={entry.rating} size="small" />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}