import { useCallback, useState } from "react";

import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { useScope } from "../../hooks/useScope";
import { dashboardApi } from "../../services/api";

// loads the dashboard payload for the chosen scope and keeps it fresh
// changing the scope reloads right away
export function useDashboard() {
  const [scope, setScope] = useScope();
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      setDashboard(await dashboardApi.get({ scope }));
    } catch (err) {
      setError(err.message || "Failed to load dashboard.");
    }
  }, [scope]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(load, { reloadKey: scope });

  return { dashboard, error, setError, scope, setScope, lastUpdated, refreshing, refresh };
}

export default useDashboard;
