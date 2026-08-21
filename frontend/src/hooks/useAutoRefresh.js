import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Runs `loader` immediately, then again every `intervalMs`.
 *
 * This is what keeps the whole app "live": every page that shows data
 * pulled from the API uses this hook so it refreshes itself automatically
 * (default: every 60 seconds) without the user needing to hit reload.
 *
 * `loader` should be a stable-ish async function (wrap it in useCallback
 * in the caller if it depends on props/state) that fetches new data and
 * updates its own state. This hook only cares about *when* to call it.
 *
 * Returns:
 *   - lastUpdated: Date | null, when the loader last completed successfully
 *   - refreshing: true while a background (non-initial) refresh is in flight
 *   - refresh(): trigger an immediate refresh, resetting the interval timer
 */
export function useAutoRefresh(loader, { intervalMs = 60000, enabled = true } = {}) {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loaderRef = useRef(loader);
  const timerRef = useRef(null);

  // Keep the latest loader available to the interval without having to
  // recreate the interval every time the caller's loader identity changes.
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
    // Defer the very first load out of the effect body itself so this
    // doesn't synchronously trigger a setState while React is still
    // committing this effect's own render pass.
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
