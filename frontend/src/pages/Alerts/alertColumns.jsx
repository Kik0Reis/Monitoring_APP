import StatusBadge from "../../components/common/StatusBadge";
import { severityTone } from "../../utils/alertLabels";
import { formatConfidence } from "./alertRows";

// the tabs of the page, to add a tab put it here and give it columns in COLUMNS
export const TABS = [
  {
    key: "offline",
    label: "Offline",
    description: "Devices and cameras that are currently unreachable.",
  },
  {
    key: "error",
    label: "Errors",
    description:
      "Free-form messages actually sent over MQTT (e.g. low threshold). These clear on their own after a while (configurable in Settings).",
  },
  {
    key: "detections",
    label: "Detections",
    description: "Real-world events reported by cameras.",
  },
];

// sort of a tab that was never sorted: newest first
export const DEFAULT_SORT = { key: "date", dir: "desc" };

// columns that start sorted from the newest or the biggest
export const DESCENDING_FIRST = ["date", "time", "confidence"];

// column definitions
// filter: text, select, multiselect, date or time (none = no filter)
// value(row): the value used to filter and to sort, sortValue(row) overrides it for sorting
// render(row): what the cell shows
const DATE_COLUMN = {
  key: "date",
  header: "Date",
  filter: "date",
  sortValue: (row) => (row.dateKey ? `${row.dateKey} ${row.timeKey}` : ""),
  render: (row) => row.dateLabel,
};

const TIME_COLUMN = {
  key: "time",
  header: "Time",
  filter: "time",
  sortValue: (row) => row.timeKey,
  render: (row) => <time>{row.timeLabel}</time>,
};

const LOCATION_COLUMN = {
  key: "location",
  header: "Location",
  filter: "text",
  value: (row) => row.location,
  render: (row) => row.location || "—",
};

const TYPE_COLUMN = {
  key: "type",
  header: "Type",
  filter: "select",
  value: (row) => row.typeLabel,
  render: (row) => row.typeLabel,
};

const STATUS_COLUMN = {
  key: "status",
  header: "Status",
  filter: "select",
  value: (row) => row.statusValue,
  render: (row) =>
    row.active === false ? (
      <span className="alert-row-resolved-tag">Resolved</span>
    ) : (
      <StatusBadge status={severityTone(row.severity)} label="Active" />
    ),
};

// the camera or device the alert is about, with the device under the camera name
function sourceColumn(header) {
  return {
    key: "source",
    header,
    filter: "text",
    value: (row) => row.source,
    render: (row) => (
      <>
        <span className="entity-name">{row.source || "—"}</span>
        {row.camera_name && row.device_name && <span className="entity-subtext">{row.device_name}</span>}
      </>
    ),
  };
}

// the device the alert is about
const DEVICE_COLUMN = {
  key: "device",
  header: "Device",
  filter: "text",
  value: (row) => row.deviceName,
  render: (row) => <span className="entity-name">{row.deviceName || "—"}</span>,
};

const MESSAGE_COLUMN = {
  key: "message",
  header: "Message",
  filter: "text",
  value: (row) => row.message ?? "",
  render: (row) => <span className="alerts-message">{row.message ?? "—"}</span>,
};

// the columns of each tab
export const COLUMNS = {
  offline: [DATE_COLUMN, TIME_COLUMN, sourceColumn("Camera / Device"), LOCATION_COLUMN, TYPE_COLUMN, STATUS_COLUMN],
  error: [DATE_COLUMN, TIME_COLUMN, DEVICE_COLUMN, LOCATION_COLUMN, TYPE_COLUMN, MESSAGE_COLUMN, STATUS_COLUMN],
  detections: [
    DATE_COLUMN,
    TIME_COLUMN,
    sourceColumn("Camera"),
    LOCATION_COLUMN,
    {
      key: "detected",
      header: "Detected",
      filter: "multiselect",
      value: (row) => row.detectedValue,
      render: (row) => (row.detectedValue ? <span className="alerts-chip">{row.detectedValue}</span> : "—"),
    },
    {
      key: "action",
      header: "Action",
      filter: "multiselect",
      value: (row) => row.actionValue,
      render: (row) => row.actionValue || "—",
    },
    {
      key: "confidence",
      header: "Confidence",
      sortValue: (row) => row.confidenceValue,
      render: (row) => formatConfidence(row.confidenceValue),
    },
  ],
};
