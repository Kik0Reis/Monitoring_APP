// shown when the record of a detail page does not exist
function NotFound({ entity }) {
  return (
    <div className="page">
      <p className="dashboard-error">{entity} not found.</p>
    </div>
  );
}

export default NotFound;
