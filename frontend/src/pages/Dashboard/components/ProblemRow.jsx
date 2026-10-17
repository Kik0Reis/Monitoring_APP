import { StatusDot } from "../../../components/common/StatusBadge";

// one device or location row with what is wrong with it, used in the panel preview and in the popup
function ProblemRow({ item, status, title, onOpen }) {
  return (
    <button type="button" className="problem-row" onClick={() => onOpen(item)}>
      <div className="problem-name">
        <StatusDot status={status} />
        <strong>{title}</strong>
      </div>
      <span>{item.issues?.join(", ") || "Needs attention"}</span>
    </button>
  );
}

export default ProblemRow;
