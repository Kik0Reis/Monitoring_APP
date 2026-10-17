import CollapsibleSection from "../../../components/common/CollapsibleSection";
import ComponentCard from "../../../components/common/ComponentCard";
import DetailRow from "../../../components/common/DetailRow";
import { formatTimestamp } from "../../../utils/formatTimestamp";

// the values of the latest heartbeat that get their own card, with the unit shown after the number
const HEARTBEAT_METRICS = [
  { key: "cpu", label: "CPU", unit: "%" },
  { key: "memory", label: "Memory", unit: "%" },
  { key: "storage", label: "Storage", unit: "%" },
  { key: "temperature", label: "Temperature", unit: "°C" },
];

// cards with the cpu, memory, storage and temperature of the latest heartbeat, nothing when the device sent none
export function HeartbeatSection({ heartbeat }) {
  const metrics = heartbeat
    ? HEARTBEAT_METRICS.filter((metric) => heartbeat[metric.key] !== null && heartbeat[metric.key] !== undefined)
    : [];

  if (metrics.length === 0) {
    return null;
  }

  return (
    <CollapsibleSection
      title="Latest Heartbeat"
      badge={<span className="entity-subtext">{formatTimestamp(heartbeat.received_at)}</span>}
    >
      <div className="metric-grid">
        {metrics.map((metric) => (
          <div className="metric-card" key={metric.key}>
            <span className="metric-card-label">{metric.label}</span>
            <span className="metric-card-value">
              {heartbeat[metric.key]}
              {metric.unit}
            </span>
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}

// one card for each internal component (detectorapi, detector, idmr, ...)
export function ComponentsSection({ componentStatuses }) {
  const entries = componentStatuses && typeof componentStatuses === "object" ? Object.entries(componentStatuses) : [];

  if (entries.length === 0) {
    return null;
  }

  return (
    <CollapsibleSection title="Component Status" count={entries.length}>
      <div className="component-grid">
        {entries.map(([name, data]) => (
          <ComponentCard key={name} name={name} data={data} />
        ))}
      </div>
    </CollapsibleSection>
  );
}

// the os, cpu, ram, gpu and ip of the device, only the simple values are shown
export function SystemInfoSection({ systemInfo }) {
  const entries =
    systemInfo && typeof systemInfo === "object"
      ? Object.entries(systemInfo).filter(([, value]) => value === null || typeof value !== "object")
      : [];

  if (entries.length === 0) {
    return null;
  }

  return (
    <CollapsibleSection title="System Info">
      <div className="component-grid">
        <div className="component-card">
          <div className="component-detail-list">
            {entries.map(([key, value]) => (
              <DetailRow key={key} label={key.replace(/_/g, " ")}>
                {value === null || value === undefined || value === "" ? "—" : String(value)}
              </DetailRow>
            ))}
          </div>
        </div>
      </div>
    </CollapsibleSection>
  );
}
