import { useEffect, useState } from "react";
import { countriesApi } from "../../services/api";
import "./countries.css";

const PAGE_SIZE = 5;

function Countries() {
  const [countries, setCountries] = useState([]);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadCountries() {
    try {
      setLoading(true);
      setError("");

      const data = await countriesApi.list(
        `?search=${encodeURIComponent(search)}`
      );

      /*
       * This assumes DRF pagination is enabled, which it is
       * in your settings.
       *
       * Example response:
       *
       * {
       *   "count": 10,
       *   "next": "...",
       *   "previous": null,
       *   "results": [...]
       * }
       */

      setCountries(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCountries();
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  function handleSearchChange(e) {
    setSearch(e.target.value);
    setPage(1);
  }

  async function handleAddCountry() {
    // Modal comes next.
    console.log("Add country");
  }

  function handleView(country) {
    console.log("View", country);
  }

  function handleEdit(country) {
    console.log("Edit", country);
  }

  async function handleDelete(country) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${country.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      await countriesApi.delete(country.id);

      setCountries((prev) =>
        prev.filter((item) => item.id !== country.id)
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="countries">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Management</p>
          <h1>Countries</h1>
        </div>

        <button
          className="primary-button"
          onClick={handleAddCountry}
        >
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
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="table-card">
        <table className="countries-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th className="actions-col">Actions</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="empty-row">
                  Loading countries...
                </td>
              </tr>
            ) : countries.length === 0 ? (
              <tr>
                <td colSpan={3} className="empty-row">
                  No countries found.
                </td>
              </tr>
            ) : (
              countries.map((country) => (
                <tr key={country.id}>
                  <td>
                    <span className="country-name">
                      {country.name}
                    </span>
                  </td>

                  <td>
                    {country.code}
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
      </div>
    </div>
  );
}

export default Countries;