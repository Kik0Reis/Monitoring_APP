import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";

import { alertsApi, dashboardApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import { StatusDot } from "../../components/common/StatusBadge";

import "./Dashboard.css";

function formatAlertType(type) {
  const labels = {
    DEVICE_OFFLINE: "Offline",
    DEVICE_HEALTH: "Health",
    DEVICE_ERROR: "Error",
    MQTT_ERROR: "MQTT",
    SYSTEM_ERROR: "System",
    CAMERA_ALERT: "Camera",
    CAMERA_ERROR: "Camera Error",
    CAMERA_OFFLINE: "Camera Offline",
  };

  return labels[type] ?? type ?? "Alert";
}

function formatTime(dateString) {
  if (!dateString) return "—";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" });
}

function severityDot(severity) {
  const value = String(severity ?? "WARNING").toUpperCase();
  if (value === "CRITICAL") return "critical";
  if (value === "WARNING") return "warning";
  return "info";
}

/**
 * One dashboard panel of alert-like rows (offline / health / errors /
 * detections). Each row navigates to the device/camera on click, and has
 * its own small "resolve" button that marks it resolved without leaving
 * the dashboard -- if the same problem gets reported again over MQTT it
 * simply comes back as a fresh alert.
 */
function AlertPanel({ eyebrow, title, items, emptyText, onOpen, onResolve, showDot = true }) {
  return (
    <article className="dashboard-panel">
      <div className="panel-header">
        <div>
          <p className="panel-eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="alert-list">
        {items.length === 0 ? (
          <div className="dashboard-empty">{emptyText}</div>
        ) : (
          items.map((item) => (
            <div className="alert-row" key={item.id} onClick={() => onOpen(item)}>
              <div className="alert-row-main">
                {showDot && <StatusDot status={severityDot(item.severity)} />}
                <div>
                  <strong>{item.message ?? (item.camera_name ?? item.device_name)}</strong>
                  <span>
                    {item.message
                      ? `${item.camera_name ?? item.device_name}${
                          item.location_name ? ` · ${item.location_name}` : ""
                        }`
                      : item.location_name ?? "—"}
                  </span>
                </div>
              </div>

              <div className="alert-row-side">
                <div className="alert-row-meta">
                  <span>{formatAlertType(item.alert_type ?? item.type)}</span>
                  <time>{formatTime(item.created_at)}</time>
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
          ))
        )}
      </div>
    </article>
  );
}

function Dashboard() {
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async () => {
    try {
      setError("");
      const data = await dashboardApi.get();
      setDashboard(data);
    } catch (err) {
      setError(err.message || "Failed to load dashboard.");
    }
  }, []);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadDashboard);

  // every row click jumps straight to that item's own detail page
  function handleAlertClick(alert) {
    if (alert.camera_id) {
      navigate(`/cameras/${alert.camera_id}`);
    } else if (alert.device_id) {
      navigate(`/devices/${alert.device_id}`);
    }
  }

  async function handleResolve(alert) {
    try {
      await alertsApi.resolveById(alert.id);
      await refresh();
    } catch (err) {
      setError(err.message || "Failed to resolve alert.");
    }
  }

  function handleDeviceClick(device) {
    navigate(`/devices/${device.id}`);
  }

  function handleLocationClick(location) {
    navigate(`/locations/${location.id}`);
  }

  if (!dashboard && !error) {
    return (
      <div className="page dashboard">
        <PageHeader eyebrow="Monitoring" title="Dashboard" />
        <div className="dashboard-loading">Loading dashboard...</div>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="page dashboard">
        <PageHeader eyebrow="Monitoring" title="Dashboard">
          <button className="primary-button" onClick={refresh}>
            Retry
          </button>
        </PageHeader>
        <div className="dashboard-error">{error}</div>
      </div>
    );
  }

  const summary = dashboard?.summary ?? {};
  const offlineAlerts = dashboard?.recent_offline_alerts ?? [];
  const errorAlerts = dashboard?.recent_error_alerts ?? [];
  const devicesWithProblems = dashboard?.devices_with_problems ?? [];
  const locationsWithProblems = dashboard?.locations_with_problems ?? [];
  const recentDetections = dashboard?.recent_detections ?? [];

  const summaryCards = [
    { label: "Devices", value: summary.devices ?? 0, description: "Total devices" },
    { label: "Online", value: summary.online ?? 0, description: "Devices online" },
    { label: "Offline", value: summary.offline ?? 0, description: "Devices offline" },
    { label: "Cameras", value: summary.cameras ?? 0, description: "Registered cameras" },
  ];

  return (
    <div className="page dashboard">
      <PageHeader
        eyebrow="Monitoring"
        title="Dashboard"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <button type="button" className="text-button" onClick={() => navigate("/alerts")}>
          See All
        </button>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <section className="summary-grid">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span className="summary-card-label">{card.label}</span>
            <strong className="summary-card-value">{card.value}</strong>
            <span className="summary-card-description">{card.description}</span>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        {/* Devices/cameras currently unreachable — stays visible for as
            long as it's genuinely still offline. */}
        <AlertPanel
          eyebrow="Connectivity"
          title="Offline"
          items={offlineAlerts}
          emptyText="Nothing offline."
          onOpen={handleAlertClick}
          onResolve={handleResolve}
        />

        {/* Component healthchecks (detectorapi/detector/idmr...) already
            drive the device's own status badge/color -- no separate
            section for them here, that would just duplicate it. */}

        {/* Free-form messages actually sent over MQTT (e.g. "low
            threshold"), separate from offline/health status. Auto-clears
            after ~1 day even if still being reported. */}
        <AlertPanel
          eyebrow="Monitoring"
          title="Errors"
          items={errorAlerts}
          emptyText="No errors reported."
          onOpen={handleAlertClick}
          onResolve={handleResolve}
        />

        {/* real camera events, not "broken" problems -- plain feed, no severity dot */}
        <AlertPanel
          eyebrow="Cameras"
          title="Recent Detections"
          items={recentDetections}
          emptyText="No detections yet."
          onOpen={handleAlertClick}
          onResolve={handleResolve}
          showDot={false}
        />

        {/* click through to the device page for full status */}
        <article className="dashboard-panel">
          <div className="panel-header">
            <div>
              <p className="panel-eyebrow">Devices</p>
              <h2>Devices with problems</h2>
            </div>
            <button type="button" className="text-button" onClick={() => navigate("/devices")}>
              See All
            </button>
          </div>

          <div className="installation-list">
            {devicesWithProblems.length === 0 ? (
              <div className="dashboard-empty">No devices with problems.</div>
            ) : (
              devicesWithProblems.map((device) => (
                <button
                  type="button"
                  className="installation-row"
                  key={device.id}
                  onClick={() => handleDeviceClick(device)}
                >
                  <div className="installation-name">
                    <StatusDot status={device.status} />
                    <div>
                      <strong>
                        {device.name} - {device.location_name ?? "—"}
                      </strong>
                    </div>
                  </div>

                  <span>{device.issues?.[0] ?? "Needs attention"}</span>
                </button>
              ))
            )}
          </div>
        </article>

        <article className="dashboard-panel">
          <div className="panel-header">
            <div>
              <p className="panel-eyebrow">Locations</p>
              <h2>Locations with problems</h2>
            </div>
            <button type="button" className="text-button" onClick={() => navigate("/locations")}>
              See All
            </button>
          </div>

          <div className="installation-list">
            {locationsWithProblems.length === 0 ? (
              <div className="dashboard-empty">No locations with problems.</div>
            ) : (
              locationsWithProblems.map((location) => {
                const issues = location.issues ?? [];

                return (
                  <button
                    type="button"
                    className="installation-row"
                    key={location.id}
                    onClick={() => handleLocationClick(location)}
                  >
                    <div className="installation-name">
                      <StatusDot status={location.status ?? "offline"} />
                      <strong>{location.name}</strong>
                    </div>

                    <span>{issues.join(", ") || "Needs attention"}</span>
                  </button>
                );
              })
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

export default Dashboard;
