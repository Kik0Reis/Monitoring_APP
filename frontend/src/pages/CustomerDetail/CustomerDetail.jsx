import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, Pencil, Trash2 } from "lucide-react";

import { customersApi, locationsApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import CrudModal from "../../components/crud/CrudModal";

const EMPTY_FORM = { name: "", description: "", active: true };

function CustomerDetail() {
  const { customerId } = useParams();
  const navigate = useNavigate();

  const [customer, setCustomer] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const loadCustomer = useCallback(async () => {
    try {
      const data = await customersApi.get(customerId);
      setCustomer(data);
    } catch {
      setNotFound(true);
    }
  }, [customerId]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadCustomer);

  const locations = useCrudResource({
    api: locationsApi,
    emptyFormData: EMPTY_FORM,
    filters: { customer: customerId },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      description: formData.description.trim(),
      active: Boolean(formData.active),
      customer_id: customerId,
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      description: item.description,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Location name is required.";
      return null;
    },
  });

  if (notFound) {
    return (
      <div className="page">
        <p className="dashboard-error">Client not found.</p>
      </div>
    );
  }

  const formFields = [
    { name: "name", label: "Name", type: "text", placeholder: "Warehouse #3" },
    { name: "description", label: "Description", type: "textarea" },
    { name: "active", label: "Active", type: "checkbox" },
  ];

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
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

  async function handleApproveCustomer() {
    try {
      await customersApi.approve(customer.id);
      await loadCustomer();
    } catch {
      // Best-effort; the badge just stays visible if this fails.
    }
  }

  async function handleApproveLocation(item) {
    await locationsApi.approve(item.id);
    await locations.reload();
  }

  return (
    <div className="page">
      <Breadcrumbs
        trail={customer?.breadcrumb?.slice(0, -1)}
        trailingLabel={customer?.name ?? "..."}
      />

      <PageHeader
        eyebrow="Client"
        title={customer?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {customer?.pending_review && (
          <button className="secondary-button" onClick={handleApproveCustomer}>
            Approve
          </button>
        )}
      </PageHeader>

      {customer && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{customer.name}</h2>
                <StatusBadge status={customer.active ? "active" : "inactive"} />
                {customer.pending_review && <PendingReviewBadge />}
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Country</span>
                  <strong>{customer.country?.name}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Locations</span>
                  <strong>{customer.locations_count ?? 0}</strong>
                </div>
                {customer.description && (
                  <div className="detail-meta-item">
                    <span>Description</span>
                    <strong>{customer.description}</strong>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Locations of {customer?.name}</h3>
          <button className="primary-button" onClick={() => locations.openCreate()}>
            + Add Location
          </button>
        </div>

        {locations.error && <div className="error-message">{locations.error}</div>}

        <DataTable
          columns={columns}
          rows={locations.items}
          loading={locations.loading}
          loadingMessage="Loading locations..."
          emptyMessage="No locations for this client yet."
          onRowClick={(location) => navigate(`/locations/${location.id}`)}
          actions={(location) => (
            <>
              {location.pending_review && (
                <button
                  className="icon-button"
                  title="Approve"
                  onClick={() => handleApproveLocation(location)}
                >
                  <Check size={16} />
                </button>
              )}
              <button className="icon-button" onClick={() => locations.openEdit(location)}>
                <Pencil size={16} />
              </button>
              <button
                className="icon-button danger"
                onClick={() => locations.handleDelete(location)}
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        />
      </section>

      {locations.modalMode && (
        <CrudModal
          mode={locations.modalMode}
          title={locations.modalMode === "create" ? "Add Location" : "Edit Location"}
          onClose={locations.closeModal}
          onSubmit={locations.handleSubmit}
          loading={locations.saving}
        >
          <div className="crud-form">
            {formFields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={locations.formData[field.name]}
                onChange={locations.handleFormChange}
                disabled={locations.saving}
              />
            ))}
          </div>
        </CrudModal>
      )}
    </div>
  );
}

export default CustomerDetail;
