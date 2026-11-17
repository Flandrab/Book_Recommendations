
export default function StarRating({ value = 0, onChange, size = "normal" }) {
    const stars = [1, 2, 3, 4, 5];
  
    if (!onChange) {
      if (!value) return null;
      return (
        <span className={`stars stars-${size}`} aria-label={`${value} out of 5 stars`}>
          {stars.map((n) => (
            <span key={n} className={n <= value ? "on" : ""} aria-hidden="true">
              ★
            </span>
          ))}
        </span>
      );
    }
  
    return (
      <span className={`stars stars-${size} stars-input`} role="radiogroup" aria-label="Rating">
        {stars.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            className={n <= value ? "on" : ""}
            onClick={() => onChange(value === n ? 0 : n)}
          >
            ★
          </button>
        ))}
      </span>
    );
  }