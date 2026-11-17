import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useLocalStorage } from "./useLocalStorage.js";

const EMPTY = { readingList: [], readingLog: [], goal: 0 };

export function todayISO() {
  return new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

function newId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

// The reading list, reading log and yearly goal.
// Signed out: kept in this browser (localStorage). Signed in: kept on the server, per user.
// Changes show instantly and are saved in the background; if a save fails, the data is reloaded.
export function useUserData(user, onSessionExpired) {
  const [guestList, setGuestList] = useLocalStorage("booktag:reading-list", []);
  const [guestLog, setGuestLog] = useLocalStorage("booktag:reading-log", []);
  const [guestGoal, setGuestGoal] = useLocalStorage("booktag:yearly-goal", 0);

  const [server, setServer] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [syncError, setSyncError] = useState(null);
  const goalTimer = useRef(null);

  const signedIn = Boolean(user);
  const userId = user?.id;

  const reload = useCallback(() => {
    if (!userId) return Promise.resolve();
    setLoading(true);
    return api.me
      .data()
      .then((data) => setServer(data))
      .catch((err) => {
        if (err.status === 401) onSessionExpired?.();
        else setSyncError("Couldn't load your saved books. Is the server running?");
      })
      .finally(() => setLoading(false));
  }, [userId, onSessionExpired]);

  useEffect(() => {
    if (userId) reload();
    else setServer(EMPTY);
  }, [userId, reload]);

  // Run a save in the background; on failure show a message and reload the real data.
  const sync = (promise) =>
    promise.catch((err) => {
      if (err.status === 401) {
        onSessionExpired?.();
        return;
      }
      setSyncError(err.message || "Couldn't save your change.");
      reload();
    });

  const readingList = signedIn ? server.readingList : guestList;
  const readingLog = signedIn ? server.readingLog : guestLog;
  const goal = signedIn ? server.goal : guestGoal;

  const updateList = (fn) =>
    signedIn ? setServer((s) => ({ ...s, readingList: fn(s.readingList) })) : setGuestList(fn);
  const updateLog = (fn) => (signedIn ? setServer((s) => ({ ...s, readingLog: fn(s.readingLog) })) : setGuestLog(fn));

  // ----- reading list -----
  const savedIds = new Set(readingList.map((b) => b.id));

  const toggleSave = (book) => {
    if (savedIds.has(book.id)) {
      updateList((list) => list.filter((b) => b.id !== book.id));
      if (signedIn) sync(api.me.unsave(book.id));
    } else {
      const item = {
        id: book.id,
        title: book.title,
        authors: book.authors || "",
        year: book.year ?? null,
        cover_url: book.cover_url ?? null,
        savedAt: Date.now(),
      };
      updateList((list) => [item, ...list]);
      if (signedIn) sync(api.me.save(item));
    }
  };

  const removeFromList = (bookId) => {
    updateList((list) => list.filter((b) => b.id !== bookId));
    if (signedIn) sync(api.me.unsave(bookId));
  };

  const clearList = () => {
    updateList(() => []);
    if (signedIn) sync(api.me.clearList());
  };

  // ----- reading log -----
  const loggedIds = new Set(readingLog.map((e) => e.bookId).filter((id) => id !== null && id !== undefined));

  const updateLogEntry = (id, changes) => {
    updateLog((log) => log.map((e) => (e.id === id ? { ...e, ...changes } : e)));
    if (signedIn) sync(api.me.updateLog(id, changes));
  };

  const addLogEntry = (entry) => {
    const full = {
      id: newId(),
      bookId: null,
      authors: "",
      year: null,
      cover_url: null,
      rating: 0,
      notes: "",
      ...entry,
    };
    updateLog((log) => [full, ...log]);
    const saved = signedIn ? api.me.addLog(full) : Promise.resolve(full);
    const savedOk = sync(saved.then(() => true));

    // Books picked from the catalogue get their cover filled in once the entry is saved.
    if (full.bookId !== null && full.bookId !== undefined && !full.cover_url) {
      savedOk
        .then((ok) => (ok ? api.book(full.bookId) : null))
        .then((details) => {
          if (details?.cover_url) updateLogEntry(full.id, { cover_url: details.cover_url });
        })
        .catch(() => {});
    }
  };

  const removeLogEntry = (id) => {
    updateLog((log) => log.filter((e) => e.id !== id));
    if (signedIn) sync(api.me.removeLog(id));
  };

  const toggleLogged = (book) => {
    if (loggedIds.has(book.id)) {
      readingLog.filter((e) => e.bookId === book.id).forEach((e) => removeLogEntry(e.id));
    } else {
      addLogEntry({
        bookId: book.id,
        title: book.title,
        authors: book.authors || "",
        year: book.year ?? null,
        cover_url: book.cover_url ?? null,
        finishedOn: todayISO(),
      });
    }
  };

  // ----- yearly goal (saved to the server half a second after you stop typing) -----
  const setGoal = (value) => {
    if (!signedIn) {
      setGuestGoal(value);
      return;
    }
    setServer((s) => ({ ...s, goal: value }));
    clearTimeout(goalTimer.current);
    goalTimer.current = setTimeout(() => sync(api.me.setGoal(value)), 500);
  };

  // ----- moving guest data into an account -----
  const hasGuestData = guestList.length > 0 || guestLog.length > 0 || guestGoal > 0;

  // Call right after signing in: copies anything saved as a guest into the account, then clears it here.
  const importGuestData = async () => {
    if (!hasGuestData) return;
    await api.me.importGuest({ readingList: guestList, readingLog: guestLog, goal: guestGoal });
    setGuestList([]);
    setGuestLog([]);
    setGuestGoal(0);
  };

  return {
    readingList,
    readingLog,
    goal,
    loading,
    savedIds,
    loggedIds,
    syncError,
    clearSyncError: () => setSyncError(null),
    toggleSave,
    removeFromList,
    clearList,
    addLogEntry,
    updateLogEntry,
    removeLogEntry,
    toggleLogged,
    setGoal,
    hasGuestData,
    importGuestData,
  };
}