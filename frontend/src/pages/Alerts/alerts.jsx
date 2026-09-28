import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";

import { alertsApi, detectionsApi, problemsApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import { StatusDot } from "../../components/common/StatusBadge";

import "./Alerts.css";

// Each tab maps to a monitoring/services/dashboard.py category, except
// "detections" which is a different endpoint entirely (real events, not
// problems). See that module's docstrings for what each category means.
const TABS = [
  {
    key: "offline",
    label: "Offline",
    description: "Devices and cameras that are currently unreachable.",
  },
  {
    key: "error",
    label: "Errors",
    description:
      "Free-form messages actually sent over MQTT (e.g. low threshold). These clear on their own after a while (configurable in Settings).",
  },
  {
    key: "detections",
    label: "Detections",
    description: "Real-world events reported by cameras.",
  },
];

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
  return date.toLocaleString("pt-PT", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function severityDot(severity) {
  const value = String(severity ?? "WARNING").toUpperCase();
  if (value === "CRITICAL") return "critical";
  if (value === "WARNING") return "warning";
  return "info";
}

function Alerts() {
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("offline");
  const [showHistory, setShowHistory] = useState(false);

  const [itemsByTab, setItemsByTab] = useState({
    offline: [],
    error: [],
    detections: [],
  });
  const [error, setError] = useState("");

  const isDetections = activeTab === "detections";

  const load = useCallback(async () => {
    try {
      setError("");

      const [offlineRes, errorRes, detectionsRes] = await Promise.all([
        problemsApi.list(`?category=offline&active_only=${!showHistory}&limit=200`),
        problemsApi.list(`?category=error&active_only=${!showHistory}&limit=200`),
        detectionsApi.list("?limit=200"),
      ]);

      setItemsByTab({
        offline: offlineRes.results ?? [],
        error: errorRes.results ?? [],
        detections: detectionsRes.results ?? [],
      });
    } catch (err) {
      setError(err.message || "Failed to load alerts.");
    }
  }, [showHistory]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(load);

  // Re-fetch immediately when toggling history (or switching tabs), rather
  // than waiting for the next 60s auto-refresh tick -- useAutoRefresh only
  // runs the loader on its timer, it doesn't watch the loader's deps.
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showHistory, activeTab]);

  async function handleResolve(item) {
    try {
      await alertsApi.resolveById(item.id);
      await refresh();
    } catch (err) {
      setError(err.message || "Failed to resolve alert.");
    }
  }

  function handleOpen(item) {
    if (item.camera_id) {
      navigate(`/cameras/${item.camera_id}`);
    } else if (item.device_id) {
      navigate(`/devices/${item.device_id}`);
    }
  }

  const items = itemsByTab[activeTab] ?? [];
  const activeTabInfo = useMemo(
    () => TABS.find((tab) => tab.key === activeTab),
    [activeTab]
  );

  return (
    <div className="page alerts">
      <PageHeader
        eyebrow="Monitoring"
        title="Alerts"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {!isDetections && (
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

      {error && <div className="error-message">{error}</div>}

      <div className="alerts-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`alerts-tab ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
            <span className="alerts-tab-count">{itemsByTab[tab.key]?.length ?? 0}</span>
          </button>
        ))}
      </div>

      <p className="alerts-tab-description">{activeTabInfo?.description}</p>

      <div className="alert-list alert-list-page">
        {items.length === 0 ? (
          <div className="dashboard-empty">Nothing here.</div>
        ) : (
          items.map((item) => (
            <div className="alert-row" key={item.id} onClick={() => handleOpen(item)}>
              <div className="alert-row-main">
                {!isDetections && <StatusDot status={severityDot(item.severity)} />}
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
                  {!item.active && <span className="alert-row-resolved-tag">Resolved</span>}
                  <time>{formatTime(item.created_at)}</time>
                </div>

                <button
                  type="button"
                  className="alert-row-resolve"
                  title={item.active === false ? "Already resolved" : "Mark as resolved"}
                  disabled={item.active === false}
                  onClick={(event) => {
                    event.stopPropagation();
                    handleResolve(item);
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Alerts;
