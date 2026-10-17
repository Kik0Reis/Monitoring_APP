import { ChevronRight, ExternalLink } from "lucide-react";

import PendingReviewBadge from "../../../components/common/PendingReviewBadge";
import { ROLLUP_LABELS, rollupTone } from "../../../utils/rollup";
import { TYPE_ICON, childSummary, nodeKey } from "../treeUtils";

// one row of the tree and, when it is open, all of its children
function TreeNode({ node, depth, expanded, onToggle, onOpen }) {
  const isOpen = expanded.has(nodeKey(node));
  const hasChildren = node.children.length > 0;
  const Icon = TYPE_ICON[node.type];
  const summary = childSummary(node);
  const tone = rollupTone(node);

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
            className={`tree-indicator tree-status-dot tree-status-${tone}`}
            title={ROLLUP_LABELS[tone]}
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

export default TreeNode;
