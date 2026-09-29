import "./list-modal.css";

/**
 * Centered popup used by the dashboard's compact panels: click a panel's
 * counter/"View all" and this opens with the full list, instead of the
 * panel itself growing and pushing everything else down the page.
 */
function ListModal({ eyebrow, title, count, onClose, children, footer }) {
  return (
    <div className="list-modal-overlay" onMouseDown={onClose}>
      <div className="list-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="list-modal-header">
          <div>
            {eyebrow && <p className="list-modal-eyebrow">{eyebrow}</p>}
            <h2>
              {title}
              {typeof count === "number" && (
                <span className="list-modal-count">{count}</span>
              )}
            </h2>
          </div>

          <button
            type="button"
            className="list-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="list-modal-body">{children}</div>

        {footer && <div className="list-modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

export default ListModal;
