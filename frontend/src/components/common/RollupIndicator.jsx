import "./rollup-indicator.css";

/**
 * The tree view's per-node signals, for drill-down pages: one status dot
 * (red = something in this branch is offline, amber = active error alert in
 * this branch, green = all clear -- red wins over amber) plus the recent
 * detections count. `node` comes from useMonitorRollup().get(type, id).
 *
 * showLabel adds a sentence next to the dot -- used in page headers; table
 * rows just show the dot + count to stay compact.
 */
function rollupTone(node) {
  if (node.system_check === "red") return "critical";
  if (node.has_alerts) return "warning";
  return "ok";
}

const LABELS = {
  critical: "Offline somewhere in this branch",
  warning: "Active error alert in this branch",
  ok: "All clear",
};

function RollupIndicator({ node, showLabel = false }) {
  if (!node) return null;

  const tone = rollupTone(node);

  return (
    <span className="rollup-indicator">
      <span className="rollup-status" title={LABELS[tone]}>
        <span className={`rollup-dot rollup-dot-${tone}`} />
        {showLabel && <span className={`rollup-label rollup-label-${tone}`}>{LABELS[tone]}</span>}
      </span>

      {node.detections_count > 0 && (
        <span className="rollup-detections" title="Recent detections">
          {node.detections_count}
          {showLabel && <span className="rollup-detections-text"> recent detections</span>}
        </span>
      )}
    </span>
  );
}

export default RollupIndicator;
