import { useEffect, useState } from "react";

// useState that is also saved in the browser's localStorage.
// Storage can be unavailable (private mode, blocked cookies), so every access is guarded.
export function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key);
      return stored !== null ? JSON.parse(stored) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // storage not available - the list still works for this visit
    }
  }, [key, value]);

  return [value, setValue];
}
