import { useNavigate } from "react-router-dom";

import ListModal from "../../components/common/ListModal";
import PageHeader from "../../components/common/PageHeader";
import ScopeToggle from "../../components/common/ScopeToggle";
import { alertsApi } from "../../services/api";
import PanelRows from "./components/PanelRows";
import SectionPanel from "./components/SectionPanel";
import SummaryCards from "./components/SummaryCards";
import { PANELS, PREVIEW_ROWS } from "./dashboardConfig";
import { useDashboard } from "./useDashboard";
import { useDashboardModal } from "./useDashboardModal";

// the dashboard: counters at the top and one panel per kind of problem
function DashboardPage() {
  const navigate = useNavigate();
  const { dashboard, error, setError, scope, setScope, lastUpdated, refreshing, refresh } = useDashboard();
  const modal = useDashboardModal({ dashboard, scope, onError: setError });

  // what happens when a row is clicked or resolved
  const handlers = {
    // opens the camera or the device of an alert
    openAlert: (alert) => {
      if (alert.camera_id) navigate(`/cameras/${alert.camera_id}`);
      else if (alert.device_id) navigate(`/devices/${alert.device_id}`);
    },
    // opens the page of a device
    openDevice: (device) => navigate(`/devices/${device.id}`),
    // opens the page of a location
    openLocation: (location) => navigate(`/locations/${location.id}`),
    // resolves an alert, removes it from the popup and reloads the dashboard
    resolveAlert: async (alert) => {
      try {
        await alertsApi.resolveById(alert.id);
        modal.removeItem(alert.id);
        await refresh();
      } catch (err) {
        setError(err.message || "Failed to resolve alert.");
      }
    },
  };

  if (!dashboard) {
    return (
      <div className="page dashboard">
        <PageHeader eyebrow="Monitoring" title="Dashboard">
          {error && (
            <button className="primary-button" onClick={refresh}>
              Retry
            </button>
          )}
        </PageHeader>
        {error ? <div className="dashboard-error">{error}</div> : <div className="dashboard-loading">Loading dashboard...</div>}
      </div>
    );
  }

  return (
    <div className="page dashboard">
      <PageHeader
        eyebrow="Monitoring"
        title="Dashboard"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <ScopeToggle scope={scope} onChange={setScope} />
        <button type="button" className="text-button" onClick={() => navigate("/alerts")}>
          See All
        </button>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <SummaryCards summary={dashboard.summary} />

      <section className="dashboard-grid compact-grid">
        {PANELS.map((panel) => (
          <SectionPanel
            key={panel.key}
            panel={panel}
            count={panel.count(dashboard)}
            onViewAll={() => modal.open(panel.key)}
          >
            <PanelRows panel={panel} items={dashboard[panel.preview].slice(0, PREVIEW_ROWS)} handlers={handlers} />
          </SectionPanel>
        ))}
      </section>

      {modal.panel && (
        <ListModal
          eyebrow={modal.panel.eyebrow}
          title={modal.panel.title}
          count={modal.items.length}
          onClose={modal.close}
        >
          {modal.loading ? (
            <div className="list-modal-loading">Loading...</div>
          ) : modal.items.length === 0 ? (
            <div className="list-modal-empty">Nothing here.</div>
          ) : (
            <PanelRows panel={modal.panel} items={modal.items} handlers={handlers} />
          )}
        </ListModal>
      )}
    </div>
  );
}

export default DashboardPage;
