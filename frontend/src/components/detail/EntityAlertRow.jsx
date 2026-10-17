import { X } from "lucide-react";

import { formatTimestamp } from "../../utils/formatTimestamp";
import StatusBadge from "../common/StatusBadge";

// one alert of a device or camera with its time and a button to resolve it
function EntityAlertRow({ alert, onResolve, label = "Active" }) {
  return (
    <div className="entity-alert-row active">
      <div className="entity-alert-main">
        <StatusBadge status="warning" label={label} />
        <span>{alert.message}</span>
      </div>

      <div className="entity-alert-row-end">
        <time>{formatTimestamp(alert.created_at)}</time>
        <button type="button" className="alert-row-resolve" title="Mark as resolved" onClick={() => onResolve(alert)}>
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

export default EntityAlertRow;
