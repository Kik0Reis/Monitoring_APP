import { X } from "lucide-react";

import { StatusDot } from "../../../components/common/StatusBadge";
import { alertTypeLabel, severityTone } from "../../../utils/alertLabels";
import { formatTime } from "../../../utils/formatTimestamp";

// one alert or detection row, used in the panel preview and in the popup
function AlertRow({ item, onOpen, onResolve, showDot = true }) {
  const source = item.camera_name ?? item.device_name;
  const subtitle = item.message
    ? `${source}${item.location_name ? ` · ${item.location_name}` : ""}`
    : item.location_name ?? "—";

  return (
    <div className="alert-row" onClick={() => onOpen(item)}>
      <div className="alert-row-main">
        {showDot && <StatusDot status={severityTone(item.severity)} />}
        <div>
          <strong>{item.message ?? source}</strong>
          <span>{subtitle}</span>
        </div>
      </div>

      <div className="alert-row-side">
        <div className="alert-row-meta">
          <span>{alertTypeLabel(item.alert_type ?? item.type)}</span>
          <time>{formatTime(item.created_at, false)}</time>
        </div>

        <button
          type="button"
          className="alert-row-resolve"
          title="Mark as resolved"
          onClick={(event) => {
            event.stopPropagation();
            onResolve(item);
          }}
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

export default AlertRow;
