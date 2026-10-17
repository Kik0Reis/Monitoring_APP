import { useNavigate } from "react-router-dom";

import DataTable from "../../components/common/DataTable";
import PageHeader from "../../components/common/PageHeader";
import Pagination from "../../components/common/Pagination";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import SearchBar from "../../components/common/SearchBar";
import ViewToggle from "../../components/common/ViewToggle";
import ResourceModal from "../../components/crud/ResourceModal";
import RowActions from "../../components/crud/RowActions";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { countriesApi } from "../../services/api";

const EMPTY_FORM = { name: "", code: "" };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Portugal" },
  { name: "code", label: "Code", type: "text", placeholder: "PT", maxLength: 2 },
];

// the list of countries
function CountriesPage() {
  const navigate = useNavigate();
  const rollup = useMonitorRollup();

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
    { key: "customers_count", header: "Clients", render: (row) => row.customers_count ?? 0 },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("country", row.id)} /> },
  ];

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

      <SearchBar value={resource.search} onChange={resource.setSearch} placeholder="Search country..." />

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading countries..."
        emptyMessage="No countries found."
        onRowClick={(country) => navigate(`/countries/${country.id}`)}
        actions={(country) => <RowActions item={country} resource={resource} />}
      />

      <Pagination {...resource.pagination} />

      <ResourceModal
        resource={resource}
        entity="Country"
        fields={FORM_FIELDS}
        details={(country) => [
          ["Name", country.name],
          ["Code", country.code],
          ["Clients", country.customers_count ?? 0],
        ]}
      />
    </div>
  );
}

export default CountriesPage;
