import { useNavigate } from "react-router-dom";

import PageHeader from "../../components/common/PageHeader";
import ScopeToggle from "../../components/common/ScopeToggle";
import ViewToggle from "../../components/common/ViewToggle";
import { useScope } from "../../hooks/useScope";
import IndicatorsTable from "./components/IndicatorsTable";
import TreeNode from "./components/TreeNode";
import { DETAIL_PATH, nodeKey } from "./treeUtils";
import { useMonitorTree } from "./useMonitorTree";

import "./MonitorViews.css";

// the tree of countries, customers, locations, devices and cameras with a status dot on every node
function MonitorViewsPage() {
  const navigate = useNavigate();
  const [scope, setScope] = useScope();
  const { tree, error, expanded, toggleNode, expandAll, collapseAll, lastUpdated, refreshing, refresh } =
    useMonitorTree(scope);

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
        <ScopeToggle scope={scope} onChange={setScope} />
        <button type="button" className="text-button" onClick={expandAll}>
          Expand all
        </button>
        <button type="button" className="text-button" onClick={collapseAll}>
          Collapse all
        </button>
      </PageHeader>

      {error && <div className="error-message">{error}</div>}

      <IndicatorsTable scope={scope} />

      <div className="tree-container">
        {!tree || tree.length === 0 ? (
          <div className="dashboard-empty">No countries yet.</div>
        ) : (
          tree.map((country) => (
            <TreeNode
              key={nodeKey(country)}
              node={country}
              depth={0}
              expanded={expanded}
              onToggle={toggleNode}
              onOpen={(node) => navigate(DETAIL_PATH[node.type](node.id))}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default MonitorViewsPage;
