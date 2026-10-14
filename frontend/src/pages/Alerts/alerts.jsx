import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown, X } from "lucide-react";

import { alertsApi, detectionsApi, problemsApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import MultiSelect from "../../components/common/MultiSelect";
import PickerInput from "../../components/common/PickerInput";
import { formatDate, formatTime } from "../../utils/formatTimestamp";

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

const ALERT_TYPE_LABELS = {
  DEVICE_OFFLINE: "Offline",
  DEVICE_HEALTH: "Health",
  DEVICE_ERROR: "Error",
  MQTT_ERROR: "MQTT",
  SYSTEM_ERROR: "System",
  CAMERA_ALERT: "Camera",
  CAMERA_ERROR: "Camera Error",
  CAMERA_OFFLINE: "Camera Offline",
};

/* ---------------------------------------------------------------
   Row preparation
   --------------------------------------------------------------- */

const pad = (n) => String(n).padStart(2, "0");

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

// Detections created before the backend started exposing class_label /
// action_code / confidence only have them inside the message text:
//   Camera 'X' detected 'smoke' (action=123, confidence=0.91).
// Fall back to parsing that so old rows still fill the columns.
function parseDetectionMessage(message) {
  const text = String(message ?? "");
  return {
    detected: text.match(/detected '([^']*)'/)?.[1] ?? null,
    action: text.match(/action=([^,)]+)/)?.[1]?.trim() ?? null,
    confidence: text.match(/confidence=([^)\s]+)/)?.[1] ?? null,
  };
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function formatConfidence(value) {
  if (value === null) return "—";
  return value <= 1 ? `${Math.round(value * 100)}%` : String(value);
}

function severityDot(severity) {
  const value = String(severity ?? "WARNING").toUpperCase();
  if (value === "CRITICAL") return "critical";
  if (value === "WARNING") return "warning";
  return "info";
}

function prepareRow(item) {
  const date = parseDate(item.created_at);
  const parsed = parseDetectionMessage(item.message);

  return {
    ...item,
    dateKey: date ? `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` : "",
    timeKey: date ? `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` : "",
    dateLabel: formatDate(item.created_at),
    timeLabel: formatTime(item.created_at),
    source: item.camera_name ?? item.device_name ?? "",
    location: item.location_name ?? "",
    typeLabel: ALERT_TYPE_LABELS[item.alert_type ?? item.type] ?? item.type ?? "Alert",
    detectedValue: item.detected ?? parsed.detected ?? "",
    actionValue: String(item.action_code ?? parsed.action ?? ""),
    confidenceValue: toNumber(item.confidence ?? parsed.confidence),
    statusValue: item.active === false ? "Resolved" : "Active",
  };
}

/* ---------------------------------------------------------------
   Columns
   filter: "text" | "select" | "multiselect" | "date" | "time" | none
   value(row): used for sorting (unless sortValue) and text/select filters
   --------------------------------------------------------------- */

const DATE_COL = {
  key: "date",
  header: "Date",
  filter: "date",
  sortValue: (row) => (row.dateKey ? `${row.dateKey} ${row.timeKey}` : ""),
  render: (row) => row.dateLabel,
};

const TIME_COL = {
  key: "time",
  header: "Time",
  filter: "time",
  sortValue: (row) => row.timeKey,
  render: (row) => <time>{row.timeLabel}</time>,
};

const LOCATION_COL = {
  key: "location",
  header: "Location",
  filter: "text",
  value: (row) => row.location,
  render: (row) => row.location || "—",
};

const TYPE_COL = {
  key: "type",
  header: "Type",
  filter: "select",
  value: (row) => row.typeLabel,
  render: (row) => row.typeLabel,
};

const STATUS_COL = {
  key: "status",
  header: "Status",
  filter: "select",
  value: (row) => row.statusValue,
  render: (row) =>
    row.active === false ? (
      <span className="alert-row-resolved-tag">Resolved</span>
    ) : (
      <StatusBadge status={severityDot(row.severity)} label="Active" />
    ),
};

function sourceColumn(header) {
  return {
    key: "source",
    header,
    filter: "text",
    value: (row) => row.source,
    render: (row) => (
      <>
        <span className="entity-name">{row.source || "—"}</span>
        {row.camera_name && row.device_name && (
          <span className="entity-subtext">{row.device_name}</span>
        )}
      </>
    ),
  };
}

