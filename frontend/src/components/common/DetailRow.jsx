// a row with a label on the left and the value on the right, used inside the detail cards
// bare puts the children as they are, for values that are already a badge
function DetailRow({ label, children, bare = false }) {
  return (
    <div className="component-detail-row">
      <span>{label}</span>
      {bare ? children : <strong>{children}</strong>}
    </div>
  );
}

export default DetailRow;
