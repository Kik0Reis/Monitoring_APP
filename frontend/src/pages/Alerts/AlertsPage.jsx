import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import PageHeader from "../../components/common/PageHeader";
import { alertsApi } from "../../services/api";
import { prepareRow } from "./alertRows";
import { COLUMNS, TABS } from "./alertColumns";
import AlertsTable from "./components/AlertsTable";
import { buildSelectOptions, filterAndSort, isFilterActive } from "./tableFilters";
import { useAlerts } from "./useAlerts";
import { useTableView } from "./useTableView";

import "./Alerts.css";

// the alerts page: one tab for offline problems, one for errors and one for detections
function AlertsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("offline");

  const { itemsByTab, error, setError, showHistory, setShowHistory, lastUpdated, refreshing, refresh } =
    useAlerts(activeTab);
  const { sort, filters, toggleSort, setFilter, clearFilters } = useTableView(activeTab);

  const columns = COLUMNS[activeTab];
  const tab = TABS.find((item) => item.key === activeTab);

  const allRows = useMemo(() => (itemsByTab[activeTab] ?? []).map(prepareRow), [itemsByTab, activeTab]);
  const selectOptions = useMemo(() => buildSelectOptions(allRows, columns), [allRows, columns]);
  const visibleRows = useMemo(
    () => filterAndSort(allRows, columns, filters, sort),
    [allRows, columns, filters, sort]
  );
  const activeFilterCount = columns.filter((column) => isFilterActive(filters[column.key])).length;

  // resolves an alert and reloads the lists
  async function resolveAlert(alert) {
    try {
      await alertsApi.resolveById(alert.id);
      await refresh();
    } catch (err) {
      setError(err.message || "Failed to resolve alert.");
    }
  }

  // opens the camera or the device of an alert
  function openAlert(alert) {
    if (alert.camera_id) navigate(`/cameras/${alert.camera_id}`);
    else if (alert.device_id) navigate(`/devices/${alert.device_id}`);
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
        {activeTab !== "detections" && (
          <label className="alerts-filter-toggle">
            <input type="checkbox" checked={showHistory} onChange={(event) => setShowHistory(event.target.checked)} />
            Show history
          </label>
        )}
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <div className="alerts-tabs">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`alerts-tab ${activeTab === item.key ? "active" : ""}`}
            onClick={() => setActiveTab(item.key)}
          >
            {item.label}
            <span className="alerts-tab-count">{itemsByTab[item.key]?.length ?? 0}</span>
          </button>
        ))}
      </div>

      <p className="alerts-tab-description">{tab.description}</p>

      <div className="table-card alerts-table-card">
        <div className="alerts-table-scroll">
          <AlertsTable
            columns={columns}
            rows={visibleRows}
            hasRows={allRows.length > 0}
            sort={sort}
            filters={filters}
            selectOptions={selectOptions}
            onSort={toggleSort}
            onFilter={setFilter}
            onOpen={openAlert}
            onResolve={resolveAlert}
          />
        </div>

        <div className="table-footer">
          <span className="results-count">
            Showing {visibleRows.length} of {allRows.length}
          </span>

          {activeFilterCount > 0 && (
            <button type="button" className="alerts-clear-filters" onClick={clearFilters}>
              Clear filters ({activeFilterCount})
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertsPage;
