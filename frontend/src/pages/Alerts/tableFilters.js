// the value of a row for a column, used by the text and select filters
export function columnValue(column, row) {
  return column.value ? column.value(row) : "";
}

// returns true when a value is empty, empty values always go to the bottom when sorting
export function isEmpty(value) {
  return value === null || value === undefined || value === "";
}

// compares two values, numbers as numbers and text with numbers inside ordered naturally
export function compareValues(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

// returns true when a column filter has something selected
export function isFilterActive(filter) {
  if (!filter) return false;
  if (Array.isArray(filter)) return filter.length > 0;
  if (typeof filter === "string") return filter !== "";
  return Boolean(filter.from || filter.to);
}

// returns true when a value is inside a from/to range, an empty side is not checked
function inRange(value, { from, to }) {
  if (from && (!value || value < from)) return false;
  if (to && (!value || value > to)) return false;
  return true;
}

// returns true when a row passes the filter of one column
function matchesFilter(column, row, filter) {
  if (!isFilterActive(filter)) return true;

  switch (column.filter) {
    case "text":
      return String(columnValue(column, row)).toLowerCase().includes(filter.toLowerCase());
    case "select":
      return columnValue(column, row) === filter;
    case "multiselect":
      return filter.includes(columnValue(column, row));
    case "date":
      return inRange(row.dateKey, filter);
    case "time":
      return inRange(row.timeKey.slice(0, 5), filter);
    default:
      return true;
  }
}

// returns the rows that pass every filter, sorted by the chosen column
export function filterAndSort(rows, columns, filters, sort) {
  const filtered = rows.filter((row) => columns.every((column) => matchesFilter(column, row, filters[column.key])));

  const sortColumn = columns.find((column) => column.key === sort.key);
  if (!sortColumn) return filtered;

  const getValue = sortColumn.sortValue ?? sortColumn.value;
  const direction = sort.dir === "asc" ? 1 : -1;

  return [...filtered].sort((a, b) => {
    const valueA = getValue(a);
    const valueB = getValue(b);

    if (isEmpty(valueA) && isEmpty(valueB)) return 0;
    if (isEmpty(valueA)) return 1;
    if (isEmpty(valueB)) return -1;

    return compareValues(valueA, valueB) * direction;
  });
}

// returns the options of the dropdown filters, the values that exist in the loaded rows
export function buildSelectOptions(rows, columns) {
  const options = {};

  for (const column of columns) {
    if (column.filter !== "select" && column.filter !== "multiselect") continue;

    const values = new Set();
    for (const row of rows) {
      const value = columnValue(column, row);
      if (!isEmpty(value)) values.add(value);
    }

    options[column.key] = [...values].sort(compareValues);
  }

  return options;
}
