
function buildLinks(title, authors, year) {
    const firstAuthor = (authors || "").split(",")[0].trim();
    const query = encodeURIComponent([title, firstAuthor].filter(Boolean).join(" "));
    const links = [
      { label: "Borrow on Open Library", href: `https://openlibrary.org/search?q=${query}` },
      { label: "Find in a library", href: `https://search.worldcat.org/search?q=${query}` },
      { label: "Google Books", href: `https://www.google.com/search?tbm=bks&q=${query}` },
    ];
 
    if (year && year < 1930) {
      links.unshift({
        label: "Free on Project Gutenberg",
        href: `https://www.gutenberg.org/ebooks/search/?query=${encodeURIComponent(title)}`,
      });
    }
    return links;
  }
  
  export default function BookLinks({ title, authors, year }) {
    return (
      <div className="book-links">
        <span className="book-links-label">Get it</span>
        {buildLinks(title, authors, year).map((link) => (
          <a key={link.label} href={link.href} target="_blank" rel="noopener noreferrer">
            {link.label}
          </a>
        ))}
      </div>
    );
  }