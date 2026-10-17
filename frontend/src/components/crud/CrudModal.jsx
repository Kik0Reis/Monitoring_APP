import "./crud-modal.css";

// small title above the heading for each mode
const MODE_LABELS = {
  create: "Create",
  edit: "Edit",
  view: "Details",
};

// popup frame with the header, the body and the cancel and save buttons, the save button is hidden in view mode
function CrudModal({ mode, title, children, onClose, onSubmit, submitLabel, loading = false }) {
  const isView = mode === "view";

  return (
    <div className="crud-modal-overlay" onMouseDown={onClose}>
      <div className="crud-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="crud-modal-header">
          <div>
            <p className="crud-modal-eyebrow">{MODE_LABELS[mode] ?? "Details"}</p>
            <h2>{title}</h2>
          </div>

          <button type="button" className="crud-modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="crud-modal-body">{children}</div>

        <div className="crud-modal-footer">
          <button type="button" className="crud-modal-cancel" onClick={onClose}>
            {isView ? "Close" : "Cancel"}
          </button>

          {!isView && (
            <button type="button" className="primary-button" onClick={onSubmit} disabled={loading}>
              {loading ? "Saving..." : submitLabel || "Save"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default CrudModal;
