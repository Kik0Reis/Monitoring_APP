import { formatTimestamp } from "../../utils/formatTimestamp";
import DetailRow from "./DetailRow";
import StatusBadge from "./StatusBadge";

// status values that mean the component is fine
const HEALTHY_STATUS_VALUES = new Set(["up", "online", "healthy", "true"]);

// returns the badge colour of a component status
function componentStatusColor(status) {
  return HEALTHY_STATUS_VALUES.has(String(status).toLowerCase()) ? "online" : "critical";
}

// turns a key like "last_error" into "last error"
function readableKey(key) {
  return key.replace(/_/g, " ");
}

// returns the text of one camera entry: its stage, or healthy / unhealthy
function cameraState(cameraData) {
  if (cameraData?.stage) return cameraData.stage;
  if (cameraData?.healthy === true) return "healthy";
  if (cameraData?.healthy === false) return "unhealthy";
  return "—";
}

// card with the health of one component (detectorapi, detector, idmr, ...)
// it shows the status, the simple fields, the lists and, when there is one, the state of each camera
// used on the device page for the whole device and on the camera page for the slice of that camera
function ComponentCard({ name, data }) {
  if (!data || typeof data !== "object") {
    return null;
  }

  const { status, timestamp, cameras, ...rest } = data;

  const scalarEntries = Object.entries(rest).filter(([, value]) => value === null || typeof value !== "object");
  const listEntries = Object.entries(rest).filter(([, value]) => Array.isArray(value) && value.length > 0);
  const cameraEntries = cameras && typeof cameras === "object" ? Object.entries(cameras) : [];

  return (
    <div className="component-card">
      <div className="component-card-header">
        <strong>{readableKey(name)}</strong>
        {status !== undefined && <StatusBadge status={componentStatusColor(status)} label={String(status)} />}
      </div>

      <div className="component-detail-list">
        {timestamp && <DetailRow label="Last update">{formatTimestamp(timestamp)}</DetailRow>}

        {scalarEntries.map(([key, value]) => (
          <DetailRow key={key} label={readableKey(key)}>
            {value === null || value === undefined || value === "" ? "—" : String(value)}
          </DetailRow>
        ))}

        {listEntries.map(([key, value]) => (
          <DetailRow key={key} label={readableKey(key)}>
            {value.join(", ")}
          </DetailRow>
        ))}

        {cameraEntries.map(([cameraId, cameraData]) => (
          <DetailRow key={cameraId} label={cameraId}>
            {cameraState(cameraData)}
          </DetailRow>
        ))}
      </div>
    </div>
  );
}

export default ComponentCard;
