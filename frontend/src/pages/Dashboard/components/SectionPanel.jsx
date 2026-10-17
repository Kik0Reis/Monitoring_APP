import { PREVIEW_ROWS } from "../dashboardConfig";

// one compact dashboard section: a clickable header with the count, a short preview and a "View all" button
function SectionPanel({ panel, count, onViewAll, children }) {
  const hasProblem = count > 0;

  return (
    <article className={`dashboard-panel compact ${hasProblem ? `has-${panel.tone}` : ""}`}>
      <button type="button" className="panel-header panel-header-clickable" onClick={onViewAll}>
        <div>
          <p className="panel-eyebrow">{panel.eyebrow}</p>
          <h2>{panel.title}</h2>
        </div>
        <span className={`panel-count-pill ${hasProblem ? panel.tone : "ok"}`}>{count}</span>
      </button>

      {count === 0 ? (
        <div className="dashboard-empty compact-empty">{panel.emptyText}</div>
      ) : (
        <>
          <div className="alert-list compact-list">{children}</div>

          {count > PREVIEW_ROWS && (
            <button type="button" className="panel-view-all" onClick={onViewAll}>
              View all {count} →
            </button>
          )}
        </>
      )}
    </article>
  );
}

export default SectionPanel;
