import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { alertsApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import StatusBadge, { StatusDot } from "../../components/common/StatusBadge";

import "./Alerts.css";

function severityToStatus(severity) {
  const value = String(severity ?? "").toLowerCase();

  if (value === "critical" || value === "error") return "critical";
  if (value === "warning") return "warning";
  return "info";
}

function formatTimestamp(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const [showActiveOnly, setShowActiveOnly] = useState(false);

  const loadAlerts = useCallback(async () => {
    try {
      setError("");
      const data = await alertsApi.list("?limit=200");
      setAlerts(data.results ?? []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadAlerts);

  const visibleAlerts = showActiveOnly ? alerts.filter((a) => a.active) : alerts;

  function goToAlert(alert) {
    if (alert.camera_id) {
      navigate(`/cameras/${alert.camera_id}`);
    } else if (alert.device_id) {
      navigate(`/devices/${alert.device_id}`);
    } else if (alert.location_id) {
      navigate(`/locations/${alert.location_id}`);
    }
  }

  return (
    <div className="page alerts">
      <PageHeader
        eyebrow="Monitoring"
        title="Alerts"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <label className="alerts-filter-toggle">
          <input
            type="checkbox"
            checked={showActiveOnly}
            onChange={(event) => setShowActiveOnly(event.target.checked)}
          />
          Active only
        </label>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <div className="table-card">
        <div className="alert-list">
          {visibleAlerts.length === 0 ? (
            <p className="dashboard-empty">No alerts to show.</p>
          ) : (
            visibleAlerts.map((alert) => (
              <button
                key={alert.id}
                className="alert-row"
                onClick={() => goToAlert(alert)}
              >
                <div className="alert-row-main">
                  <StatusDot status={severityToStatus(alert.severity)} />
                  <div>
                    <strong>{alert.message}</strong>
                    <span>
                      {alert.camera_name ?? alert.device_name}
                      {alert.location_name ? ` · ${alert.location_name}` : ""}
                    </span>
                  </div>
                </div>

                <div className="alert-row-meta">
                  <StatusBadge
                    status={alert.active ? "warning" : "unknown"}
                    label={alert.active ? "Active" : "Resolved"}
                  />
                  <time>{formatTimestamp(alert.created_at)}</time>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Alerts;
