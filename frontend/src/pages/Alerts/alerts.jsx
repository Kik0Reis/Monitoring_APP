import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { problemsApi, detectionsApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { formatTimestamp } from "../../utils/formatTimestamp";

import PageHeader from "../../components/common/PageHeader";
import StatusBadge, { StatusDot } from "../../components/common/StatusBadge";

import "./Alerts.css";

function severityToStatus(severity) {
  const value = String(severity ?? "").toLowerCase();

  if (value === "critical" || value === "error") return "critical";
  if (value === "warning") return "warning";
  return "info";
}

function AlertRow({ alert, onClick, showStatus = true }) {
  return (
    <button className="alert-row" onClick={onClick}>
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
        {showStatus && (
          <StatusBadge
            status={alert.active ? "warning" : "unknown"}
            label={alert.active ? "Active" : "Resolved"}
          />
        )}
        <time>{formatTimestamp(alert.created_at)}</time>
      </div>
    </button>
  );
}

/**
 * Two tabs:
 *
 * - "Problems": device/camera health & connectivity issues (offline,
 *   unhealthy component, MQTT/system errors, camera errors). Defaults to
 *   showing only *active* problems, since the backend already reuses one
 *   alert row per device while it stays broken — active-only naturally
 *   shows one row per thing that currently needs attention, instead of
 *   repeating a flapping device's entire history. "Show history" reveals
 *   the full (including resolved) log.
 *
 * - "Detections": real events reported by cameras over MQTT. These don't have an active/resolved lifecycle — every
 *   detection is a distinct event, so it's just a chronological log.
 */
function Alerts() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("problems");
  const [showHistory, setShowHistory] = useState(false);

  const [problems, setProblems] = useState([]);
  const [detections, setDetections] = useState([]);
  const [error, setError] = useState("");

  const loadProblems = useCallback(async () => {
    try {
      setError("");
      const params = `?limit=200&active_only=${showHistory ? "false" : "true"}`;
      const data = await problemsApi.list(params);
      setProblems(data.results ?? []);
    } catch (err) {
      setError(err.message);
    }
  }, [showHistory]);

  const loadDetections = useCallback(async () => {
    try {
      setError("");
      const data = await detectionsApi.list("?limit=200");
      setDetections(data.results ?? []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const loadActiveTab = useCallback(async () => {
    if (tab === "problems") {
      await loadProblems();
    } else {
      await loadDetections();
    }
  }, [tab, loadProblems, loadDetections]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadActiveTab);

  // Re-fetch immediately when switching tabs or toggling history, rather
  // than waiting for the next 60s auto-refresh tick.
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, showHistory]);

  function goToAlert(alert) {
    if (alert.camera_id) {
      navigate(`/cameras/${alert.camera_id}`);
    } else if (alert.device_id) {
      navigate(`/devices/${alert.device_id}`);
    } else if (alert.location_id) {
      navigate(`/locations/${alert.location_id}`);
    }
  }

  const rows = tab === "problems" ? problems : detections;

  return (
    <div className="page alerts">
      <PageHeader
        eyebrow="Monitoring"
        title="Alerts"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {tab === "problems" && (
          <label className="alerts-filter-toggle">
            <input
              type="checkbox"
              checked={showHistory}
              onChange={(event) => setShowHistory(event.target.checked)}
            />
            Show history
          </label>
        )}
      </PageHeader>

      <div className="alerts-tabs">
        <button
          className={`alerts-tab ${tab === "problems" ? "active" : ""}`}
          onClick={() => setTab("problems")}
        >
          Problems
          {problems.length > 0 && (
            <span className="alerts-tab-count">{problems.length}</span>
          )}
        </button>

        <button
          className={`alerts-tab ${tab === "detections" ? "active" : ""}`}
          onClick={() => setTab("detections")}
        >
          Detections
          {detections.length > 0 && (
            <span className="alerts-tab-count">{detections.length}</span>
          )}
        </button>
      </div>

      {tab === "problems" && (
        <p className="alerts-tab-description">
          {showHistory
            ? "Full history, including problems that have already been resolved."
            : "Only problems that currently need attention — one row per device or camera."}
        </p>
      )}

      {tab === "detections" && (
        <p className="alerts-tab-description">
          Events reported directly by cameras over MQTT.
        </p>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="table-card">
        <div className="alert-list">
          {rows.length === 0 ? (
            <p className="dashboard-empty">
              {tab === "problems" ? "No problems to show." : "No detections to show."}
            </p>
          ) : (
            rows.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                onClick={() => goToAlert(alert)}
                showStatus={tab === "problems"}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Alerts;
