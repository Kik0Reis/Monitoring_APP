import { useCallback, useEffect, useRef, useState } from "react";

// runs the loader once and then every intervalMs (60 seconds by default) so a page stays up to date
// when reloadKey changes (for example a filter), it reloads right away instead of waiting for the timer
// returns lastUpdated, refreshing and refresh() that reloads right now and restarts the timer
export function useAutoRefresh(loader, { intervalMs = 60000, enabled = true, reloadKey } = {}) {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loaderRef = useRef(loader);
  const timerRef = useRef(null);

  // always call the newest loader without restarting the timer
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  // calls the loader, background loads show the refreshing state
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

  // reloads now and restarts the timer
  const refresh = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    runLoader(true);

    if (enabled) {
      timerRef.current = setInterval(() => runLoader(true), intervalMs);
    }
  }, [enabled, intervalMs, runLoader]);

  // reload when the reload key changes, the first render is skipped because the first load already runs below
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  useEffect(() => {
    // the first load is delayed so it does not set state while the page is rendering
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
