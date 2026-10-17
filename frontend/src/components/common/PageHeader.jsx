// turns a date into "just now", "12s ago" or "3m ago"
function formatRelativeTime(date) {
  if (!date) {
    return null;
  }

  const seconds = Math.round((Date.now() - date.getTime()) / 1000);

  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;

  return `${Math.round(seconds / 60)}m ago`;
}

// header of every page: eyebrow and title on the left, refresh indicator and the buttons given as children on the right
function PageHeader({ eyebrow, title, lastUpdated, refreshing, onRefresh, children }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
      </div>

      <div className="page-header-actions">
        {onRefresh && (
          <button
            type="button"
            className="refresh-indicator"
            onClick={onRefresh}
            disabled={refreshing}
            title="Refresh now"
          >
            <span className={`refresh-dot ${refreshing ? "spinning" : ""}`} />
            {refreshing ? "Refreshing..." : lastUpdated ? `Updated ${formatRelativeTime(lastUpdated)}` : "Refresh"}
          </button>
        )}

        {children}
      </div>
    </header>
  );
}

export default PageHeader;
