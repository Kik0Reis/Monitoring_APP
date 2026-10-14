import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ExternalLink, Globe, Users, MapPin, Cpu, Camera } from "lucide-react";

import { monitorApi } from "../../services/api";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import ViewToggle from "../../components/common/ViewToggle";

import "./MonitorViews.css";

// Where "open" (the external-link icon) on each node type takes you --
// the tree is for browsing/expanding, these are the existing detail pages
// for the full record/CRUD.
const DETAIL_PATH = {
  country: (id) => `/countries/${id}`,
  customer: (id) => `/clients/${id}`,
  location: (id) => `/locations/${id}`,
  device: (id) => `/devices/${id}`,
  camera: (id) => `/cameras/${id}`,
};

const TYPE_ICON = {
  country: Globe,
  customer: Users,
  location: MapPin,
  device: Cpu,
  camera: Camera,
};

const CHILD_LABEL = {
  country: "customer",
  customer: "location",
  location: "device",
  device: "camera",
};

function nodeKey(node) {
  return `${node.type}-${node.id}`;
}

// One status circle per node, not one per signal -- red always wins
// (something in this branch is offline), then amber (an error alert
// somewhere in this branch, nothing offline), otherwise green. This is
// the same system_check/has_alerts rollup as before, just collapsed into
// a single indicator instead of two or three side by side.
function nodeStatusTone(node) {
  if (node.system_check === "red") return "critical";
  if (node.has_alerts) return "warning";
  return "ok";
}

function nodeStatusLabel(node) {
  if (node.system_check === "red") return "Issue: something in this branch is offline";
  if (node.has_alerts) return "Active error alert in this branch";
  return "All clear";
}

/** Counts every node in a subtree, one level deep, for the "3 customers"
 * kind of hint shown next to a collapsed node. */
function childSummary(node) {
  const count = node.children.length;
  if (count === 0) return null;
  const label = CHILD_LABEL[node.type];
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}

/** Table at the top of the page that explains what each indicator in the
 * tree means. The wording follows the current scope: with "Active only" the
 * colours only look at active devices/cameras, with "All" inactive ones
 * count too. */
