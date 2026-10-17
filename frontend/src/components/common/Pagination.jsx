// must match REST_FRAMEWORK PAGE_SIZE in the backend settings
const PAGE_SIZE = 10;

// first, previous, next and last page buttons with the "Showing 1-10 of 42" text, hidden when there is only one page
function Pagination({ page, setPage, count, hasNext, hasPrevious }) {
  if (count <= PAGE_SIZE) {
    return null;
  }

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, count);

  return (
    <div className="table-footer">
      <span className="results-count">
        Showing {start}-{end} of {count}
      </span>

      <div className="pagination">
        <button onClick={() => setPage(1)} disabled={page === 1}>
          «
        </button>

        <button onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={!hasPrevious}>
          ‹
        </button>

        <span className="pagination-current">
          {page} / {totalPages}
        </span>

        <button onClick={() => setPage((current) => current + 1)} disabled={!hasNext}>
          ›
        </button>

        <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>
          »
        </button>
      </div>
    </div>
  );
}

export default Pagination;
