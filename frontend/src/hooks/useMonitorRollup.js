import { useCallback, useMemo, useState } from "react";

import { monitorApi } from "../services/api";
import { useAutoRefresh } from "./useAutoRefresh";

function indexTree(nodes, map) {
  for (const node of nodes) {
    map.set(`${node.type}-${node.id}`, node);
    indexTree(node.children ?? [], map);
  }
  return map;
}

/**
 * Loads the same Country > Customer > Location > Device > Camera tree the
 * "Monitor > Views" page uses and indexes it by "type-id", so any drill-down
 * page can ask "what's the rolled-up health of THIS node" with
 * rollup.get("location", 12) -- same system_check / has_alerts /
 * detections_count the tree shows, so the two views can never disagree.
 *
 * get() returns undefined until the first load finishes (or if the record
 * isn't in the tree), and RollupIndicator renders nothing in that case.
 * Refreshes on its own 60s timer, like every other live page.
 */
export function useMonitorRollup() {
  const [tree, setTree] = useState([]);

  const loadTree = useCallback(async () => {
    try {
      const data = await monitorApi.tree();
      setTree(data.results ?? []);
    } catch {
      // Best-effort: the page works without the indicators, they just
      // stay hidden (or show the last good value) if this call fails.
    }
  }, []);

  useAutoRefresh(loadTree);

  const index = useMemo(() => indexTree(tree, new Map()), [tree]);

  const get = useCallback(
    (type, id) => index.get(`${type}-${id}`),
    [index],
  );

  return { get };
}

export default useMonitorRollup;
