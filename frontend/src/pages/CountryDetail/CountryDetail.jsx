import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { countriesApi, customersApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import StatusBadge from "../../components/common/StatusBadge";
import CrudModal from "../../components/crud/CrudModal";

const EMPTY_FORM = { name: "", description: "", active: true };

function CountryDetail() {
  const { countryId } = useParams();
  const navigate = useNavigate();

  const [country, setCountry] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const loadCountry = useCallback(async () => {
    try {
      const data = await countriesApi.get(countryId);
      setCountry(data);
    } catch {
      setNotFound(true);
    }
  }, [countryId]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadCountry);

  const customers = useCrudResource({
    api: customersApi,
    emptyFormData: EMPTY_FORM,
    filters: { country: countryId },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      description: formData.description.trim(),
      active: Boolean(formData.active),
      country_id: countryId,
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      description: item.description,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Client name is required.";
      return null;
    },
  });

  if (notFound) {
    return (
      <div className="page">
        <p className="dashboard-error">Country not found.</p>
      </div>
    );
  }

  const formFields = [
    { name: "name", label: "Name", type: "text", placeholder: "Acme Corp" },
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

  async function handleApproveCountry() {
    try {
      await countriesApi.approve(country.id);
      await loadCountry();
    } catch {
      // Best-effort; the badge just stays visible if this fails.
    }
  }

  async function handleApproveCustomer(item) {
    await customersApi.approve(item.id);
    await customers.reload();
  }

  return (
    <div className="page">
      <Breadcrumbs trail={[]} trailingLabel={country?.name ?? "..."} />

      <PageHeader
        eyebrow="Country"
        title={country?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {country?.pending_review && (
          <button className="secondary-button" onClick={handleApproveCountry}>
            Approve
          </button>
        )}
      </PageHeader>

      {country && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{country.name}</h2>
                {country.pending_review && <PendingReviewBadge />}
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Code</span>
                  <strong>{country.code}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Clients</span>
                  <strong>{country.customers_count ?? 0}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Clients in {country?.name}</h3>
          <button className="primary-button" onClick={() => customers.openCreate()}>
            + Add Client
          </button>
        </div>

        {customers.error && <div className="error-message">{customers.error}</div>}

        <DataTable
          columns={columns}
          rows={customers.items}
          loading={customers.loading}
          loadingMessage="Loading clients..."
          emptyMessage="No clients in this country yet."
          onRowClick={(client) => navigate(`/clients/${client.id}`)}
          actions={(client) => (
            <>
              {client.pending_review && (
                <button
                  className="icon-button"
                  title="Approve"
                  onClick={() => handleApproveCustomer(client)}
                >
                  ✓
                </button>
              )}
              <button className="icon-button" onClick={() => customers.openEdit(client)}>
                ✎
              </button>
              <button
                className="icon-button danger"
                onClick={() => customers.handleDelete(client)}
              >
                🗑
              </button>
            </>
          )}
        />
      </section>

      {customers.modalMode && (
        <CrudModal
          mode={customers.modalMode}
          title={customers.modalMode === "create" ? "Add Client" : "Edit Client"}
          onClose={customers.closeModal}
          onSubmit={customers.handleSubmit}
          loading={customers.saving}
        >
          <div className="crud-form">
            {formFields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={customers.formData[field.name]}
                onChange={customers.handleFormChange}
                disabled={customers.saving}
              />
            ))}
          </div>
        </CrudModal>
      )}
    </div>
  );
}

export default CountryDetail;
