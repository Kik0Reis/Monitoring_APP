import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, Pencil, Trash2 } from "lucide-react";

import { devicesApi, camerasApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import ComponentCard, { formatTimestamp } from "../../components/common/ComponentCard";
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
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          {!row.on_mqtt && <NotOnMqttBadge />}
        </span>
      ),
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

  async function handleApproveCamera(item) {
    await camerasApi.approve(item.id);
    await cameras.reload();
  }

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
      >
        {device?.pending_review && (
          <button
            className="secondary-button"
            onClick={async () => {
              try {
                await devicesApi.approve(device.id);
                await loadDevice();
              } catch {
                // Best-effort; the badge just stays visible if this fails.
              }
            }}
          >
            Approve
          </button>
        )}
      </PageHeader>

      {device && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{device.name}</h2>
                <StatusBadge status={device.status} />
                {device.pending_review && <PendingReviewBadge />}
                {!device.on_mqtt && <NotOnMqttBadge />}
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Location</span>
                  <strong>{device.location?.name}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Customer</span>
                  <strong>
                    {device.breadcrumb?.find((entry) => entry.type === "customer")
                      ?.name ?? "—"}
                  </strong>
                </div>
                <div className="detail-meta-item">
                  <span>Country</span>
                  <strong>
                    {device.breadcrumb?.find((entry) => entry.type === "country")
                      ?.name ?? "—"}
                  </strong>
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

      {device && device.alerts && device.alerts.length > 0 && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>Alerts</h3>
          </div>

          <div className="entity-alerts-list">
            {device.alerts.map((alert) => (
              <div
                className={`entity-alert-row ${alert.active ? "active" : "resolved"}`}
                key={alert.id}
              >
                <div className="entity-alert-main">
                  <StatusBadge
                    status={alert.active ? "warning" : "unknown"}
                    label={alert.active ? "Active" : "Resolved"}
                  />
                  <span>{alert.message}</span>
                </div>
                <time>{formatTimestamp(alert.created_at)}</time>
              </div>
            ))}
          </div>
        </section>
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

      {device?.system_info && Object.keys(device.system_info).length > 0 && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>System Info</h3>
          </div>

          <div className="component-grid">
            <div className="component-card">
              <div className="component-detail-list">
                {Object.entries(device.system_info)
                  .filter(([, value]) => value === null || typeof value !== "object")
                  .map(([key, value]) => (
                    <div className="component-detail-row" key={key}>
                      <span>{key.replace(/_/g, " ")}</span>
                      <strong>
                        {value === null || value === undefined || value === ""
                          ? "—"
                          : String(value)}
                      </strong>
                    </div>
                  ))}
              </div>
            </div>
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
              {camera.pending_review && (
                <button
                  className="icon-button"
                  title="Approve"
                  onClick={() => handleApproveCamera(camera)}
                >
                  <Check size={16} />
                </button>
              )}
              <button className="icon-button" onClick={() => cameras.openEdit(camera)}>
                <Pencil size={16} />
              </button>
              <button
                className="icon-button danger"
                onClick={() => cameras.handleDelete(camera)}
              >
                <Trash2 size={16} />
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
