import { ArrowDown, ArrowUp, ArrowUpDown, X } from "lucide-react";

import FilterCell from "./FilterCell";

// the table of one tab: sortable headers, a row of filters and the alerts
function AlertsTable({ columns, rows, hasRows, sort, filters, selectOptions, onSort, onFilter, onOpen, onResolve }) {
  const hasFilters = columns.some((column) => column.filter);

  return (
    <table className="data-table alerts-table">
      <thead>
        <tr>
          {columns.map((column) => {
            const isSorted = sort.key === column.key;
            const SortIcon = !isSorted ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
            const ariaSort = isSorted ? (sort.dir === "asc" ? "ascending" : "descending") : "none";

            return (
              <th key={column.key} aria-sort={ariaSort}>
                <button
                  type="button"
                  className={`alerts-sort ${isSorted ? "active" : ""}`}
                  onClick={() => onSort(column.key)}
                >
                  {column.header}
                  <SortIcon size={12} />
                </button>
              </th>
            );
          })}
          <th className="actions-col" />
        </tr>

        {hasFilters && (
          <tr className="alerts-filter-row">
            {columns.map((column) => (
              <th key={column.key}>
                <FilterCell
                  column={column}
                  value={filters[column.key]}
                  options={selectOptions[column.key] ?? []}
                  onChange={(value) => onFilter(column.key, value)}
                />
              </th>
            ))}
            <th className="actions-col" />
          </tr>
        )}
      </thead>

      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={columns.length + 1} className="empty-row">
              {hasRows ? "No results match the filters." : "Nothing here."}
            </td>
          </tr>
        ) : (
          rows.map((row) => (
            <tr key={row.id} className="clickable-row" onClick={() => onOpen(row)}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}

              <td className="actions-col" onClick={(event) => event.stopPropagation()}>
                <button
                  type="button"
                  className="alert-row-resolve"
                  title={row.active === false ? "Already resolved" : "Mark as resolved"}
                  disabled={row.active === false}
                  onClick={() => onResolve(row)}
                >
                  <X size={14} />
                </button>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

export default AlertsTable;
