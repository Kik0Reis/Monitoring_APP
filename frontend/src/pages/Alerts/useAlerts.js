import { useCallback, useState } from "react";

import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { detectionsApi, problemsApi } from "../../services/api";

const LIST_LIMIT = 200;

// loads the offline problems, the error problems and the detections of the page
// showHistory also loads the resolved problems, it reloads when it or the tab changes
export function useAlerts(activeTab) {
  const [showHistory, setShowHistory] = useState(false);
  const [itemsByTab, setItemsByTab] = useState({ offline: [], error: [], detections: [] });
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");

      const query = `active_only=${!showHistory}&limit=${LIST_LIMIT}`;
      const [offline, errors, detections] = await Promise.all([
        problemsApi.list(`?category=offline&${query}`),
        problemsApi.list(`?category=error&${query}`),
        detectionsApi.list(`?limit=${LIST_LIMIT}`),
      ]);

      setItemsByTab({
        offline: offline.results ?? [],
        error: errors.results ?? [],
        detections: detections.results ?? [],
      });
    } catch (err) {
      setError(err.message || "Failed to load alerts.");
    }
  }, [showHistory]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(load, { reloadKey: `${showHistory}-${activeTab}` });

  return { itemsByTab, error, setError, showHistory, setShowHistory, lastUpdated, refreshing, refresh };
}

export default useAlerts;
