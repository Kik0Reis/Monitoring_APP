import { useNavigate } from "react-router-dom";
import { Check, Eye, Pencil, Trash2 } from "lucide-react";

import { countriesApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import ViewToggle from "../../components/common/ViewToggle";
import SearchBar from "../../components/common/SearchBar";
import DataTable from "../../components/common/DataTable";
import Pagination from "../../components/common/Pagination";
import FormField from "../../components/common/FormField";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import CrudModal from "../../components/crud/CrudModal";
import RollupIndicator from "../../components/common/RollupIndicator";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";

import "./Countries.css";

const EMPTY_FORM = { name: "", code: "" };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Portugal" },
  { name: "code", label: "Code", type: "text", placeholder: "PT", maxLength: 2 },
];

function Countries() {
  const navigate = useNavigate();

  const resource = useCrudResource({
    api: countriesApi,
    emptyFormData: EMPTY_FORM,
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      code: formData.code.trim().toUpperCase(),
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Country name is required.";
      if (!formData.code.trim()) return "Country code is required.";
      return null;
    },
  });

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(resource.reload);

  const rollup = useMonitorRollup();

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
    { key: "code", header: "Code" },
    {
      key: "customers_count",
      header: "Clients",
      render: (row) => row.customers_count ?? 0,
    },
    {
      key: "health",
      header: "Health",
      render: (row) => <RollupIndicator node={rollup.get("country", row.id)} />,
    },
  ];

  async function handleApprove(country) {
    try {
      await countriesApi.approve(country.id);
      await resource.reload();
    } catch (err) {
      resource.setError(err.message);
    }
  }

  return (
    <div className="page countries">
      <PageHeader
        eyebrow="Management"
        title="Countries"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <ViewToggle active="drilldown" />
        <button className="primary-button" onClick={() => resource.openCreate()}>
          + Add Country
        </button>
      </PageHeader>

      <SearchBar
        value={resource.search}
        onChange={resource.setSearch}
        placeholder="Search country..."
      />

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading countries..."
        emptyMessage="No countries found."
        onRowClick={(country) => navigate(`/countries/${country.id}`)}
        actions={(country) => (
          <>
            {country.pending_review && (
              <button
                className="icon-button"
                aria-label={`Approve ${country.name}`}
                title="Approve"
                onClick={() => handleApprove(country)}
              >
                <Check size={16} />
              </button>
            )}
            <button
              className="icon-button"
              aria-label={`View ${country.name}`}
              onClick={() => resource.openView(country)}
            >
              <Eye size={16} />
            </button>
            <button
              className="icon-button"
              aria-label={`Edit ${country.name}`}
              onClick={() => resource.openEdit(country)}
            >
              <Pencil size={16} />
            </button>
            <button
              className="icon-button danger"
              aria-label={`Delete ${country.name}`}
              onClick={() => resource.handleDelete(country)}
            >
              <Trash2 size={16} />
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
              ? "Add Country"
              : resource.modalMode === "edit"
              ? "Edit Country"
              : "Country Details"
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
                <span>Code</span>
                <strong>{resource.selected?.code}</strong>
              </div>
              <div className="crud-detail">
                <span>Clients</span>
                <strong>{resource.selected?.customers_count ?? 0}</strong>
              </div>
            </div>
          ) : (
            <div className="crud-form">
              {FORM_FIELDS.map((field) => (
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

export default Countries;
