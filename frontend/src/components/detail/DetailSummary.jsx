// the box at the top of a detail page: the name with badges and a grid of label and value pairs
// meta: [{ label, value, bare }], entries that are false are skipped, bare puts the value as it is (for badges)
function DetailSummary({ title, badges, meta }) {
  return (
    <div className="detail-summary">
      <div className="detail-summary-main">
        <div>
          <div className="detail-summary-title">
            <h2>{title}</h2>
            {badges}
          </div>

          <div className="detail-summary-meta">
            {meta.filter(Boolean).map((item) => (
              <div className="detail-meta-item" key={item.label}>
                <span>{item.label}</span>
                {item.bare ? item.value : <strong>{item.value}</strong>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DetailSummary;
