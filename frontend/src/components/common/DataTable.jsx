/**
 * Generic table: one implementation shared by every resource list and
 * every drilldown "children" table, instead of near-identical <table>
 * markup repeated on every page.
 *
 * columns: [{ key, header, render?(row), align? }]
 * actions: (row) => ReactNode, rendered in a trailing "Actions" column
 */
function DataTable({
  columns,
  rows,
  loading,
  emptyMessage = "No results found.",
  loadingMessage = "Loading...",
  onRowClick,
  actions,
  getRowKey = (row) => row.id,
}) {
  const columnCount = columns.length + (actions ? 1 : 0);

  return (
    <div className="table-card">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={column.align === "right" ? "actions-col" : undefined}
              >
                {column.header}
              </th>
            ))}
            {actions && <th className="actions-col">Actions</th>}
          </tr>
        </thead>

        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columnCount} className="empty-row">
                {loadingMessage}
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columnCount} className="empty-row">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={getRowKey(row)}
                className={onRowClick ? "clickable-row" : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={column.align === "right" ? "actions-col" : undefined}
                  >
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}

                {actions && (
                  <td
                    className="actions-col"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {actions(row)}
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
