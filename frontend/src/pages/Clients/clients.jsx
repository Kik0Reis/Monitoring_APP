import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { customersApi, countriesApi, fetchAll } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import SearchBar from "../../components/common/SearchBar";
import DataTable from "../../components/common/DataTable";
import Pagination from "../../components/common/Pagination";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import CrudModal from "../../components/crud/CrudModal";

import "./Clients.css";

const EMPTY_FORM = {
  name: "",
  description: "",
  country_id: "",
  active: true,
};

function Clients() {
  const navigate = useNavigate();
  const [countries, setCountries] = useState([]);
  const [countryFilter, setCountryFilter] = useState("");

  useEffect(() => {
    fetchAll(countriesApi.list).then(setCountries).catch(() => {});
  }, []);

  const resource = useCrudResource({
    api: customersApi,
    emptyFormData: EMPTY_FORM,
    filters: { country: countryFilter },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      description: formData.description.trim(),
      country_id: formData.country_id,
      active: Boolean(formData.active),
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      description: item.description,
      country_id: item.country?.id ?? "",
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Client name is required.";
      if (!formData.country_id) return "Country is required.";
      return null;
    },
  });

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(resource.reload);

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Acme Corp" },
      {
        name: "country_id",
        label: "Country",
        type: "select",
        options: countries.map((c) => ({ value: c.id, label: c.name })),
      },
      { name: "description", label: "Description", type: "textarea" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [countries]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          <span className="entity-subtext">{row.country?.name}</span>
        </span>
      ),
    },
    {
      key: "locations_count",
      header: "Locations",
      render: (row) => row.locations_count ?? 0,
    },
    {
      key: "active",
      header: "Status",
      render: (row) => <StatusBadge status={row.active ? "active" : "inactive"} />,
    },
  ];

  async function handleApprove(client) {
    try {
      await customersApi.approve(client.id);
      await resource.reload();
    } catch (err) {
      resource.setError(err.message);
    }
  }

  return (
    <div className="page clients">
      <PageHeader
        eyebrow="Management"
        title="Clients"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <button className="primary-button" onClick={() => resource.openCreate()}>
          + Add Client
        </button>
      </PageHeader>

      <div className="filter-bar">
        <SearchBar
          value={resource.search}
          onChange={resource.setSearch}
          placeholder="Search clients..."
        />

        <select
          className="filter-select"
          value={countryFilter}
          onChange={(event) => setCountryFilter(event.target.value)}
        >
          <option value="">All countries</option>
          {countries.map((country) => (
            <option key={country.id} value={country.id}>
              {country.name}
            </option>
          ))}
        </select>
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading clients..."
        emptyMessage="No clients found."
        onRowClick={(client) => navigate(`/clients/${client.id}`)}
        actions={(client) => (
          <>
            {client.pending_review && (
              <button
                className="icon-button"
                aria-label={`Approve ${client.name}`}
                title="Approve"
                onClick={() => handleApprove(client)}
              >
                ✓
              </button>
            )}
            <button
              className="icon-button"
              aria-label={`View ${client.name}`}
              onClick={() => resource.openView(client)}
            >
              👁
            </button>
            <button
              className="icon-button"
              aria-label={`Edit ${client.name}`}
              onClick={() => resource.openEdit(client)}
            >
              ✎
            </button>
            <button
              className="icon-button danger"
              aria-label={`Delete ${client.name}`}
              onClick={() => resource.handleDelete(client)}
            >
              🗑
            </button>
          </>
        )}
      />

      <Pagination
        page={resource.page}
        setPage={resource.setPage}
        count={resource.count}
        hasNext={resource.hasNext}
        hasPrevious={resource.hasPrevious}
      />

      {resource.modalMode && (
        <CrudModal
          mode={resource.modalMode}
          title={
            resource.modalMode === "create"
              ? "Add Client"
              : resource.modalMode === "edit"
              ? "Edit Client"
              : "Client Details"
          }
          onClose={resource.closeModal}
          onSubmit={resource.handleSubmit}
          loading={resource.saving}
        >
          {resource.modalMode === "view" ? (
            <div className="crud-details">
              <div className="crud-detail">
                <span>Name</span>
                <strong>{resource.selected?.name}</strong>
              </div>
              <div className="crud-detail">
                <span>Country</span>
                <strong>{resource.selected?.country?.name}</strong>
              </div>
              <div className="crud-detail">
                <span>Locations</span>
                <strong>{resource.selected?.locations_count ?? 0}</strong>
              </div>
              <div className="crud-detail">
                <span>Description</span>
                <strong>{resource.selected?.description || "—"}</strong>
              </div>
              <div className="crud-detail">
                <span>Status</span>
                <strong>{resource.selected?.active ? "Active" : "Inactive"}</strong>
              </div>
            </div>
          ) : (
            <div className="crud-form">
              {formFields.map((field) => (
                <FormField
                  key={field.name}
                  field={field}
                  value={resource.formData[field.name]}
                  onChange={resource.handleFormChange}
                  disabled={resource.saving}
                />
              ))}
            </div>
          )}
        </CrudModal>
      )}
    </div>
  );
}

export default Clients;
