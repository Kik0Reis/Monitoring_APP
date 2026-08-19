import { useEffect, useState } from "react";

import { countriesApi, customersApi } from "../../services/api";
import CrudModal from "../../components/crud/CrudModal";

import "./clients.css";

const PAGE_SIZE = 5;

function Clients() {
  const [clients, setClients] = useState([]);
  const [countries, setCountries] = useState([]);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    country_id: "",
    active: true,
  });

  const [saving, setSaving] = useState(false);

  // ------------------------------------------------------------------
  // Load clients
  // ------------------------------------------------------------------

  async function loadClients() {
    try {
      setLoading(true);
      setError("");

      const data = await customersApi.list(
        `?search=${encodeURIComponent(search)}`
      );

      setClients(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------------------------------------
  // Load countries for the form
  // ------------------------------------------------------------------

  async function loadCountries() {
    try {
      const data = await countriesApi.list();

      setCountries(data.results ?? data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadClients();
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    loadCountries();
  }, []);

  // ------------------------------------------------------------------
  // Search
  // ------------------------------------------------------------------

  function handleSearchChange(event) {
    setSearch(event.target.value);
    setPage(1);
  }

  // ------------------------------------------------------------------
  // Modal
  // ------------------------------------------------------------------

  function openCreateModal() {
    setSelectedClient(null);

    setFormData({
      name: "",
      description: "",
      country_id: "",
      active: true,
    });

    setModalMode("create");
  }

  function openViewModal(client) {
    setSelectedClient(client);
    setModalMode("view");
  }

  function openEditModal(client) {
    setSelectedClient(client);

    setFormData({
      name: client.name,
      description: client.description || "",
      country_id: client.country?.id || "",
      active: client.active,
    });

    setModalMode("edit");
  }

  function closeModal() {
    setModalMode(null);
    setSelectedClient(null);
  }

  // ------------------------------------------------------------------
  // Form
  // ------------------------------------------------------------------

  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit() {
    setSaving(true);
    setError("");

    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        country_id: Number(formData.country_id),
        active: formData.active,
      };

      if (modalMode === "create") {
        await customersApi.create(payload);
      }

      if (modalMode === "edit") {
        await customersApi.update(
          selectedClient.id,
          payload
        );
      }

      closeModal();

      await loadClients();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // ------------------------------------------------------------------
  // Delete
  // ------------------------------------------------------------------

  async function handleDelete(client) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${client.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await customersApi.delete(client.id);

      setClients((previous) =>
        previous.filter(
          (item) => item.id !== client.id
        )
      );
    } catch (err) {
      setError(err.message);
    }
  }

  // ------------------------------------------------------------------
  // Pagination
  // ------------------------------------------------------------------

  const totalPages = Math.max(
    1,
    Math.ceil(clients.length / PAGE_SIZE)
  );

  const start = (page - 1) * PAGE_SIZE;

  const pageItems = clients.slice(
    start,
    start + PAGE_SIZE
  );

  function goToPage(next) {
    setPage(
      Math.min(
        Math.max(next, 1),
        totalPages
      )
    );
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className="clients">

      <header className="page-header">
        <div>
          <p className="page-eyebrow">
            Management
          </p>

          <h1>Clients</h1>
        </div>

        <button
          className="primary-button"
          onClick={openCreateModal}
        >
          + Add Client
        </button>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search client..."
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

        <table className="clients-table">

          <thead>
            <tr>
              <th>Name</th>
              <th>Country</th>
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
                  Loading clients...
                </td>
              </tr>
            ) : pageItems.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="empty-row"
                >
                  No clients found.
                </td>
              </tr>
            ) : (
              pageItems.map((client) => (
                <tr
                  key={client.id}
                  onClick={() =>
                    openViewModal(client)
                  }
                  className="clickable-row"
                >

                  <td>
                    <span className="client-name">
                      {client.name}
                    </span>
                  </td>

                  <td>
                    {client.country?.name || "—"}
                  </td>

                  <td>
                    <span
                      className={`client-status ${
                        client.active
                          ? "active"
                          : "inactive"
                      }`}
                    >
                      {client.active
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </td>

                  <td
                    className="actions-col"
                    onClick={(event) =>
                      event.stopPropagation()
                    }
                  >

                    <button
                      className="icon-button"
                      aria-label={`View ${client.name}`}
                      onClick={() =>
                        openViewModal(client)
                      }
                    >
                      👁
                    </button>

                    <button
                      className="icon-button"
                      aria-label={`Edit ${client.name}`}
                      onClick={() =>
                        openEditModal(client)
                      }
                    >
                      ✎
                    </button>

                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${client.name}`}
                      onClick={() =>
                        handleDelete(client)
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
            {clients.length === 0
              ? "0 results"
              : `${start + 1}-${Math.min(
                  start + PAGE_SIZE,
                  clients.length
                )} of ${clients.length}`}
          </span>

          <div className="pagination">

            <button
              onClick={() => goToPage(1)}
              disabled={page === 1}
            >
              «
            </button>

            <button
              onClick={() => goToPage(page - 1)}
              disabled={page === 1}
            >
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

      {/* ------------------------------------------------------------ */}
      {/* Modal */}
      {/* ------------------------------------------------------------ */}

      {modalMode && (
        <CrudModal
          mode={modalMode}
          title={
            modalMode === "create"
              ? "Add Client"
              : modalMode === "edit"
              ? "Edit Client"
              : selectedClient?.name
          }
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={
            modalMode === "create"
              ? "Create Client"
              : "Save Changes"
          }
          loading={saving}
        >

          {modalMode === "view" ? (
            <div className="client-details">

              <div className="detail-field">
                <span>Name</span>
                <strong>
                  {selectedClient?.name}
                </strong>
              </div>

              <div className="detail-field">
                <span>Country</span>
                <strong>
                  {selectedClient?.country?.name || "—"}
                </strong>
              </div>

              <div className="detail-field">
                <span>Description</span>
                <strong>
                  {selectedClient?.description || "—"}
                </strong>
              </div>

              <div className="detail-field">
                <span>Status</span>
                <strong>
                  {selectedClient?.active
                    ? "Active"
                    : "Inactive"}
                </strong>
              </div>

            </div>
          ) : (
            <div className="crud-form">

              <div className="form-field">
                <label htmlFor="client-name">
                  Name
                </label>

                <input
                  id="client-name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="Client name"
                />
              </div>

              <div className="form-field">
                <label htmlFor="client-country">
                  Country
                </label>

                <select
                  id="client-country"
                  name="country_id"
                  value={formData.country_id}
                  onChange={handleFormChange}
                >
                  <option value="">
                    Select country
                  </option>

                  {countries.map((country) => (
                    <option
                      key={country.id}
                      value={country.id}
                    >
                      {country.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-field">
                <label htmlFor="client-description">
                  Description
                </label>

                <textarea
                  id="client-description"
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  placeholder="Optional description"
                  rows={4}
                />
              </div>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  name="active"
                  checked={formData.active}
                  onChange={handleFormChange}
                />

                <span>
                  Active
                </span>
              </label>

            </div>
          )}

        </CrudModal>
      )}

    </div>
  );
}

export default Clients;