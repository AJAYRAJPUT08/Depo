import { useEffect, useState } from "react";

/** Re-renders every second with the current Date. */
export function useClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return now;
}

/** Simple `useEffect`-based polling helper: calls `fn` immediately, then every `intervalMs`. */
export function usePolling(fn, intervalMs, deps = []) {
  useEffect(() => {
    let cancelled = false;
    const run = () => {
      if (!cancelled) fn();
    };
    run();
    const id = setInterval(run, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
