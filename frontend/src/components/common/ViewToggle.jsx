import { useNavigate } from "react-router-dom";

import "./view-toggle.css";

// switches between the two ways of browsing the hierarchy
// tree view: everything opens on one page (Monitor > Views), drill down: one list page per level
function ViewToggle({ active }) {
  const navigate = useNavigate();

  return (
    <div className="view-toggle">
      <button
        type="button"
        className={`view-toggle-option ${active === "tree" ? "active" : ""}`}
        onClick={() => navigate("/monitor/views")}
      >
        Tree view
      </button>
      <button
        type="button"
        className={`view-toggle-option ${active === "drilldown" ? "active" : ""}`}
        onClick={() => navigate("/countries")}
      >
        Drill down
      </button>
    </div>
  );
}

export default ViewToggle;
