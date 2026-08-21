/**
 * Renders a small colored dot + label for any status value
 * (device status, camera status, location health, alert severity...).
 *
 * Having exactly one implementation of this (instead of a slightly
 * different status-dot per page) is what keeps status colors/sizes
 * consistent across the whole app.
 */
function normalize(status) {
  return String(status ?? "unknown").toLowerCase();
}

export function StatusDot({ status }) {
  return <span className={`status-dot status-dot-${normalize(status)}`} />;
}

const DEFAULT_LABELS = {
  online: "Online",
  offline: "Offline",
  unknown: "Unknown",
  warning: "Warning",
  critical: "Critical",
  info: "Info",
  active: "Active",
  inactive: "Inactive",
};

function StatusBadge({ status, label }) {
  const normalized = normalize(status);

  return (
    <span className={`status-badge status-badge-${normalized}`}>
      <StatusDot status={normalized} />
      {label ?? DEFAULT_LABELS[normalized] ?? status ?? "Unknown"}
    </span>
  );
}

export default StatusBadge;
