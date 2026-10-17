// lowercases a status so it matches the css class, an empty status is unknown
function normalize(status) {
  return String(status ?? "unknown").toLowerCase();
}

// small coloured dot for a status (online, offline, unknown, warning, critical, info, active)
export function StatusDot({ status }) {
  return <span className={`status-dot status-dot-${normalize(status)}`} />;
}

// the text shown when a badge is given no label
const DEFAULT_LABELS = {
  online: "Online",
  offline: "Offline",
  unknown: "Unknown",
  warning: "Warning",
  critical: "Critical",
  info: "Info",
  active: "Active",
};

// coloured dot and label for any status, this is the only status badge of the app so the colours stay the same everywhere
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
