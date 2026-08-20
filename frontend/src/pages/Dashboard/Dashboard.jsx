import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { dashboardApi } from "../../services/api";

import "./dashboard.css";


/* ============================================================
   STATUS DOT
   ============================================================ */

function StatusDot({ status }) {
  const normalizedStatus = String(
    status ?? "unknown"
  ).toLowerCase();

  return (
    <span
      className={`status-dot status-dot-${normalizedStatus}`}
    />
  );
}


/* ============================================================
   ALERT TYPE LABEL
   ============================================================ */

function formatAlertType(type) {
  if (!type) {
    return "Alert";
  }

  const labels = {
    DEVICE_OFFLINE: "Offline",
    DEVICE_HEALTH: "Health",
    DEVICE_ERROR: "Error",
    MQTT_ERROR: "MQTT",
    SYSTEM_ERROR: "System",
    CAMERA_ALERT: "Camera",
    CAMERA_ERROR: "Camera Error",
  };

  return labels[type] ?? type;
}


/* ============================================================
   TIME FORMAT
   ============================================================ */

function formatTime(dateString) {
  if (!dateString) {
    return "—";
  }

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleTimeString("pt-PT", {
    hour: "2-digit",
    minute: "2-digit",
  });
}


/* ============================================================
   DASHBOARD
   ============================================================ */

