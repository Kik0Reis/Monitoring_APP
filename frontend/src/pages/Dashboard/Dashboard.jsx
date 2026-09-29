import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";

import { alertsApi, dashboardApi, detectionsApi, problemsApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import { StatusDot } from "../../components/common/StatusBadge";
import ListModal from "../../components/common/ListModal";

import "./Dashboard.css";

// How many rows a panel shows before you have to open "View all" -- keeps
// every section visible without scrolling, no matter how many problems
// there are (see PREVIEW_ROWS below).
const PREVIEW_ROWS = 3;

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

/** One alert/detection row -- used both in a panel's 3-row preview and in
 * the "View all" popup, so they always look identical. */
function AlertRow({ item, onOpen, onResolve, showDot = true }) {
  return (
    <div className="alert-row" onClick={() => onOpen(item)}>
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
  );
}

/** One installation (device/location) row -- same idea as AlertRow, shared
 * between preview and popup. */
function InstallationRow({ item, statusValue, subtitle, onOpen }) {
  return (
    <button type="button" className="installation-row" onClick={() => onOpen(item)}>
      <div className="installation-name">
        <StatusDot status={statusValue} />
        <strong>{subtitle}</strong>
      </div>
      <span>{item.issues?.join(", ") || item.issues?.[0] || "Needs attention"}</span>
    </button>
  );
}

/**
 * One compact dashboard section: a clickable header with a count pill
 * (red/amber when there's a problem, neutral when clear), a short preview
 * of up to PREVIEW_ROWS items, and a "View all" button once there's more
 * than that. Clicking the header or the pill opens the same popup as
 * "View all" -- both are "the counters are clickable" per the same action.
 */
function SectionPanel({ eyebrow, title, count, tone, emptyText, onViewAll, children }) {
  const hasProblem = count > 0;

  return (
    <article className={`dashboard-panel compact ${hasProblem ? `has-${tone}` : ""}`}>
      <button type="button" className="panel-header panel-header-clickable" onClick={onViewAll}>
        <div>
          <p className="panel-eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <span className={`panel-count-pill ${hasProblem ? tone : "ok"}`}>{count}</span>
      </button>

      {count === 0 ? (
        <div className="dashboard-empty compact-empty">{emptyText}</div>
      ) : (
        <>
          <div className="alert-list compact-list">{children}</div>

          {count > PREVIEW_ROWS && (
            <button type="button" className="panel-view-all" onClick={onViewAll}>
              View all {count} →
            </button>
          )}
        </>
      )}
    </article>
  );
}

function Dashboard() {
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");

  // Which popup is open, if any: "offline" | "error" | "detections" |
  // "devices" | "locations". Devices/locations already come back in full
  // (up to 50) in the dashboard payload, so their popup just reuses that.
  // Offline/error/detections only carry a short preview, so opening those
  // fetches the full list on demand.
  const [modalType, setModalType] = useState(null);
  const [modalItems, setModalItems] = useState([]);
  const [modalLoading, setModalLoading] = useState(false);

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

  function handleDeviceClick(device) {
    navigate(`/devices/${device.id}`);
  }

  function handleLocationClick(location) {
    navigate(`/locations/${location.id}`);
  }

  async function handleResolve(alert) {
    try {
      await alertsApi.resolveById(alert.id);
      // keep the open popup in sync too, not just the panels behind it
      setModalItems((items) => items.filter((item) => item.id !== alert.id));
      await refresh();
    } catch (err) {
      setError(err.message || "Failed to resolve alert.");
    }
  }

  function closeModal() {
    setModalType(null);
    setModalItems([]);
  }

  async function openModal(type) {
    setModalType(type);

    if (type === "devices") {
      setModalItems(dashboard?.devices_with_problems ?? []);
      return;
    }

    if (type === "locations") {
      setModalItems(dashboard?.locations_with_problems ?? []);
      return;
    }

    setModalLoading(true);
    try {
      const res =
        type === "detections"
          ? await detectionsApi.list("?limit=200")
          : await problemsApi.list(`?category=${type}&active_only=true&limit=200`);
      setModalItems(res.results ?? []);
    } catch (err) {
      setError(err.message || "Failed to load list.");
    } finally {
      setModalLoading(false);
    }
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
  const counts = dashboard?.alert_counts ?? { offline: 0, error: 0, detections: 0 };
  const offlinePreview = dashboard?.recent_offline_alerts ?? [];
  const errorPreview = dashboard?.recent_error_alerts ?? [];
  const detectionsPreview = dashboard?.recent_detections ?? [];
  const devicesWithProblems = dashboard?.devices_with_problems ?? [];
  const locationsWithProblems = dashboard?.locations_with_problems ?? [];

  // Every card is clickable and sends you to the Devices/Cameras list,
  // pre-filtered by status (no filter for the plain "Devices"/"Cameras"
  // totals) -- both list pages read ?status= from the URL on load.
  const summaryCards = [
    { label: "Devices", value: summary.devices ?? 0, description: "Total devices", to: "/devices" },
    {
      label: "Online",
      value: summary.online ?? 0,
      description: "Devices online",
      to: "/devices?status=ONLINE",
    },
    {
      label: "Offline",
      value: summary.offline ?? 0,
      description: "Devices offline",
      to: "/devices?status=OFFLINE",
    },
    { label: "Cameras", value: summary.cameras ?? 0, description: "Registered cameras", to: "/cameras" },
    {
      label: "Cameras Online",
      value: summary.cameras_online ?? 0,
      description: "Cameras online",
      to: "/cameras?status=ONLINE",
    },
    {
      label: "Cameras Offline",
      value: summary.cameras_offline ?? 0,
      description: "Cameras offline",
      to: "/cameras?status=OFFLINE",
    },
  ];

  const modalConfig = {
    offline: { eyebrow: "Connectivity", title: "Offline" },
    error: { eyebrow: "Monitoring", title: "Errors" },
    detections: { eyebrow: "Cameras", title: "Recent Detections" },
    devices: { eyebrow: "Devices", title: "Devices with problems" },
    locations: { eyebrow: "Locations", title: "Locations with problems" },
  }[modalType];

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
          <button
            type="button"
            className="summary-card summary-card-clickable"
            key={card.label}
            onClick={() => navigate(card.to)}
          >
            <span className="summary-card-label">{card.label}</span>
            <strong className="summary-card-value">{card.value}</strong>
            <span className="summary-card-description">{card.description}</span>
          </button>
        ))}
      </section>

      <section className="dashboard-grid compact-grid">
        {/* Devices/cameras currently unreachable — stays a problem for as
            long as it's genuinely still offline. */}
        <SectionPanel
          eyebrow="Connectivity"
          title="Offline"
          count={counts.offline}
          tone="critical"
          emptyText="Nothing offline."
          onViewAll={() => openModal("offline")}
        >
          {offlinePreview.slice(0, PREVIEW_ROWS).map((item) => (
            <AlertRow key={item.id} item={item} onOpen={handleAlertClick} onResolve={handleResolve} />
          ))}
        </SectionPanel>

        {/* Component healthchecks (detectorapi/detector/idmr...) already
            drive the device's own status badge/color -- no separate
            section for them here, that would just duplicate it. */}

        {/* Free-form messages actually sent over MQTT (e.g. "low
            threshold"), separate from offline status. Auto-clears after a
            while (configurable in Settings) even if still being reported. */}
        <SectionPanel
          eyebrow="Monitoring"
          title="Errors"
          count={counts.error}
          tone="warning"
          emptyText="No errors reported."
          onViewAll={() => openModal("error")}
        >
          {errorPreview.slice(0, PREVIEW_ROWS).map((item) => (
            <AlertRow key={item.id} item={item} onOpen={handleAlertClick} onResolve={handleResolve} />
          ))}
        </SectionPanel>

        {/* real camera events, not "broken" problems -- neutral tone, no severity dot */}
        <SectionPanel
          eyebrow="Cameras"
          title="Recent Detections"
          count={counts.detections}
          tone="info"
          emptyText="No detections yet."
          onViewAll={() => openModal("detections")}
        >
          {detectionsPreview.slice(0, PREVIEW_ROWS).map((item) => (
            <AlertRow
              key={item.id}
              item={item}
              onOpen={handleAlertClick}
              onResolve={handleResolve}
              showDot={false}
            />
          ))}
        </SectionPanel>

        <SectionPanel
          eyebrow="Devices"
          title="Devices with problems"
          count={devicesWithProblems.length}
          tone="critical"
          emptyText="No devices with problems."
          onViewAll={() => openModal("devices")}
        >
          {devicesWithProblems.slice(0, PREVIEW_ROWS).map((device) => (
            <InstallationRow
              key={device.id}
              item={device}
              statusValue={device.status}
              subtitle={`${device.name} - ${device.location_name ?? "—"}`}
              onOpen={handleDeviceClick}
            />
          ))}
        </SectionPanel>

        <SectionPanel
          eyebrow="Locations"
          title="Locations with problems"
          count={locationsWithProblems.length}
          tone="critical"
          emptyText="No locations with problems."
          onViewAll={() => openModal("locations")}
        >
          {locationsWithProblems.slice(0, PREVIEW_ROWS).map((location) => (
            <InstallationRow
              key={location.id}
              item={location}
              statusValue={location.status ?? "offline"}
              subtitle={location.name}
              onOpen={handleLocationClick}
            />
          ))}
        </SectionPanel>
      </section>

      {modalType && (
        <ListModal
          eyebrow={modalConfig.eyebrow}
          title={modalConfig.title}
          count={modalItems.length}
          onClose={closeModal}
        >
          {modalLoading ? (
            <div className="list-modal-loading">Loading...</div>
          ) : modalItems.length === 0 ? (
            <div className="list-modal-empty">Nothing here.</div>
          ) : modalType === "devices" ? (
            modalItems.map((device) => (
              <InstallationRow
                key={device.id}
                item={device}
                statusValue={device.status}
                subtitle={`${device.name} - ${device.location_name ?? "—"}`}
                onOpen={handleDeviceClick}
              />
            ))
          ) : modalType === "locations" ? (
            modalItems.map((location) => (
              <InstallationRow
                key={location.id}
                item={location}
                statusValue={location.status ?? "offline"}
                subtitle={location.name}
                onOpen={handleLocationClick}
              />
            ))
          ) : (
            modalItems.map((item) => (
              <AlertRow
                key={item.id}
                item={item}
                onOpen={handleAlertClick}
                onResolve={handleResolve}
                showDot={modalType !== "detections"}
              />
            ))
          )}
        </ListModal>
      )}
    </div>
  );
}

export default Dashboard;
