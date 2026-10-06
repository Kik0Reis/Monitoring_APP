import { useCallback, useState } from "react";
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

function TreeNode({ node, depth, expanded, onToggle, onOpen }) {
  const isOpen = expanded.has(nodeKey(node));
  const hasChildren = node.children.length > 0;
  const Icon = TYPE_ICON[node.type];
  const summary = childSummary(node);

  return (
    <div className="tree-node">
      <div
        className={`tree-row ${hasChildren ? "has-children" : ""}`}
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

  const loadTree = useCallback(async () => {
    try {
      setError("");
      const data = await monitorApi.tree();
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
  }, [initialized]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadTree);

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
        <button type="button" className="text-button" onClick={expandAll}>
          Expand all
        </button>
        <button type="button" className="text-button" onClick={collapseAll}>
          Collapse all
        </button>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

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