function Dashboard() {
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");


  /* ==========================================================
     LOAD DASHBOARD
     ========================================================== */

  async function loadDashboard(showRefreshing = false) {
    try {
      if (showRefreshing) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const data = await dashboardApi.get();

      setDashboard(data);
    } catch (err) {
      console.error(
        "Failed to load dashboard:",
        err
      );

      setError(
        err.message ||
        "Failed to load dashboard."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }


  /* ==========================================================
     INITIAL LOAD
     ========================================================== */

  useEffect(() => {
    loadDashboard();
  }, []);


  /* ==========================================================
     REFRESH
     ========================================================== */

  function handleRefresh() {
    loadDashboard(true);
  }


  /* ==========================================================
     ALERT CLICK
     ========================================================== */

  function handleAlertClick(alert) {
    if (alert.device_id) {
      navigate(
        `/devices/${alert.device_id}`
      );

      return;
    }

    if (alert.camera_id) {
      navigate(
        `/cameras/${alert.camera_id}`
      );
    }
  }


  /* ==========================================================
     LOCATION CLICK
     ========================================================== */

  function handleLocationClick(location) {
    if (!location?.id) {
      return;
    }

    navigate(
      `/locations/${location.id}`
    );
  }


  /* ==========================================================
     LOADING
     ========================================================== */

  if (loading && !dashboard) {
    return (
      <div className="dashboard-page">

        <header className="page-header">
          <div>
            <p className="page-eyebrow">
              Monitoring
            </p>

            <h1>
              Dashboard
            </h1>
          </div>
        </header>

        <div className="dashboard-empty">
          Loading dashboard...
        </div>

      </div>
    );
  }


  /* ==========================================================
     ERROR
     ========================================================== */

  if (error && !dashboard) {
    return (
      <div className="dashboard-page">

        <header className="page-header">

          <div>
            <p className="page-eyebrow">
              Monitoring
            </p>

            <h1>
              Dashboard
            </h1>
          </div>

          <button
            className="primary-button"
            onClick={() => loadDashboard()}
          >
            Retry
          </button>

        </header>

        <div className="dashboard-error">
          {error}
        </div>

      </div>
    );
  }


  /* ==========================================================
     DATA
     ========================================================== */

  const summary =
    dashboard?.summary ?? {};

  const recentAlerts =
    dashboard?.recent_alerts ?? [];

  const locationsWithProblems =
    dashboard?.locations_with_problems ?? [];


  /* ==========================================================
     SUMMARY CARDS
     ========================================================== */

  const summaryCards = [
    {
      label: "Dispositivos",
      value: summary.devices ?? 0,
      description: "Total de dispositivos",
    },
    {
      label: "Online",
      value: summary.online ?? 0,
      description: "Dispositivos online",
    },
    {
      label: "Offline",
      value: summary.offline ?? 0,
      description: "Dispositivos offline",
    },
    {
      label: "Câmaras",
      value: summary.cameras ?? 0,
      description: "Câmaras registadas",
    },
  ];


  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <div className="dashboard-page">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <header className="page-header">

        <div>
          <p className="page-eyebrow">
            Monitoring
          </p>

          <h1>
            Dashboard
          </h1>
        </div>

        <button
          className="primary-button"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing
            ? "Refreshing..."
            : "Refresh"}
        </button>

      </header>


      {/* ======================================================
          ERROR
          ====================================================== */}

      {error && (
        <div className="dashboard-error">
          {error}
        </div>
      )}


      {/* ======================================================
          SUMMARY
          ====================================================== */}

      <section className="summary-grid">

        {summaryCards.map((card) => (
          <article
            className="summary-card"
            key={card.label}
          >

            <span className="summary-card-label">
              {card.label}
            </span>

            <strong className="summary-card-value">
              {card.value}
            </strong>

            <span className="summary-card-description">
              {card.description}
            </span>

          </article>
        ))}

      </section>


      {/* ======================================================
          DASHBOARD PANELS
          ====================================================== */}

      <section className="dashboard-grid">

        {/* ====================================================
            RECENT ALERTS
            ==================================================== */}

        <article className="dashboard-panel">

          <div className="panel-header">

            <div>
              <p className="panel-eyebrow">
                Monitoring
              </p>

              <h2>
                Recent Alerts
              </h2>
            </div>

            <button
              type="button"
              className="text-button"
              onClick={() =>
                navigate("/alerts")
              }
            >
              See All
            </button>

          </div>


          <div className="alert-list">

            {recentAlerts.length === 0 ? (

              <div className="dashboard-empty">
                No active alerts.
              </div>

            ) : (

              recentAlerts.map((alert) => {

                /*
                 * Support both possible API formats:
                 *
                 * device / device_name
                 * camera / camera_name
                 * location / location_name
                 */

                const deviceName =
                  alert.device ??
                  alert.device_name ??
                  "Unknown device";

                const cameraName =
                  alert.camera ??
                  alert.camera_name;

                const locationName =
                  alert.location ??
                  alert.location_name ??
                  "—";

                const alertType =
                  alert.type ??
                  alert.alert_type;

                const severity =
                  alert.severity ??
                  "WARNING";

                const dotStatus =
                  severity === "CRITICAL"
                    ? "critical"
                    : severity === "WARNING"
                    ? "warning"
                    : "info";

                return (
                  <button
                    type="button"
                    className="alert-row"
                    key={alert.id}
                    onClick={() =>
                      handleAlertClick(alert)
                    }
                  >

                    <div className="alert-row-main">

                      <StatusDot
                        status={dotStatus}
                      />

                      <div>

                        <strong>
                          {cameraName ??
                            deviceName}
                        </strong>

                        <span>
                          {locationName}
                        </span>

                      </div>

                    </div>


                    <div className="alert-row-meta">

                      <span>
                        {formatAlertType(
                          alertType
                        )}
                      </span>

                      <time>
                        {formatTime(
                          alert.created_at
                        )}
                      </time>

                    </div>

                  </button>
                );
              })

            )}

          </div>

        </article>


        {/* ====================================================
            LOCATIONS WITH PROBLEMS
            ==================================================== */}

        <article className="dashboard-panel">

          <div className="panel-header">

            <div>

              <p className="panel-eyebrow">
                Locations
              </p>

              <h2>
                Locations with problems
              </h2>

            </div>

            <button
              type="button"
              className="text-button"
              onClick={() =>
                navigate("/locations")
              }
            >
              See All
            </button>

          </div>


          <div className="installation-list">

            {locationsWithProblems.length === 0 ? (

              <div className="dashboard-empty">
                No locations with problems.
              </div>

            ) : (

              locationsWithProblems.map(
                (location) => {

                  const problemCount =
                    location.problem_count ??
                    location.offline_devices ??
                    0;

                  return (
                    <button
                      type="button"
                      className="installation-row"
                      key={location.id}
                      onClick={() =>
                        handleLocationClick(
                          location
                        )
                      }
                    >

                      <div className="installation-name">

                        <StatusDot
                          status={
                            location.status ??
                            "offline"
                          }
                        />

                        <strong>
                          {location.name}
                        </strong>

                      </div>


                      <span>
                        {problemCount}{" "}
                        {problemCount === 1
                          ? "problem"
                          : "problems"}
                      </span>

                    </button>
                  );
                }
              )

            )}

          </div>

        </article>

      </section>

    </div>
  );
}


export default Dashboard;