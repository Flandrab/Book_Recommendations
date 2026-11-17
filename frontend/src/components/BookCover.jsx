import { useState } from "react";

const PALETTES = [
  ["#8c2f39", "#5e1f27"],
  ["#2f5d50", "#1c3a32"],
  ["#3b4a6b", "#232d44"],
  ["#a0662b", "#6b4219"],
  ["#5b3f6b", "#3a2846"],
  ["#4a5a2a", "#2e3a19"],
];

function hash(text) {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) | 0;
  return Math.abs(h);
}

// Real cover from Open Library when we have one, otherwise a generated cloth-bound style cover.
export default function BookCover({ title, authors, coverUrl, size = "normal" }) {
  const [failed, setFailed] = useState(false);

  if (coverUrl && !failed) {
    return (
      <div className={`cover cover-${size}`}>
        <img src={coverUrl} alt={`Cover of ${title}`} loading="lazy" onError={() => setFailed(true)} />
      </div>
    );
  }

  const [light, dark] = PALETTES[hash(title) % PALETTES.length];
  return (
    <div
      className={`cover cover-${size} cover-generated`}
      style={{ background: `linear-gradient(160deg, ${light}, ${dark})` }}
      role="img"
      aria-label={`Cover of ${title}`}
    >
      <span className="cover-title">{title}</span>
      {authors && size !== "small" && <span className="cover-author">{authors.split(",")[0]}</span>}
    </div>
  );
}
