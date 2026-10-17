import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import DataTable from "../../components/common/DataTable";
import FilterSelect from "../../components/common/FilterSelect";
import PageHeader from "../../components/common/PageHeader";
import Pagination from "../../components/common/Pagination";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import SearchBar from "../../components/common/SearchBar";
import ResourceModal from "../../components/crud/ResourceModal";
import RowActions from "../../components/crud/RowActions";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useOptions } from "../../hooks/useOptions";
import { countriesApi, customersApi } from "../../services/api";

const EMPTY_FORM = { name: "", description: "", country_id: "", active: true };

// the list of clients (customers)
function ClientsPage() {
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const countries = useOptions(countriesApi.list);
  const [countryFilter, setCountryFilter] = useState("");

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

  const countryOptions = useMemo(() => countries.map((country) => ({ value: country.id, label: country.name })), [countries]);

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Acme Corp" },
      { name: "country_id", label: "Country", type: "select", options: countryOptions },
      { name: "description", label: "Description", type: "textarea" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [countryOptions]
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
    { key: "locations_count", header: "Locations", render: (row) => row.locations_count ?? 0 },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("customer", row.id)} /> },
    { key: "active", header: "Status", render: (row) => <ActiveBadge active={row.active} /> },
  ];

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
        <SearchBar value={resource.search} onChange={resource.setSearch} placeholder="Search clients..." />
        <FilterSelect value={countryFilter} onChange={setCountryFilter} allLabel="All countries" options={countryOptions} />
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading clients..."
        emptyMessage="No clients found."
        onRowClick={(client) => navigate(`/clients/${client.id}`)}
        actions={(client) => <RowActions item={client} resource={resource} />}
      />

      <Pagination {...resource.pagination} />

      <ResourceModal
        resource={resource}
        entity="Client"
        fields={formFields}
        details={(client) => [
          ["Name", client.name],
          ["Country", client.country?.name],
          ["Locations", client.locations_count ?? 0],
          ["Description", client.description || "—"],
          ["Status", client.active ? "Active" : "Inactive"],
        ]}
      />
    </div>
  );
}

export default ClientsPage;
