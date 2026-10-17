import { useState } from "react";

import { DEFAULT_SORT, DESCENDING_FIRST } from "./alertColumns";

// keeps the sort and the filters of each tab, so changing tab does not lose what was set on another one
export function useTableView(tabKey) {
  const [sortByTab, setSortByTab] = useState({});
  const [filtersByTab, setFiltersByTab] = useState({});

  const sort = sortByTab[tabKey] ?? DEFAULT_SORT;
  const filters = filtersByTab[tabKey] ?? {};

  // sorts by a column, clicking the same column again reverses the order
  function toggleSort(columnKey) {
    const current = sortByTab[tabKey] ?? DEFAULT_SORT;
    const dir =
      current.key === columnKey
        ? current.dir === "asc" ? "desc" : "asc"
        : DESCENDING_FIRST.includes(columnKey) ? "desc" : "asc";

    setSortByTab((previous) => ({ ...previous, [tabKey]: { key: columnKey, dir } }));
  }

  // sets the filter of one column
  function setFilter(columnKey, value) {
    setFiltersByTab((previous) => ({
      ...previous,
      [tabKey]: { ...(previous[tabKey] ?? {}), [columnKey]: value },
    }));
  }

  // removes every filter of the tab
  function clearFilters() {
    setFiltersByTab((previous) => ({ ...previous, [tabKey]: {} }));
  }

  return { sort, filters, toggleSort, setFilter, clearFilters };
}

export default useTableView;
