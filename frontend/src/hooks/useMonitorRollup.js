import { useCallback, useMemo, useState } from "react";

import { monitorApi } from "../services/api";
import { SCOPE } from "../utils/scope";
import { useAutoRefresh } from "./useAutoRefresh";

// puts every node of the tree in a map, the key is "type-id"
function indexTree(nodes, map) {
  for (const node of nodes) {
    map.set(`${node.type}-${node.id}`, node);
    indexTree(node.children ?? [], map);
  }

  return map;
}

// loads the monitor tree and lets any page ask for the rolled up status of one record
// rollup.get("location", 12) returns the same node the tree page shows, or undefined until it is loaded
export function useMonitorRollup() {
  const [tree, setTree] = useState([]);

  const loadTree = useCallback(async () => {
    try {
      const data = await monitorApi.tree({ scope: SCOPE.ALL });
      setTree(data.results ?? []);
    } catch {
      // the pages work without the indicators, they stay hidden when this fails
    }
  }, []);

  useAutoRefresh(loadTree);

  const index = useMemo(() => indexTree(tree, new Map()), [tree]);
  const get = useCallback((type, id) => index.get(`${type}-${id}`), [index]);

  return { get };
}

export default useMonitorRollup;
