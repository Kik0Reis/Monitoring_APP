import { useEffect, useState } from "react";
import { countriesApi } from "../../services/api";
import "./countries.css";
import CrudModal from "../../components/crud/CrudModal";

function Countries() {
  const [countries, setCountries] = useState([]);

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selectedCountry, setSelectedCountry] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    code: "",
  });

  const [saving, setSaving] = useState(false);

  // ========================================================================
  // Load countries
  // ========================================================================

  async function loadCountries() {
    try {
      setLoading(true);
      setError("");

      const query = search
        ? `?search=${encodeURIComponent(search)}`
        : "";

      const data = await countriesApi.list(query);

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

  // ========================================================================
  // Search
  // ========================================================================

  function handleSearchChange(event) {
    setSearch(event.target.value);
  }

  // ========================================================================
  // Create
  // ========================================================================

  function openCreateModal() {
    setSelectedCountry(null);

    setFormData({
      name: "",
      code: "",
    });

    setError("");
    setModalMode("create");
  }

  // ========================================================================
  // View
  // ========================================================================

  function openViewModal(country) {
    setSelectedCountry(country);
    setError("");
    setModalMode("view");
  }

  // ========================================================================
  // Edit
  // ========================================================================

  function openEditModal(country) {
    setSelectedCountry(country);

    setFormData({
      name: country.name,
      code: country.code,
    });

    setError("");
    setModalMode("edit");
  }

  // ========================================================================
  // Close modal
  // ========================================================================

  function closeModal() {
    if (saving) {
      return;
    }

    setModalMode(null);
    setSelectedCountry(null);

    setFormData({
      name: "",
      code: "",
    });
  }

  // ========================================================================
  // Form
  // ========================================================================

  function handleFormChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  // ========================================================================
  // Submit create/edit
  // ========================================================================

  async function handleSubmit() {
    if (!formData.name.trim()) {
      setError("Country name is required.");
      return;
    }

    if (!formData.code.trim()) {
      setError("Country code is required.");
      return;
    }

    try {
      setSaving(true);
      setError("");

      const payload = {
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
      };

      // --------------------------------------------------------------
      // CREATE
      // --------------------------------------------------------------

      if (modalMode === "create") {
        await countriesApi.create(payload);
      }

      // --------------------------------------------------------------
      // EDIT
      // --------------------------------------------------------------

      if (modalMode === "edit") {
        await countriesApi.update(
          selectedCountry.id,
          payload
        );
      }

      // --------------------------------------------------------------
      // Close modal
      // --------------------------------------------------------------

      setModalMode(null);
      setSelectedCountry(null);

      setFormData({
        name: "",
        code: "",
      });

      // --------------------------------------------------------------
      // Reload from backend
      // --------------------------------------------------------------

      await loadCountries();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // ========================================================================
  // Delete
  // ========================================================================

  async function handleDelete(country) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${country.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await countriesApi.delete(country.id);

      await loadCountries();
    } catch (err) {
      setError(err.message);
    }
  }

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="countries">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Management</p>
          <h1>Countries</h1>
        </div>

        <button
          className="primary-button"
          onClick={openCreateModal}
        >
          + Add Country
        </button>
      </header>

      {/* Search */}

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search country..."
          value={search}
          onChange={handleSearchChange}
        />
      </div>

      {/* Error */}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Table */}

      <div className="table-card">
        <table className="countries-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th className="actions-col">
                Actions
              </th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={3}
                  className="empty-row"
                >
                  Loading countries...
                </td>
              </tr>
            ) : countries.length === 0 ? (
              <tr>
                <td
                  colSpan={3}
                  className="empty-row"
                >
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

                    {/* VIEW */}

                    <button
                      className="icon-button"
                      aria-label={`View ${country.name}`}
                      onClick={() =>
                        openViewModal(country)
                      }
                    >
                      👁
                    </button>

                    {/* EDIT */}

                    <button
                      className="icon-button"
                      aria-label={`Edit ${country.name}`}
                      onClick={() =>
                        openEditModal(country)
                      }
                    >
                      ✎
                    </button>

                    {/* DELETE */}

                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${country.name}`}
                      onClick={() =>
                        handleDelete(country)
                      }
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

      {/* ================================================================== */}
      {/* CRUD MODAL */}
      {/* ================================================================== */}

      {modalMode && (
        <CrudModal
          mode={modalMode}
          title={
            modalMode === "create"
              ? "Add Country"
              : modalMode === "edit"
              ? "Edit Country"
              : "Country Details"
          }
          onClose={closeModal}
          onSubmit={handleSubmit}
          loading={saving}
        >
          {modalMode === "view" ? (
            <div className="crud-details">

              <div className="crud-detail">
                <span>Name</span>
                <strong>
                  {selectedCountry?.name}
                </strong>
              </div>

              <div className="crud-detail">
                <span>Code</span>
                <strong>
                  {selectedCountry?.code}
                </strong>
              </div>

              <div className="crud-detail">
                <span>ID</span>
                <strong>
                  {selectedCountry?.id}
                </strong>
              </div>

            </div>
          ) : (
            <div className="crud-form">

              <div className="form-field">
                <label htmlFor="country-name">
                  Name
                </label>

                <input
                  id="country-name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="Portugal"
                  disabled={saving}
                />
              </div>

              <div className="form-field">
                <label htmlFor="country-code">
                  Code
                </label>

                <input
                  id="country-code"
                  name="code"
                  type="text"
                  maxLength={2}
                  value={formData.code}
                  onChange={handleFormChange}
                  placeholder="PT"
                  disabled={saving}
                />
              </div>

            </div>
          )}
        </CrudModal>
      )}
    </div>
  );
}

export default Countries;