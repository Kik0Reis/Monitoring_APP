import { useState, useMemo } from "react";
import "./countries.css";

// this will get from the api
const INITIAL_COUNTRIES = [
  { id: 1, name: "Portugal", status: "active" },
  { id: 2, name: "Spain", status: "active" },
  { id: 3, name: "France", status: "inactive" },
  { id: 4, name: "Germany", status: "active" },
  { id: 5, name: "Italy", status: "active" },
];

const PAGE_SIZE = 5;

function Countries() {
  const [countries, setCountries] = useState(INITIAL_COUNTRIES);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return countries.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [countries, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const pageItems = filtered.slice(start, start + PAGE_SIZE);

  function goToPage(next) {
    setPage(Math.min(Math.max(next, 1), totalPages));
  }

  function handleSearchChange(e) {
    setSearch(e.target.value);
    setPage(1);
  }

  function handleAddCountry() {
    // this will be a modal to add a new country
    console.log("Add country clicked");
  }

  function handleView(country) {
    console.log("View", country);
  }

  function handleEdit(country) {
    console.log("Edit", country);
  }

  function handleDelete(country) {
    setCountries((prev) => prev.filter((c) => c.id !== country.id));
  }

  return (
    <div className="countries">
      <header className="page-header">
        <h1>Countries</h1>
        <button className="primary-button" onClick={handleAddCountry}>
          + Add Country
        </button>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search country..."
          value={search}
          onChange={handleSearchChange}
        />
        <span className="search-caret">⌄</span>
      </div>

      <div className="table-card">
        <table className="countries-table">
          <thead>
            <tr>
              <th>Name</th>
              <th className="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 ? (
              <tr>
                <td colSpan={2} className="empty-row">
                  No countries found.
                </td>
              </tr>
            ) : (
              pageItems.map((country) => (
                <tr key={country.id}>
                  <td>
                    <span className="country-name">{country.name}</span>
                    <span
                      className={`status-dot ${
                        country.status === "active" ? "active" : "inactive"
                      }`}
                    />
                  </td>
                  <td className="actions-col">
                    <button
                      className="icon-button"
                      aria-label={`View ${country.name}`}
                      onClick={() => handleView(country)}
                    >
                      👁
                    </button>
                    <button
                      className="icon-button"
                      aria-label={`Edit ${country.name}`}
                      onClick={() => handleEdit(country)}
                    >
                      ✎
                    </button>
                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${country.name}`}
                      onClick={() => handleDelete(country)}
                    >
                      🗑
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        <div className="table-footer">
          <span className="results-count">
            {filtered.length === 0
              ? "0 results"
              : `${start + 1}-${Math.min(
                  start + PAGE_SIZE,
                  filtered.length
                )} of ${filtered.length}`}
          </span>
          <div className="pagination">
            <button onClick={() => goToPage(1)} disabled={page === 1}>
              «
            </button>
            <button onClick={() => goToPage(page - 1)} disabled={page === 1}>
              ‹
            </button>
            <button
              onClick={() => goToPage(page + 1)}
              disabled={page === totalPages}
            >
              ›
            </button>
            <button
              onClick={() => goToPage(totalPages)}
              disabled={page === totalPages}
            >
              »
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Countries;
