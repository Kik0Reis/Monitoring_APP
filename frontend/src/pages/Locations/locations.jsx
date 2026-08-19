import { useEffect, useState } from "react";

import {
  locationsApi,
  customersApi,
} from "../../services/api";

import CrudModal from "../../components/crud/CrudModal";

import "./locations.css";

const PAGE_SIZE = 10;

function Locations() {
  const [locations, setLocations] = useState([]);
  const [customers, setCustomers] = useState([]);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    customer_id: "",
    active: true,
  });

  const [saving, setSaving] = useState(false);

  /*
   * Load locations
   */
  async function loadLocations() {
    try {
      setLoading(true);
      setError("");

      const params =
        `?search=${encodeURIComponent(search)}` +
        `&page=${page}`;

      const data = await locationsApi.list(params);

      setLocations(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  /*
   * Load customers for the dropdown.
   */
  async function loadCustomers() {
    try {
      const data = await customersApi.list();

      setCustomers(data.results ?? data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadLocations();
    }, 300);

    return () => clearTimeout(timer);
  }, [search, page]);

  useEffect(() => {
    loadCustomers();
  }, []);

  /*
   * Search
   */
  function handleSearchChange(event) {
    setSearch(event.target.value);
    setPage(1);
  }

  /*
   * Open create modal
   */
  function openCreateModal() {
    setSelectedLocation(null);

    setFormData({
      name: "",
      description: "",
      customer_id: "",
      active: true,
    });

    setModalMode("create");
  }

  /*
   * Open view modal
   */
  function openViewModal(location) {
    setSelectedLocation(location);
    setModalMode("view");
  }

  /*
   * Open edit modal
   */
  function openEditModal(location) {
    setSelectedLocation(location);

    setFormData({
      name: location.name || "",
      description: location.description || "",
      customer_id: location.customer?.id || "",
      active: location.active ?? true,
    });

    setModalMode("edit");
  }

  /*
   * Close modal
   */
  function closeModal() {
    setModalMode(null);
    setSelectedLocation(null);
  }

  /*
   * Form changes
   */
  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  /*
   * Create / update
   */
  async function handleSubmit() {
    setSaving(true);
    setError("");

    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        customer_id: Number(formData.customer_id),
        active: formData.active,
      };

      if (modalMode === "create") {
        await locationsApi.create(payload);
      }

      if (modalMode === "edit") {
        await locationsApi.update(
          selectedLocation.id,
          payload
        );
      }

      closeModal();

      await loadLocations();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  /*
   * Delete
   */
  async function handleDelete(location) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${location.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await locationsApi.delete(location.id);

      await loadLocations();
    } catch (err) {
      setError(err.message);
    }
  }

  /*
   * Pagination
   *
   * For now this uses the backend's page pagination.
   */
  function goToPage(nextPage) {
    if (nextPage < 1) {
      return;
    }

    setPage(nextPage);
  }

  return (
    <div className="locations">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">
            Management
          </p>

          <h1>Locations</h1>
        </div>

        <button
          className="primary-button"
          onClick={openCreateModal}
        >
          + Add Location
        </button>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search location..."
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
        <table className="locations-table">
          <thead>
            <tr>
              <th>Location</th>
              <th>Customer</th>
              <th>Status</th>
              <th className="actions-col">
                Actions
              </th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={4}
                  className="empty-row"
                >
                  Loading locations...
                </td>
              </tr>
            ) : locations.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="empty-row"
                >
                  No locations found.
                </td>
              </tr>
            ) : (
              locations.map((location) => (
                <tr
                  key={location.id}
                  onDoubleClick={() =>
                    openViewModal(location)
                  }
                >
                  <td>
                    <span className="location-name">
                      {location.name}
                    </span>
                  </td>

                  <td>
                    {location.customer?.name || "—"}
                  </td>

                  <td>
                    <span
                      className={`location-status ${
                        location.active
                          ? "active"
                          : "inactive"
                      }`}
                    >
                      <span className="status-dot" />

                      {location.active
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </td>

                  <td className="actions-col">
                    <button
                      className="icon-button"
                      aria-label={`View ${location.name}`}
                      onClick={() =>
                        openViewModal(location)
                      }
                    >
                      👁
                    </button>

                    <button
                      className="icon-button"
                      aria-label={`Edit ${location.name}`}
                      onClick={() =>
                        openEditModal(location)
                      }
                    >
                      ✎
                    </button>

                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${location.name}`}
                      onClick={() =>
                        handleDelete(location)
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

        <div className="table-footer">
          <span className="results-count">
            Page {page}
          </span>

          <div className="pagination">
            <button
              onClick={() => goToPage(page - 1)}
              disabled={page === 1}
            >
              ‹
            </button>

            <button
              onClick={() => goToPage(page + 1)}
              disabled={
                locations.length < PAGE_SIZE
              }
            >
              ›
            </button>
          </div>
        </div>
      </div>

      {modalMode && (
        <CrudModal
          mode={modalMode}
          title={
            modalMode === "create"
              ? "Add Location"
              : modalMode === "edit"
              ? "Edit Location"
              : selectedLocation?.name
          }
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={
            modalMode === "create"
              ? "Create Location"
              : "Save Changes"
          }
          loading={saving}
        >
          {modalMode === "view" ? (
            <div className="location-details">
              <div className="detail-item">
                <span>Name</span>
                <strong>
                  {selectedLocation?.name}
                </strong>
              </div>

              <div className="detail-item">
                <span>Customer</span>
                <strong>
                  {selectedLocation?.customer?.name ||
                    "—"}
                </strong>
              </div>

              <div className="detail-item">
                <span>Description</span>
                <strong>
                  {selectedLocation?.description ||
                    "—"}
                </strong>
              </div>

              <div className="detail-item">
                <span>Status</span>
                <strong>
                  {selectedLocation?.active
                    ? "Active"
                    : "Inactive"}
                </strong>
              </div>
            </div>
          ) : (
            <div className="crud-form">
              <label>
                <span>Name</span>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="Location name"
                />
              </label>

              <label>
                <span>Description</span>

                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  placeholder="Optional description"
                  rows={4}
                />
              </label>

              <label>
                <span>Customer</span>

                <select
                  name="customer_id"
                  value={formData.customer_id}
                  onChange={handleFormChange}
                >
                  <option value="">
                    Select customer
                  </option>

                  {customers.map((customer) => (
                    <option
                      key={customer.id}
                      value={customer.id}
                    >
                      {customer.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  name="active"
                  checked={formData.active}
                  onChange={handleFormChange}
                />

                <span>Active</span>
              </label>
            </div>
          )}
        </CrudModal>
      )}
    </div>
  );
}

export default Locations;