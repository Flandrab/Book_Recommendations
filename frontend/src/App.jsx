import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import ReadingList from "./components/ReadingList.jsx";
import { useHashRoute } from "./hooks/useHashRoute.js";
import { useUserData } from "./hooks/useUserData.js";
import AccountPage from "./pages/AccountPage.jsx";
import BookPage from "./pages/BookPage.jsx";
import DiscoverPage from "./pages/DiscoverPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import ReadingLogPage from "./pages/ReadingLogPage.jsx";
import "./pages/account.css";

const NAV = [
  { path: "/", label: "Home" },
  { path: "/discover", label: "Discover" },
  { path: "/log", label: "Reading log" },
];

export default function App() {
  const route = useHashRoute();

  const [options, setOptions] = useState(null);
  const [llmAvailable, setLlmAvailable] = useState(false);
  const [bookCount, setBookCount] = useState(null);
  const [backendError, setBackendError] = useState(null);

  const [user, setUser] = useState(null);
  const [notice, setNotice] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleSessionExpired = useCallback(() => {
    setUser(null);
    setNotice("You were signed out. Sign in again to see your saved books.");
  }, []);

  const data = useUserData(user, handleSessionExpired);

  useEffect(() => {
    api
      .options()
      .then(setOptions)
      .catch(() => setBackendError("Can't reach the server. Is the backend running on port 8000?"));
    api
      .health()
      .then((h) => {
        setLlmAvailable(h.llm_available);
        setBookCount(h.books);
      })
      .catch(() => setLlmAvailable(false));
    api.auth
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  const handleSignedIn = async (signedInUser) => {
    try {
      await data.importGuestData();
    } catch {
      setNotice("Signed in, but the books saved on this device couldn't be moved to your account.");
    }
    setUser(signedInUser);
    window.location.hash = "#/";
  };

  const handleSignOut = async () => {
    try {
      await api.auth.logout();
    } catch {
      // signed out locally either way
    }
    setUser(null);
    window.location.hash = "#/";
  };

  const bookMatch = route.match(/^\/book\/(\d+)$/);
  const bookId = bookMatch ? Number(bookMatch[1]) : null;
  const knownPages = [...NAV.map((n) => n.path), "/account"];
  const page = bookId !== null ? "/book" : knownPages.includes(route) ? route : "/";

  const listWithReadState = data.readingList.map((b) => ({ ...b, read: data.loggedIds.has(b.id) }));
  const bannerMessage = data.syncError || notice;

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          <img src="/favicon.svg" alt="" width="28" height="28" />
          BookTag
        </a>
        <nav className="main-nav" aria-label="Main">
          {NAV.map((item) => (
            <a key={item.path} href={`#${item.path}`} aria-current={page === item.path ? "page" : undefined}>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="topbar-actions">
          <button type="button" className="list-button" onClick={() => setDrawerOpen(true)}>
            Reading list
            {data.readingList.length > 0 && <span className="count">{data.readingList.length}</span>}
          </button>
          {user ? (
            <a
              className="account-button"
              href="#/account"
              aria-current={page === "/account" ? "page" : undefined}
              title="Your account"
            >
              <span className="mini-avatar" aria-hidden="true">
                {user.name.slice(0, 1).toUpperCase()}
              </span>
              <span className="account-name">{user.name.split(" ")[0]}</span>
            </a>
          ) : (
            <a className="account-button signed-out" href="#/account">
              Sign in
            </a>
          )}
        </div>
      </header>

      {page === "/" && (
        <HomePage
          readingList={data.readingList}
          readingLog={data.readingLog}
          goal={data.goal}
          bookCount={bookCount}
          onOpenList={() => setDrawerOpen(true)}
        />
      )}

      {/* Discover stays mounted so your results are still there when you come back to it. */}
      <div hidden={page !== "/discover"}>
        <DiscoverPage
          options={options}
          llmAvailable={llmAvailable}
          bookCount={bookCount}
          backendError={backendError}
          savedIds={data.savedIds}
          onToggleSave={data.toggleSave}
          loggedIds={data.loggedIds}
          onToggleLogged={data.toggleLogged}
        />
      </div>

      {page === "/book" && (
        <BookPage
          key={bookId}
          bookId={bookId}
          savedIds={data.savedIds}
          onToggleSave={data.toggleSave}
          loggedIds={data.loggedIds}
          onToggleLogged={data.toggleLogged}
        />
      )}

      {page === "/log" && (
        <ReadingLogPage
          readingLog={data.readingLog}
          goal={data.goal}
          onGoalChange={data.setGoal}
          onAdd={data.addLogEntry}
          onUpdate={data.updateLogEntry}
          onRemove={data.removeLogEntry}
        />
      )}

      {page === "/account" && (
        <AccountPage
          user={user}
          readingList={data.readingList}
          readingLog={data.readingLog}
          hasGuestData={data.hasGuestData}
          onSignedIn={handleSignedIn}
          onSignOut={handleSignOut}
        />
      )}

      <footer className="footer">
        BookTag · Covers from <a href="https://openlibrary.org">Open Library</a> · Built by Flandra Bytyqi
      </footer>

      <ReadingList
        open={drawerOpen}
        books={listWithReadState}
        onClose={() => setDrawerOpen(false)}
        onRemove={data.removeFromList}
        onToggleRead={(id) => {
          const book = data.readingList.find((b) => b.id === id);
          if (book) data.toggleLogged(book);
        }}
        onClear={() => {
          if (window.confirm("Remove every book from your reading list?")) data.clearList();
        }}
      />

      {bannerMessage && (
        <div className="sync-banner" role="alert">
          <span>{bannerMessage}</span>
          <button
            type="button"
            onClick={() => {
              data.clearSyncError();
              setNotice(null);
            }}
          >
            OK
          </button>
        </div>
      )}
    </div>
  );
}