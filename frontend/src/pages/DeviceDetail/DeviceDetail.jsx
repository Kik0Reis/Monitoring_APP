import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { devicesApi, camerasApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import CrudModal from "../../components/crud/CrudModal";

const EMPTY_FORM = { name: "", camera_identifier: "", channel: 1, active: true };

// Fields that get their own "metric card" instead of a generic detail row.
const METRIC_KEYS = ["cpu", "memory", "storage", "temperature"];

const METRIC_LABELS = {
  cpu: "CPU",
  memory: "Memory",
  storage: "Storage",
  temperature: "Temperature",
};

function metricSuffix(key) {
  return key === "temperature" ? "°C" : "%";
}

function formatTimestamp(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

/**
 * Renders one entry of device.component_statuses as a card. The MQTT
 * payload shape isn't fixed ahead of time (different component types
 * report different fields), so this walks the object generically:
 * scalars become detail rows, nested per-camera breakdowns become a
 * compact sub-list, and "status"/"timestamp" get pulled into the header.
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
        <StatusBadge status={status} />
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
            <strong>{String(value)}</strong>
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

function DeviceDetail() {
  const { deviceId } = useParams();
  const navigate = useNavigate();

  const [device, setDevice] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const loadDevice = useCallback(async () => {
    try {
      const data = await devicesApi.get(deviceId);
      setDevice(data);
    } catch {
      setNotFound(true);
    }
  }, [deviceId]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadDevice);

  const cameras = useCrudResource({
    api: camerasApi,
    emptyFormData: EMPTY_FORM,
    filters: { device: deviceId },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      camera_identifier: formData.camera_identifier.trim(),
      channel: Number(formData.channel) || 1,
      active: Boolean(formData.active),
      device_id: deviceId,
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      camera_identifier: item.camera_identifier,
      channel: item.channel,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Camera name is required.";
      if (!formData.camera_identifier.trim()) return "Camera identifier is required.";
      return null;
    },
  });

  if (notFound) {
    return (
      <div className="page">
        <p className="dashboard-error">Device not found.</p>
      </div>
    );
  }

  const formFields = [
    { name: "name", label: "Name", type: "text", placeholder: "Office Camera 1" },
    { name: "camera_identifier", label: "Camera Identifier", type: "text" },
    { name: "channel", label: "Channel", type: "text", placeholder: "1" },
    { name: "active", label: "Active", type: "checkbox" },
  ];

  const cameraColumns = [
    {
      key: "name",
      header: "Name",
      render: (row) => <span className="entity-name">{row.name}</span>,
    },
    { key: "channel", header: "Ch." },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "last_seen",
      header: "Last Seen",
      render: (row) => formatTimestamp(row.last_seen),
    },
  ];

  const componentEntries =
    device?.component_statuses && typeof device.component_statuses === "object"
      ? Object.entries(device.component_statuses)
      : [];

  const heartbeat = device?.latest_heartbeat;

  const heartbeatMetrics = heartbeat
    ? METRIC_KEYS.filter((key) => heartbeat[key] !== null && heartbeat[key] !== undefined)
    : [];

  return (
    <div className="page">
      <Breadcrumbs
        trail={device?.breadcrumb?.slice(0, -1)}
        trailingLabel={device?.name ?? "..."}
      />

      <PageHeader
        eyebrow="Device"
        title={device?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      />

      {device && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{device.name}</h2>
                <StatusBadge status={device.status} />
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Location</span>
                  <strong>{device.location?.name}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Serial Number</span>
                  <strong>{device.serial_number}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>MQTT Identifier</span>
                  <strong>{device.mqtt_identifier}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Device Type</span>
                  <strong>{device.device_type}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Last Seen</span>
                  <strong>{formatTimestamp(device.last_seen)}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Cameras</span>
                  <strong>{device.cameras_count ?? 0}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {heartbeat && heartbeatMetrics.length > 0 && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>Latest Heartbeat</h3>
            <span className="entity-subtext">
              {formatTimestamp(heartbeat.received_at)}
            </span>
          </div>

          <div className="metric-grid">
            {heartbeatMetrics.map((key) => (
              <div className="metric-card" key={key}>
                <span className="metric-card-label">{METRIC_LABELS[key]}</span>
                <span className="metric-card-value">
                  {heartbeat[key]}
                  {metricSuffix(key)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {componentEntries.length > 0 && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>Component Status</h3>
          </div>

          <div className="component-grid">
            {componentEntries.map(([name, data]) => (
              <ComponentCard key={name} name={name} data={data} />
            ))}
          </div>
        </section>
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Cameras on {device?.name}</h3>
          <button className="primary-button" onClick={() => cameras.openCreate()}>
            + Add Camera
          </button>
        </div>

        {cameras.error && <div className="error-message">{cameras.error}</div>}

        <DataTable
          columns={cameraColumns}
          rows={cameras.items}
          loading={cameras.loading}
          loadingMessage="Loading cameras..."
          emptyMessage="No cameras on this device yet."
          onRowClick={(camera) => navigate(`/cameras/${camera.id}`)}
          actions={(camera) => (
            <>
              <button className="icon-button" onClick={() => cameras.openEdit(camera)}>
                ✎
              </button>
              <button
                className="icon-button danger"
                onClick={() => cameras.handleDelete(camera)}
              >
                🗑
              </button>
            </>
          )}
        />
      </section>

      {cameras.modalMode && (
        <CrudModal
          mode={cameras.modalMode}
          title={cameras.modalMode === "create" ? "Add Camera" : "Edit Camera"}
          onClose={cameras.closeModal}
          onSubmit={cameras.handleSubmit}
          loading={cameras.saving}
        >
          <div className="crud-form">
            {formFields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={cameras.formData[field.name]}
                onChange={cameras.handleFormChange}
                disabled={cameras.saving}
              />
            ))}
          </div>
        </CrudModal>
      )}
    </div>
  );
}

export default DeviceDetail;
