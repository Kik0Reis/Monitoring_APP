import { Check, Eye, Pencil, Trash2 } from "lucide-react";

// the buttons at the end of a list row: approve (only while the record waits for review), view, edit and delete
// resource is what useCrudResource returned for the page, withView false hides the view button
function RowActions({ item, resource, withView = true }) {
  return (
    <>
      {item.pending_review && (
        <button
          className="icon-button"
          aria-label={`Approve ${item.name}`}
          title="Approve"
          onClick={() => resource.handleApprove(item)}
        >
          <Check size={16} />
        </button>
      )}
      {withView && (
        <button className="icon-button" aria-label={`View ${item.name}`} onClick={() => resource.openView(item)}>
          <Eye size={16} />
        </button>
      )}
      <button className="icon-button" aria-label={`Edit ${item.name}`} onClick={() => resource.openEdit(item)}>
        <Pencil size={16} />
      </button>
      <button
        className="icon-button danger"
        aria-label={`Delete ${item.name}`}
        onClick={() => resource.handleDelete(item)}
      >
        <Trash2 size={16} />
      </button>
    </>
  );
}

export default RowActions;
