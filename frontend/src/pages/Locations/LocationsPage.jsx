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
import { customersApi, locationsApi } from "../../services/api";

const EMPTY_FORM = { name: "", description: "", customer_id: "", active: true };

// the list of locations
function LocationsPage() {
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const customers = useOptions(customersApi.list);
  const [customerFilter, setCustomerFilter] = useState("");

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

  const customerOptions = useMemo(
    () => customers.map((customer) => ({ value: customer.id, label: customer.name })),
    [customers]
  );

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Warehouse #3" },
      { name: "customer_id", label: "Client", type: "select", options: customerOptions },
      { name: "description", label: "Description", type: "textarea" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [customerOptions]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          <span className="entity-subtext">{row.customer?.name}</span>
        </span>
      ),
    },
    { key: "devices_count", header: "Devices", render: (row) => row.devices_count ?? 0 },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("location", row.id)} /> },
    { key: "active", header: "Status", render: (row) => <ActiveBadge active={row.active} /> },
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
        <SearchBar value={resource.search} onChange={resource.setSearch} placeholder="Search locations..." />
        <FilterSelect value={customerFilter} onChange={setCustomerFilter} allLabel="All clients" options={customerOptions} />
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading locations..."
        emptyMessage="No locations found."
        onRowClick={(location) => navigate(`/locations/${location.id}`)}
        actions={(location) => <RowActions item={location} resource={resource} />}
      />

      <Pagination {...resource.pagination} />

      <ResourceModal
        resource={resource}
        entity="Location"
        fields={formFields}
        details={(location) => [
          ["Name", location.name],
          ["Client", location.customer?.name],
          ["Devices", location.devices_count ?? 0],
          ["Description", location.description || "—"],
          ["Status", location.active ? "Active" : "Inactive"],
        ]}
      />
    </div>
  );
}

export default LocationsPage;
