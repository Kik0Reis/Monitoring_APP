import { useCallback, useRef, useState } from "react";

import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { monitorApi } from "../../services/api";
import { collectAllKeys, initialExpandedKeys, nodeKey } from "./treeUtils";

// loads the monitor tree for a scope and keeps which branches are open
// the open branches are only set on the first load, so changing the scope or refreshing never closes what the person opened
export function useMonitorTree(scope) {
  const [tree, setTree] = useState(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(new Set());
  const loadedOnce = useRef(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const data = await monitorApi.tree({ scope });
      const results = data.results ?? [];
      setTree(results);

      if (!loadedOnce.current) {
        loadedOnce.current = true;
        setExpanded(initialExpandedKeys(results));
      }
    } catch (err) {
      setError(err.message || "Failed to load the monitor tree.");
    }
  }, [scope]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(load, { reloadKey: scope });

  // opens or closes one branch
  function toggleNode(node) {
    setExpanded((current) => {
      const next = new Set(current);
      const key = nodeKey(node);

      if (next.has(key)) next.delete(key);
      else next.add(key);

      return next;
    });
  }

  // opens every branch
  function expandAll() {
    if (tree) setExpanded(collectAllKeys(tree));
  }

  // closes every branch, only the countries stay open
  function collapseAll() {
    if (tree) setExpanded(new Set(tree.map(nodeKey)));
  }

  return { tree, error, expanded, toggleNode, expandAll, collapseAll, lastUpdated, refreshing, refresh };
}

export default useMonitorTree;
