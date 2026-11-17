import { useState } from "react";
import LikedBooksInput from "./LikedBooksInput.jsx";

const VISIBLE_GENRES = 14;
const MAX_GENRES = 3;

export default function SearchForm({ options, form, onChange, onSubmit, loading }) {
  const [showAllGenres, setShowAllGenres] = useState(false);
  const genres = options?.genres ?? [];
  const moods = options?.moods ?? [];
  const shownGenres = showAllGenres ? genres : genres.slice(0, VISIBLE_GENRES);

  const update = (patch) => onChange({ ...form, ...patch });

  const toggleGenre = (name) => {
    if (form.genres.includes(name)) update({ genres: form.genres.filter((g) => g !== name) });
    else if (form.genres.length < MAX_GENRES) update({ genres: [...form.genres, name] });
  };

  const isEmpty = !form.genres.length && !form.mood && !form.likedBooks.length && !form.description.trim();

  return (
    <form
      className="search-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!isEmpty && !loading) onSubmit();
      }}
    >
      <fieldset>
        <legend>
          Genres <span className="hint">pick up to {MAX_GENRES}</span>
        </legend>
        <div className="chips">
          {shownGenres.map(({ name }) => {
            const selected = form.genres.includes(name);
            return (
              <button
                type="button"
                key={name}
                className={`chip ${selected ? "selected" : ""}`}
                aria-pressed={selected}
                disabled={!selected && form.genres.length >= MAX_GENRES}
                onClick={() => toggleGenre(name)}
              >
                {name}
              </button>
            );
          })}
          {genres.length > VISIBLE_GENRES && (
            <button type="button" className="chip chip-more" onClick={() => setShowAllGenres((v) => !v)}>
              {showAllGenres ? "Fewer" : `+${genres.length - VISIBLE_GENRES} more`}
            </button>
          )}
        </div>
      </fieldset>

      <fieldset>
        <legend>Mood</legend>
        <div className="chips">
          {moods.map((mood) => {
            const selected = form.mood === mood;
            return (
              <button
                type="button"
                key={mood}
                className={`chip mood ${selected ? "selected" : ""}`}
                aria-pressed={selected}
                onClick={() => update({ mood: selected ? null : mood })}
              >
                {mood}
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset>
        <legend>Books you loved</legend>
        <LikedBooksInput books={form.likedBooks} onChange={(likedBooks) => update({ likedBooks })} />
      </fieldset>

      <fieldset>
        <legend>
          Anything else? <span className="hint">optional</span>
        </legend>
        <textarea
          rows={3}
          maxLength={1000}
          value={form.description}
          placeholder="e.g. enemies to lovers with a strong heroine, set somewhere cold"
          onChange={(e) => update({ description: e.target.value })}
        />
      </fieldset>

      <button type="submit" className="primary" disabled={isEmpty || loading}>
        {loading ? "Finding books..." : "Find my next book"}
      </button>
      {isEmpty && <p className="form-note">Choose at least one thing above to get started.</p>}
    </form>
  );
}
