import { ROLLUP_LABELS, rollupTone } from "../../utils/rollup";
import "./rollup-indicator.css";

// the status dot and the recent detections count of a tree node, shown on the drill down pages
// node comes from useMonitorRollup().get(type, id), showLabel adds a sentence next to the dot (used in page headers)
function RollupIndicator({ node, showLabel = false }) {
  if (!node) return null;

  const tone = rollupTone(node);

  return (
    <span className="rollup-indicator">
      <span className="rollup-status" title={ROLLUP_LABELS[tone]}>
        <span className={`rollup-dot rollup-dot-${tone}`} />
        {showLabel && <span className={`rollup-label rollup-label-${tone}`}>{ROLLUP_LABELS[tone]}</span>}
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