const COLUMNS = {
  offline: [DATE_COL, TIME_COL, sourceColumn("Camera / Device"), LOCATION_COL, TYPE_COL, STATUS_COL],
  error: [
    DATE_COL,
    TIME_COL,
    sourceColumn("Camera / Device"),
    LOCATION_COL,
    TYPE_COL,
    {
      key: "message",
      header: "Message",
      filter: "text",
      value: (row) => row.message ?? "",
      render: (row) => <span className="alerts-message">{row.message ?? "—"}</span>,
    },
    STATUS_COL,
  ],
  detections: [
    DATE_COL,
    TIME_COL,
    sourceColumn("Camera"),
    LOCATION_COL,
    {
      key: "detected",
      header: "Detected",
      filter: "multiselect",
      value: (row) => row.detectedValue,
      render: (row) =>
        row.detectedValue ? <span className="alerts-chip">{row.detectedValue}</span> : "—",
    },
    {
      key: "action",
      header: "Action",
      filter: "multiselect",
      value: (row) => row.actionValue,
      render: (row) => row.actionValue || "—",
    },
    {
      key: "confidence",
      header: "Confidence",
      sortValue: (row) => row.confidenceValue,
      render: (row) => formatConfidence(row.confidenceValue),
    },
  ],
};

/* ---------------------------------------------------------------
   Filtering / sorting
   --------------------------------------------------------------- */

function columnValue(column, row) {
  return column.value ? column.value(row) : "";
}

function matchesFilter(column, row, filter) {
  if (!filter) return true;

  if (column.filter === "text") {
    return !filter || String(columnValue(column, row)).toLowerCase().includes(filter.toLowerCase());
  }

  if (column.filter === "select") {
    return !filter || columnValue(column, row) === filter;
  }

  if (column.filter === "multiselect") {
    return filter.length === 0 || filter.includes(columnValue(column, row));
  }

  if (column.filter === "date") {
    if (filter.from && (!row.dateKey || row.dateKey < filter.from)) return false;
    if (filter.to && (!row.dateKey || row.dateKey > filter.to)) return false;
    return true;
  }

  if (column.filter === "time") {
    const hhmm = row.timeKey.slice(0, 5);
    if (filter.from && (!hhmm || hhmm < filter.from)) return false;
    if (filter.to && (!hhmm || hhmm > filter.to)) return false;
    return true;
  }

  return true;
}

function isFilterActive(filter) {
  if (!filter) return false;
  if (Array.isArray(filter)) return filter.length > 0;
  if (typeof filter === "string") return filter !== "";
  return Boolean(filter.from || filter.to);
}

