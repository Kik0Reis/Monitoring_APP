import { useState } from "react";

import { getPanel } from "./dashboardConfig";

// state of the "View all" popup: which panel is open and its full list
// panels with loadAll fetch the list when opened, the others reuse the rows of the dashboard payload
export function useDashboardModal({ dashboard, scope, onError }) {
  const [panelKey, setPanelKey] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  // opens the popup of a panel and fills it with the full list
  async function open(key) {
    const panel = getPanel(key);
    setPanelKey(key);

    if (!panel.loadAll) {
      setItems(dashboard?.[panel.preview] ?? []);
      return;
    }

    setLoading(true);
    try {
      const response = await panel.loadAll(scope);
      setItems(response.results ?? []);
    } catch (err) {
      onError(err.message || "Failed to load list.");
    } finally {
      setLoading(false);
    }
  }

  // closes the popup
  function close() {
    setPanelKey(null);
    setItems([]);
  }

  // takes one item out of the open list, used after an alert is resolved
  function removeItem(id) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  return { panel: panelKey ? getPanel(panelKey) : null, items, loading, open, close, removeItem };
}

export default useDashboardModal;
