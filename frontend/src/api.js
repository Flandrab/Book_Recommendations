// Small wrapper around the backend API. In development Vite proxies /api to FastAPI;
// in production the frontend is served by the same server, so relative URLs work.
const BASE_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send the sign-in cookie
    ...options,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        message = body.detail[0].msg.replace(/^Value error, /, "");
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(message, response.status);
  }
  return response.json();
}

const json = (method, body) => ({ method, body: JSON.stringify(body) });

export const api = {
  health: () => request("/api/health"),
  options: () => request("/api/options"),
  book: (id) => request(`/api/books/${id}`),
  similarBooks: (id) => request(`/api/books/${id}/similar?limit=6`),
  ratings: (id) => request(`/api/books/${id}/ratings`),
  searchBooks: (query, signal) =>
    request(`/api/books/search?q=${encodeURIComponent(query)}&limit=6`, { signal }),
  recommend: (query) => request("/api/recommend", json("POST", query)),
  explain: (query, bookIds) => request("/api/explain", json("POST", { ...query, book_ids: bookIds })),

  auth: {
    me: () => request("/api/auth/me"),
    signup: (email, name, password) => request("/api/auth/signup", json("POST", { email, name, password })),
    login: (email, password) => request("/api/auth/login", json("POST", { email, password })),
    logout: () => request("/api/auth/logout", { method: "POST" }),
  },

  me: {
    data: () => request("/api/me/data"),
    save: (book) => request(`/api/me/reading-list/${book.id}`, json("PUT", book)),
    unsave: (bookId) => request(`/api/me/reading-list/${bookId}`, { method: "DELETE" }),
    clearList: () => request("/api/me/reading-list", { method: "DELETE" }),
    addLog: (entry) => request("/api/me/reading-log", json("POST", entry)),
    updateLog: (id, changes) => request(`/api/me/reading-log/${encodeURIComponent(id)}`, json("PATCH", changes)),
    removeLog: (id) => request(`/api/me/reading-log/${encodeURIComponent(id)}`, { method: "DELETE" }),
    setGoal: (goal) => request("/api/me/goal", json("PUT", { goal })),
    importGuest: (data) => request("/api/me/import", json("POST", data)),
  },
};