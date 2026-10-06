import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, Pencil, Trash2, X } from "lucide-react";

import { alertsApi, devicesApi, camerasApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import ComponentCard from "../../components/common/ComponentCard";
import CollapsibleSection from "../../components/common/CollapsibleSection";
import { formatTimestamp } from "../../utils/formatTimestamp";

import CrudModal from "../../components/crud/CrudModal";
import RollupIndicator from "../../components/common/RollupIndicator";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";

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

/**
 * One row inside an Offline/Errors section, with a resolve button.
 * Only active alerts show a resolve button -- resolved ones are just kept
 * out of the list entirely (see the filters in the sections below).
 */
function AlertRow({ alert, onResolve }) {
  return (
    <div className="entity-alert-row active">
      <div className="entity-alert-main">
        <StatusBadge status="warning" label="Active" />
        <span>{alert.message}</span>
      </div>

      <div className="entity-alert-row-end">
        <time>{formatTimestamp(alert.created_at)}</time>
        <button
          type="button"
          className="alert-row-resolve"
          title="Mark as resolved"
          onClick={() => onResolve(alert)}
        >
          <X size={14} />
        </button>
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
  const rollup = useMonitorRollup();

  async function handleResolveAlert(alert) {
    try {
      await alertsApi.resolveDevice(alert.id);
      await loadDevice();
    } catch {
      // Best-effort; the row just stays visible if this fails.
    }
  }

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
      key: "health",
      header: "Health",
      render: (row) => <RollupIndicator node={rollup.get("camera", row.id)} />,
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

  // Same alert list, split by category (see monitoring/services/dashboard.py):
  // "offline" = unreachable right now, "error" = a free-form MQTT message
  // (e.g. "low threshold"). DEVICE_HEALTH ("health") is deliberately not
  // shown here -- it's what already drives the device's own status badge/
  // component cards above, a separate section would just duplicate it.
  const allAlerts = device?.alerts ?? [];
  const activeAlerts = allAlerts.filter((alert) => alert.active);
  const offlineAlerts = activeAlerts.filter((alert) => alert.category === "offline");
  const errorAlerts = activeAlerts.filter((alert) => alert.category === "error");

  const systemInfoEntries =
    device?.system_info && typeof device.system_info === "object"
      ? Object.entries(device.system_info).filter(
          ([, value]) => value === null || typeof value !== "object"
        )
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
                <RollupIndicator node={rollup.get("device", device.id)} showLabel />
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

      {offlineAlerts.length > 0 && (
        <CollapsibleSection title="Offline" count={offlineAlerts.length} defaultOpen>
          <div className="entity-alerts-list">
            {offlineAlerts.map((alert) => (
              <AlertRow key={alert.id} alert={alert} onResolve={handleResolveAlert} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {errorAlerts.length > 0 && (
        <CollapsibleSection title="Errors" count={errorAlerts.length} defaultOpen>
          <div className="entity-alerts-list">
            {errorAlerts.map((alert) => (
              <AlertRow key={alert.id} alert={alert} onResolve={handleResolveAlert} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {heartbeat && heartbeatMetrics.length > 0 && (
        <CollapsibleSection
          title="Latest Heartbeat"
          badge={<span className="entity-subtext">{formatTimestamp(heartbeat.received_at)}</span>}
        >
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
        </CollapsibleSection>
      )}

      {componentEntries.length > 0 && (
        <CollapsibleSection title="Component Status" count={componentEntries.length}>
          <div className="component-grid">
            {componentEntries.map(([name, data]) => (
              <ComponentCard key={name} name={name} data={data} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      {systemInfoEntries.length > 0 && (
        <CollapsibleSection title="System Info">
          <div className="component-grid">
            <div className="component-card">
              <div className="component-detail-list">
                {systemInfoEntries.map(([key, value]) => (
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
        </CollapsibleSection>
      )}

      <CollapsibleSection
        title={`Cameras on ${device?.name ?? "..."}`}
        count={cameras.items.length}
        defaultOpen
        actions={
          <button className="primary-button" onClick={() => cameras.openCreate()}>
            + Add Camera
          </button>
        }
      >
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
      </CollapsibleSection>

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
