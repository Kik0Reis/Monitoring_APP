/**
 * Shown on any Country/Customer/Location/Device that was auto-created
 * from an MQTT topic instead of created deliberately through the UI.
 * Purely informational — the record works normally either way.
 */
function PendingReviewBadge() {
  return <span className="pending-review-badge">Pending Review</span>;
}

export default PendingReviewBadge;