function compareValues(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function isEmpty(value) {
  return value === null || value === undefined || value === "";
}

/* ---------------------------------------------------------------
   Filter cell
   --------------------------------------------------------------- */

function FilterCell({ column, value, options, onChange }) {
  if (column.filter === "text") {
    return (
      <input
        type="search"
        className="alerts-filter-input"
        placeholder="Filter…"
        aria-label={`Filter by ${column.header}`}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  if (column.filter === "select") {
    return (
      <select
        className="alerts-filter-input"
        aria-label={`Filter by ${column.header}`}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (column.filter === "multiselect") {
    return (
      <MultiSelect
        ariaLabel={`Filter by ${column.header}`}
        options={options}
        value={value ?? []}
        onChange={onChange}
      />
    );
  }

  if (column.filter === "date" || column.filter === "time") {
    // always Portuguese (dd/mm/aaaa, 24h), whatever the browser language is
    const mode = column.filter;
    const range = value ?? {};

    return (
      <div className="alerts-filter-range">
        <label className="alerts-filter-field">
          <span>From</span>
          <PickerInput
            mode={mode}
            className="alerts-filter-input"
            ariaLabel={`${column.header} from`}
            value={range.from ?? ""}
            onChange={(next) => onChange({ ...range, from: next })}
          />
        </label>
        <label className="alerts-filter-field">
          <span>To</span>
          <PickerInput
            mode={mode}
            className="alerts-filter-input"
            ariaLabel={`${column.header} to`}
            value={range.to ?? ""}
            onChange={(next) => onChange({ ...range, to: next })}
          />
        </label>
      </div>
    );
  }

  return null;
}

/* ---------------------------------------------------------------
   Page
   --------------------------------------------------------------- */

const DEFAULT_SORT = { key: "date", dir: "desc" };

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

  // Sort + filters are remembered per tab, so switching tabs doesn't
  // lose what you had set up on another one.
  const [sortByTab, setSortByTab] = useState({});
  const [filtersByTab, setFiltersByTab] = useState({});

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

  const columns = COLUMNS[activeTab];
  const sort = sortByTab[activeTab] ?? DEFAULT_SORT;
  const filters = useMemo(() => filtersByTab[activeTab] ?? {}, [filtersByTab, activeTab]);

  const allRows = useMemo(
    () => (itemsByTab[activeTab] ?? []).map(prepareRow),
    [itemsByTab, activeTab]
  );

  // Options for the dropdown filters come from the data actually loaded.
  const selectOptions = useMemo(() => {
    const result = {};
    for (const column of columns) {
      if (column.filter !== "select" && column.filter !== "multiselect") continue;
      const values = new Set();
      for (const row of allRows) {
        const value = columnValue(column, row);
        if (!isEmpty(value)) values.add(value);
      }
      result[column.key] = [...values].sort((a, b) => compareValues(a, b));
    }
    return result;
  }, [columns, allRows]);

  const visibleRows = useMemo(() => {
    const filtered = allRows.filter((row) =>
      columns.every((column) => matchesFilter(column, row, filters[column.key]))
    );

    const sortColumn = columns.find((column) => column.key === sort.key);
    if (!sortColumn) return filtered;

    const getValue = sortColumn.sortValue ?? sortColumn.value;
    const direction = sort.dir === "asc" ? 1 : -1;

    return [...filtered].sort((a, b) => {
      const va = getValue(a);
      const vb = getValue(b);
      // empty values always sink to the bottom, whatever the direction
      if (isEmpty(va) && isEmpty(vb)) return 0;
      if (isEmpty(va)) return 1;
      if (isEmpty(vb)) return -1;
      return compareValues(va, vb) * direction;
    });
  }, [allRows, columns, filters, sort]);

  const activeFilterCount = columns.filter((column) => isFilterActive(filters[column.key])).length;
  const hasFilterRow = columns.some((column) => column.filter);

  function toggleSort(key) {
    setSortByTab((prev) => {
      const current = prev[activeTab] ?? DEFAULT_SORT;
      const next =
        current.key === key
          ? { key, dir: current.dir === "asc" ? "desc" : "asc" }
          : { key, dir: key === "date" || key === "time" || key === "confidence" ? "desc" : "asc" };
      return { ...prev, [activeTab]: next };
    });
  }

  function setFilter(key, value) {
    setFiltersByTab((prev) => ({
      ...prev,
      [activeTab]: { ...(prev[activeTab] ?? {}), [key]: value },
    }));
  }

  function clearFilters() {
    setFiltersByTab((prev) => ({ ...prev, [activeTab]: {} }));
  }

  const activeTabInfo = useMemo(
    () => TABS.find((tab) => tab.key === activeTab),
    [activeTab]
  );

  const columnCount = columns.length + 1; // + resolve button column

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

      <div className="table-card alerts-table-card">
        <div className="alerts-table-scroll">
          <table className="data-table alerts-table">
            <thead>
              <tr>
                {columns.map((column) => {
                  const isSorted = sort.key === column.key;
                  const SortIcon = !isSorted ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;

                  return (
                    <th
                      key={column.key}
                      aria-sort={
                        isSorted ? (sort.dir === "asc" ? "ascending" : "descending") : "none"
                      }
                    >
                      <button
                        type="button"
                        className={`alerts-sort ${isSorted ? "active" : ""}`}
                        onClick={() => toggleSort(column.key)}
                      >
                        {column.header}
                        <SortIcon size={12} />
                      </button>
                    </th>
                  );
                })}
                <th className="actions-col" />
              </tr>

              {hasFilterRow && (
                <tr className="alerts-filter-row">
                  {columns.map((column) => (
                    <th key={column.key}>
                      <FilterCell
                        column={column}
                        value={filters[column.key]}
                        options={selectOptions[column.key] ?? []}
                        onChange={(value) => setFilter(column.key, value)}
                      />
                    </th>
                  ))}
                  <th className="actions-col" />
                </tr>
              )}
            </thead>

            <tbody>
              {visibleRows.length === 0 ? (
                <tr>
                  <td colSpan={columnCount} className="empty-row">
                    {allRows.length === 0 ? "Nothing here." : "No results match the filters."}
                  </td>
                </tr>
              ) : (
                visibleRows.map((row) => (
                  <tr key={row.id} className="clickable-row" onClick={() => handleOpen(row)}>
                    {columns.map((column) => (
                      <td key={column.key}>{column.render(row)}</td>
                    ))}

                    <td className="actions-col" onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        className="alert-row-resolve"
                        title={row.active === false ? "Already resolved" : "Mark as resolved"}
                        disabled={row.active === false}
                        onClick={() => handleResolve(row)}
                      >
                        <X size={14} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
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

export default Alerts;
