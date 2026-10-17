import { SCOPE } from "../../utils/scope";
import "./view-toggle.css";

// button pair that switches between showing only active records or all of them
function ScopeToggle({ scope, onChange }) {
  return (
    <div className="view-toggle" role="group" aria-label="Which items to show">
      <button
        type="button"
        className={`view-toggle-option ${scope === SCOPE.ACTIVE ? "active" : ""}`}
        onClick={() => onChange(SCOPE.ACTIVE)}
      >
        Active only
      </button>
      <button
        type="button"
        className={`view-toggle-option ${scope === SCOPE.ALL ? "active" : ""}`}
        onClick={() => onChange(SCOPE.ALL)}
      >
        All
      </button>
    </div>
  );
}

export default ScopeToggle;
