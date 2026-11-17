import { useState } from "react";
import { api } from "../api.js";
import "./account.css";

function SignedIn({ user, readingList, readingLog, onSignOut }) {
  const [busy, setBusy] = useState(false);
  const year = String(new Date().getFullYear());
  const readThisYear = readingLog.filter((e) => e.finishedOn?.startsWith(year)).length;

  return (
    <main className="account-page">
      <section className="account-card">
        <div className="avatar" aria-hidden="true">
          {user.name.slice(0, 1).toUpperCase()}
        </div>
        <h1>{user.name}</h1>
        <p className="muted">{user.email}</p>

        <dl className="account-stats">
          <div>
            <dt>On your reading list</dt>
            <dd>{readingList.length}</dd>
          </div>
          <div>
            <dt>Books logged</dt>
            <dd>{readingLog.length}</dd>
          </div>
          <div>
            <dt>Read in {year}</dt>
            <dd>{readThisYear}</dd>
          </div>
        </dl>

        <p className="hint">Your reading list, reading log and goal are saved to your account, on any device.</p>

        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onSignOut();
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Signing out..." : "Sign out"}
        </button>
      </section>
    </main>
  );
}

export default function AccountPage({ user, readingList, readingLog, hasGuestData, onSignedIn, onSignOut }) {
  const [mode, setMode] = useState("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) {
    return <SignedIn user={user} readingList={readingList} readingLog={readingLog} onSignOut={onSignOut} />;
  }

  const signingUp = mode === "signup";

  const submit = async (event) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const signedIn = signingUp
        ? await api.auth.signup(email.trim(), name.trim(), password)
        : await api.auth.login(email.trim(), password);
      setPassword("");
      await onSignedIn(signedIn);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (next) => {
    setMode(next);
    setError(null);
  };

  return (
    <main className="account-page">
      <section className="account-card">
        <h1>{signingUp ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">
          {signingUp
            ? "Keep your reading list and reading log safe, and use them on any device."
            : "Sign in to see your reading list and reading log."}
        </p>

        <div className="mode-switch" role="tablist" aria-label="Sign in or create an account">
          <button type="button" role="tab" aria-selected={!signingUp} onClick={() => switchMode("signin")}>
            Sign in
          </button>
          <button type="button" role="tab" aria-selected={signingUp} onClick={() => switchMode("signup")}>
            Create account
          </button>
        </div>

        <form className="account-form" onSubmit={submit}>
          {signingUp && (
            <label>
              Name
              <input
                type="text"
                autoComplete="name"
                required
                maxLength={60}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={signingUp ? "new-password" : "current-password"}
              required
              minLength={signingUp ? 8 : undefined}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {signingUp && <span className="hint">At least 8 characters.</span>}
          </label>

          {error && <p className="alert">{error}</p>}

          <button type="submit" className="primary" disabled={busy}>
            {busy ? "One moment..." : signingUp ? "Create account" : "Sign in"}
          </button>
        </form>

        {hasGuestData && (
          <p className="hint guest-note">
            The books you've saved on this device will be moved into your account when you sign in.
          </p>
        )}
      </section>
    </main>
  );
}