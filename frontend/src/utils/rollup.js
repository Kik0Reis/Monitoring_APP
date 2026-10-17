// the colour of the status dot of a tree node: red when something is offline, amber for an error alert, else green
export function rollupTone(node) {
  if (node.system_check === "red") return "critical";
  if (node.has_alerts) return "warning";
  return "ok";
}

// the tooltip text of each colour
export const ROLLUP_LABELS = {
  critical: "Offline somewhere in this branch",
  warning: "Active error alert in this branch",
  ok: "All clear",
};
