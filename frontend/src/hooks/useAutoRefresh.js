import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Runs `loader` immediately, then every `intervalMs` (default 60s) -- this
 * is what keeps pages "live" without the user hitting reload.
 *
 * `loader` should be a stable async function (wrap it in useCallback if it
 * depends on props/state); it fetches data and updates its own state, this
 * hook only decides *when* to call it.
 *
 * Returns lastUpdated (Date|null), refreshing (bool), refresh() (forces an
 * immediate refresh and resets the timer).
 */
export function useAutoRefresh(loader, { intervalMs = 60000, enabled = true } = {}) {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loaderRef = useRef(loader);
  const timerRef = useRef(null);

  // keep the latest loader available without recreating the interval
  // every time the caller passes a new function identity
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  const runLoader = useCallback(async (isBackground) => {
    if (isBackground) {
      setRefreshing(true);
    }

    try {
      await loaderRef.current();
      setLastUpdated(new Date());
    } finally {
      if (isBackground) {
        setRefreshing(false);
      }
    }
  }, []);

  const refresh = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    runLoader(true);

    if (enabled) {
      timerRef.current = setInterval(() => runLoader(true), intervalMs);
    }
  }, [enabled, intervalMs, runLoader]);

  useEffect(() => {
    // deferred so this doesn't setState synchronously mid-commit
    const initialLoad = setTimeout(() => runLoader(false), 0);

    if (enabled) {
      timerRef.current = setInterval(() => runLoader(true), intervalMs);
    }

    return () => {
      clearTimeout(initialLoad);

      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs]);

  return { lastUpdated, refreshing, refresh };
}

export default useAutoRefresh;
