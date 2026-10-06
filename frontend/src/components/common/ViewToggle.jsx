import { useNavigate } from "react-router-dom";

import "./view-toggle.css";

/**
 * Lets the person switch between the two ways of browsing the
 * Country > Customer > Location > Device > Camera hierarchy:
 *   - "tree": Monitor > Views, everything expands inline on one page.
 *   - "drilldown": the original Countries/Clients/Locations list pages,
 *     navigating one level at a time.
 * Rendered in the page header on both sides so either one is always a
 * click away.
 */
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
