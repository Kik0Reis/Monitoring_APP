import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { locationsApi, customersApi, fetchAll } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import SearchBar from "../../components/common/SearchBar";
import DataTable from "../../components/common/DataTable";
import Pagination from "../../components/common/Pagination";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import CrudModal from "../../components/crud/CrudModal";

import "./Locations.css";

const EMPTY_FORM = {
  name: "",
  description: "",
  customer_id: "",
  active: true,
};

function Locations() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [customerFilter, setCustomerFilter] = useState("");

  useEffect(() => {
    fetchAll(customersApi.list).then(setCustomers).catch(() => {});
  }, []);

  const resource = useCrudResource({
    api: locationsApi,
    emptyFormData: EMPTY_FORM,
    filters: { customer: customerFilter },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      description: formData.description.trim(),
      customer_id: formData.customer_id,
      active: Boolean(formData.active),
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      description: item.description,
      customer_id: item.customer?.id ?? "",
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Location name is required.";
      if (!formData.customer_id) return "Client is required.";
      return null;
    },
  });

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(resource.reload);

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Warehouse #3" },
      {
        name: "customer_id",
        label: "Client",
        type: "select",
        options: customers.map((c) => ({ value: c.id, label: c.name })),
      },
      { name: "description", label: "Description", type: "textarea" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [customers]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          <span className="entity-subtext">{row.customer?.name}</span>
        </span>
      ),
    },
    {
      key: "devices_count",
      header: "Devices",
      render: (row) => row.devices_count ?? 0,
    },
    {
      key: "active",
      header: "Status",
      render: (row) => <StatusBadge status={row.active ? "active" : "inactive"} />,
    },
  ];

  return (
    <div className="page locations">
      <PageHeader
        eyebrow="Management"
        title="Locations"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <button className="primary-button" onClick={() => resource.openCreate()}>
          + Add Location
        </button>
      </PageHeader>

      <div className="filter-bar">
        <SearchBar
          value={resource.search}
          onChange={resource.setSearch}
          placeholder="Search locations..."
        />

        <select
          className="filter-select"
          value={customerFilter}
          onChange={(event) => setCustomerFilter(event.target.value)}
        >
          <option value="">All clients</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </select>
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading locations..."
        emptyMessage="No locations found."
        onRowClick={(location) => navigate(`/locations/${location.id}`)}
        actions={(location) => (
          <>
            <button
              className="icon-button"
              aria-label={`View ${location.name}`}
              onClick={() => resource.openView(location)}
            >
              👁
            </button>
            <button
              className="icon-button"
              aria-label={`Edit ${location.name}`}
              onClick={() => resource.openEdit(location)}
            >
              ✎
            </button>
            <button
              className="icon-button danger"
              aria-label={`Delete ${location.name}`}
              onClick={() => resource.handleDelete(location)}
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
              ? "Add Location"
              : resource.modalMode === "edit"
              ? "Edit Location"
              : "Location Details"
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
                <span>Client</span>
                <strong>{resource.selected?.customer?.name}</strong>
              </div>
              <div className="crud-detail">
                <span>Devices</span>
                <strong>{resource.selected?.devices_count ?? 0}</strong>
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

export default Locations;
