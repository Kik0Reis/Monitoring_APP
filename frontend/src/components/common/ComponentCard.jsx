import StatusBadge from "./StatusBadge";

export function formatTimestamp(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

/**
 * Renders one health-component payload (e.g. detectorapi/detector/idmr)
 * as a small card: status badge, a few scalar fields, list fields, and
 * (when present) a per-camera breakdown. Used on both the Device detail
 * page (device-wide component status) and the Camera detail page (that
 * camera's own slice of each component, see Camera.health_data).
 */
function ComponentCard({ name, data }) {
  if (!data || typeof data !== "object") {
    return null;
  }

  const { status, timestamp, cameras, ...rest } = data;

  const scalarEntries = Object.entries(rest).filter(
    ([, value]) => value === null || typeof value !== "object"
  );

  const listEntries = Object.entries(rest).filter(
    ([, value]) => Array.isArray(value) && value.length > 0
  );

  const cameraEntries = cameras && typeof cameras === "object" ? Object.entries(cameras) : [];

  return (
    <div className="component-card">
      <div className="component-card-header">
        <strong>{name.replace(/_/g, " ")}</strong>
        {status !== undefined && <StatusBadge status={status} />}
      </div>

      <div className="component-detail-list">
        {timestamp && (
          <div className="component-detail-row">
            <span>Last update</span>
            <strong>{formatTimestamp(timestamp)}</strong>
          </div>
        )}

        {scalarEntries.map(([key, value]) => (
          <div className="component-detail-row" key={key}>
            <span>{key.replace(/_/g, " ")}</span>
            <strong>
              {value === null || value === undefined || value === "" ? "—" : String(value)}
            </strong>
          </div>
        ))}

        {listEntries.map(([key, value]) => (
          <div className="component-detail-row" key={key}>
            <span>{key.replace(/_/g, " ")}</span>
            <strong>{value.length ? value.join(", ") : "none"}</strong>
          </div>
        ))}

        {cameraEntries.map(([camId, camData]) => (
          <div className="component-detail-row" key={camId}>
            <span>{camId}</span>
            <strong>
              {camData?.stage ??
                (camData?.healthy === true
                  ? "healthy"
                  : camData?.healthy === false
                  ? "unhealthy"
                  : "—")}
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ComponentCard;
