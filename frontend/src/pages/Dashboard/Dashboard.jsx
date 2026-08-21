import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { dashboardApi } from "../../services/api";
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

  // Every alert/device/location click navigates straight to the drilldown
  // page for that item, so a broken device on the dashboard is always one
  // click away from its full status (components, health, cameras...).
  function handleAlertClick(alert) {
    if (alert.camera_id) {
      navigate(`/cameras/${alert.camera_id}`);
    } else if (alert.device_id) {
      navigate(`/devices/${alert.device_id}`);
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
  const recentAlerts = dashboard?.recent_alerts ?? [];
  const devicesWithProblems = dashboard?.devices_with_problems ?? [];
  const locationsWithProblems = dashboard?.locations_with_problems ?? [];

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
      />

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
        <article className="dashboard-panel">
          <div className="panel-header">
            <div>
              <p className="panel-eyebrow">Monitoring</p>
              <h2>Recent Alerts</h2>
            </div>
            <button type="button" className="text-button" onClick={() => navigate("/alerts")}>
              See All
            </button>
          </div>

          <div className="alert-list">
            {recentAlerts.length === 0 ? (
              <div className="dashboard-empty">No active alerts.</div>
            ) : (
              recentAlerts.map((alert) => (
                <button
                  type="button"
                  className="alert-row"
                  key={alert.id}
                  onClick={() => handleAlertClick(alert)}
                >
                  <div className="alert-row-main">
                    <StatusDot status={severityDot(alert.severity)} />
                    <div>
                      <strong>{alert.camera_name ?? alert.device_name}</strong>
                      <span>{alert.location_name ?? "—"}</span>
                    </div>
                  </div>

                  <div className="alert-row-meta">
                    <span>{formatAlertType(alert.alert_type ?? alert.type)}</span>
                    <time>{formatTime(alert.created_at)}</time>
                  </div>
                </button>
              ))
            )}
          </div>
        </article>

        {/* Devices with problems: click straight through to the device
            page, which now shows full component/health status. */}
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
                      <strong>{device.name}</strong>
                      <span>{device.location_name ?? "—"}</span>
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
                const problemCount = location.problem_count ?? 0;

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

                    <span>
                      {problemCount} {problemCount === 1 ? "problem" : "problems"}
                    </span>
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
