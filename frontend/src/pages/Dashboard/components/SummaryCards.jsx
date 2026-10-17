import { useNavigate } from "react-router-dom";

import { buildSummaryCards } from "../dashboardConfig";

// the row of counters at the top, each card opens the devices or cameras list
function SummaryCards({ summary }) {
  const navigate = useNavigate();

  return (
    <section className="summary-grid">
      {buildSummaryCards(summary).map((card) => (
        <button
          type="button"
          className="summary-card summary-card-clickable"
          key={card.label}
          onClick={() => navigate(card.to)}
        >
          <span className="summary-card-label">{card.label}</span>
          <strong className="summary-card-value">{card.value}</strong>
          <span className="summary-card-description">{card.description}</span>
        </button>
      ))}
    </section>
  );
}

export default SummaryCards;