function IndicatorsTable({ activeOnly }) {
  const scope = activeOnly ? "active " : "";

  return (
    <table className="tree-key-table">
      <thead>
        <tr>
          <th>Indicator</th>
          <th>Meaning</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <span className="tree-key-indicator">
              <span className="tree-status-dot tree-status-critical" /> Red
            </span>
          </td>
          <td>
            Offline: at least one {scope}device or camera in this branch is offline.
          </td>
        </tr>
        <tr>
          <td>
            <span className="tree-key-indicator">
              <span className="tree-status-dot tree-status-warning" /> Amber
            </span>
          </td>
          <td>
            Error: there is an active error alert on {activeOnly ? "an active " : "a "}
            device or camera in this branch (and nothing is offline).
          </td>
        </tr>
        <tr>
          <td>
            <span className="tree-key-indicator">
              <span className="tree-status-dot tree-status-ok" /> Green
            </span>
          </td>
          <td>All clear: nothing offline and no active error alerts in this branch.</td>
        </tr>
        <tr>
          <td>
            <span className="tree-key-indicator">
              <span className="tree-indicator tree-detections-badge">3</span> Detections
            </span>
          </td>
          <td>
            Number of recent detections reported by {scope}cameras in this branch.
          </td>
        </tr>
        {!activeOnly && (
          <tr>
            <td>
              <span className="tree-key-indicator">
                <span className="tree-inactive-tag">Inactive</span>
              </span>
            </td>
            <td>
              Switched off. While &quot;All&quot; is selected, inactive devices and cameras also
              count towards the colours above.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

function TreeNode({ node, depth, expanded, onToggle, onOpen }) {
  const isOpen = expanded.has(nodeKey(node));
  const hasChildren = node.children.length > 0;
  const Icon = TYPE_ICON[node.type];
  const summary = childSummary(node);

  return (
    <div className="tree-node">
      <div
        className={`tree-row ${hasChildren ? "has-children" : ""} ${node.active === false ? "inactive" : ""}`}
        style={{ paddingLeft: 12 + depth * 22 }}
        onClick={() => hasChildren && onToggle(node)}
      >
        <ChevronRight
          size={14}
          className={`tree-chevron ${isOpen ? "open" : ""} ${hasChildren ? "" : "invisible"}`}
        />

        <Icon size={14} className="tree-type-icon" />

        <span className="tree-name">{node.name}</span>

        {node.pending_review && <PendingReviewBadge />}

        {node.active === false && <span className="tree-inactive-tag">Inactive</span>}

        {summary && <span className="tree-child-summary">{summary}</span>}

        <span className="tree-indicators">
          <span
            className={`tree-indicator tree-status-dot tree-status-${nodeStatusTone(node)}`}
            title={nodeStatusLabel(node)}
          />

          {node.detections_count > 0 && (
            <span className="tree-indicator tree-detections-badge" title="Recent detections">
              {node.detections_count}
            </span>
          )}

          <button
            type="button"
            className="tree-open-button"
            title={`Open ${node.type}`}
            onClick={(event) => {
              event.stopPropagation();
              onOpen(node);
            }}
          >
            <ExternalLink size={14} />
          </button>
        </span>
      </div>

      {isOpen && hasChildren && (
        <div className="tree-children">
          {node.children.map((child) => (
            <TreeNode
              key={nodeKey(child)}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              onOpen={onOpen}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function collectAllKeys(nodes, keys) {
  for (const node of nodes) {
    keys.add(nodeKey(node));
    collectAllKeys(node.children, keys);
  }
  return keys;
}

/** Auto-expand every ancestor of a red node, so a problem is visible the
 * moment the page loads instead of being hidden a few clicks deep.
 * node.system_check already tells us the *subtree* has a problem (it's a
 * rollup), so a single top-down pass is enough: expand this node whenever
 * it's red, then recurse into its children the same way. */
function collectRedPathKeys(nodes, keys) {
  for (const node of nodes) {
    if (node.system_check === "red") {
      keys.add(nodeKey(node));
    }
    collectRedPathKeys(node.children, keys);
  }
  return keys;
}

function MonitorViews() {
  const navigate = useNavigate();

  const [tree, setTree] = useState(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(new Set());
  const [initialized, setInitialized] = useState(false);
  // "Active only" hides inactive customers/locations/devices/cameras and
  // ignores them in every colour; "All" shows them and counts them. The
  // backend does the filtering/rollup (see monitoring/services/tree.py).
  const [activeOnly, setActiveOnly] = useState(true);

  const loadTree = useCallback(async () => {
    try {
      setError("");
      const data = await monitorApi.tree({ activeOnly });
      const results = data.results ?? [];
      setTree(results);

      // First load only: start with every branch that has a problem
      // already expanded (see collectRedPathKeys), and everything else
      // collapsed down to the country level. Later auto-refreshes leave
      // whatever the person has expanded/collapsed alone.
      if (!initialized) {
        const keys = new Set();
        results.forEach((country) => keys.add(nodeKey(country)));
        collectRedPathKeys(results, keys);
        setExpanded(keys);
        setInitialized(true);
      }
    } catch (err) {
      setError(err.message || "Failed to load the monitor tree.");
    }
  }, [initialized, activeOnly]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadTree);

  // Switching scope reloads right away (the 60s timer would be too slow) and
  // re-opens the branches that have a problem in the new scope. Skipped on
  // the first render because useAutoRefresh already does the initial load.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOnly]);

  function changeScope(nextActiveOnly) {
    if (nextActiveOnly === activeOnly) return;
    setInitialized(false);
    setActiveOnly(nextActiveOnly);
  }

  function toggleNode(node) {
    setExpanded((current) => {
      const next = new Set(current);
      const key = nodeKey(node);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function openNode(node) {
    navigate(DETAIL_PATH[node.type](node.id));
  }

  function expandAll() {
    if (!tree) return;
    setExpanded(collectAllKeys(tree, new Set()));
  }

  function collapseAll() {
    if (!tree) return;
    setExpanded(new Set(tree.map((country) => nodeKey(country))));
  }

  if (!tree && !error) {
    return (
      <div className="page">
        <PageHeader eyebrow="Monitor" title="Views" />
        <div className="dashboard-loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Monitor"
        title="Views"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <ViewToggle active="tree" />
        <div className="view-toggle" role="group" aria-label="Which items to show">
          <button
            type="button"
            className={`view-toggle-option ${activeOnly ? "active" : ""}`}
            onClick={() => changeScope(true)}
          >
            Active only
          </button>
          <button
            type="button"
            className={`view-toggle-option ${!activeOnly ? "active" : ""}`}
            onClick={() => changeScope(false)}
          >
            All
          </button>
        </div>
        <button type="button" className="text-button" onClick={expandAll}>
          Expand all
        </button>
        <button type="button" className="text-button" onClick={collapseAll}>
          Collapse all
        </button>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <IndicatorsTable activeOnly={activeOnly} />

      <div className="tree-container">
        {tree.length === 0 ? (
          <div className="dashboard-empty">No countries yet.</div>
        ) : (
          tree.map((country) => (
            <TreeNode
              key={nodeKey(country)}
              node={country}
              depth={0}
              expanded={expanded}
              onToggle={toggleNode}
              onOpen={openNode}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default MonitorViews;
