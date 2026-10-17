// table used by every list and by the children tables of the detail pages
// columns: [{ key, header, render?(row), align? }], actions(row) draws a last column with the row buttons
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
  // returns the class of a cell, columns aligned to the right use the same class as the actions column
  const cellClass = (column) => (column.align === "right" ? "actions-col" : undefined);

  // a single row with a message, used while loading and when there is nothing to show
  const messageRow = (message) => (
    <tr>
      <td colSpan={columnCount} className="empty-row">
        {message}
      </td>
    </tr>
  );

  return (
    <div className="table-card">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={cellClass(column)}>
                {column.header}
              </th>
            ))}
            {actions && <th className="actions-col">Actions</th>}
          </tr>
        </thead>

        <tbody>
          {loading
            ? messageRow(loadingMessage)
            : rows.length === 0
              ? messageRow(emptyMessage)
              : rows.map((row) => (
                  <tr
                    key={getRowKey(row)}
                    className={onRowClick ? "clickable-row" : undefined}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {columns.map((column) => (
                      <td key={column.key} className={cellClass(column)}>
                        {column.render ? column.render(row) : row[column.key]}
                      </td>
                    ))}

                    {actions && (
                      <td className="actions-col" onClick={(event) => event.stopPropagation()}>
                        {actions(row)}
                      </td>
                    )}
                  </tr>
                ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
