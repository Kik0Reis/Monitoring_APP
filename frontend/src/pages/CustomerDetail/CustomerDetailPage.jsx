import { useNavigate, useParams } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import PageHeader from "../../components/common/PageHeader";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import ChildrenTable from "../../components/crud/ChildrenTable";
import ResourceModal from "../../components/crud/ResourceModal";
import DetailSummary from "../../components/detail/DetailSummary";
import NotFound from "../../components/detail/NotFound";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useRecord } from "../../hooks/useRecord";
import { customersApi, locationsApi } from "../../services/api";

const EMPTY_FORM = { name: "", description: "", active: true };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Warehouse #3" },
  { name: "description", label: "Description", type: "textarea" },
  { name: "active", label: "Active", type: "checkbox" },
];

// the page of one client with its locations
function CustomerDetailPage() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const { record: customer, notFound, lastUpdated, refreshing, refresh, approve } = useRecord(customersApi, customerId);

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
    mapItemToFormData: (item) => ({ name: item.name, description: item.description, active: item.active }),
    validate: (formData) => (formData.name.trim() ? null : "Location name is required."),
  });

  if (notFound) {
    return <NotFound entity="Client" />;
  }

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
    { key: "devices_count", header: "Devices", render: (row) => row.devices_count ?? 0 },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("location", row.id)} /> },
    { key: "active", header: "Status", render: (row) => <ActiveBadge active={row.active} /> },
  ];

  return (
    <div className="page">
      <Breadcrumbs trail={customer?.breadcrumb?.slice(0, -1)} trailingLabel={customer?.name ?? "..."} />

      <PageHeader
        eyebrow="Client"
        title={customer?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {customer?.pending_review && (
          <button className="secondary-button" onClick={approve}>
            Approve
          </button>
        )}
      </PageHeader>

      {customer && (
        <DetailSummary
          title={customer.name}
          badges={
            <>
              <ActiveBadge active={customer.active} />
              {customer.pending_review && <PendingReviewBadge />}
              <RollupIndicator node={rollup.get("customer", customer.id)} showLabel />
            </>
          }
          meta={[
            { label: "Country", value: customer.country?.name },
            { label: "Locations", value: customer.locations_count ?? 0 },
            customer.description && { label: "Description", value: customer.description },
          ]}
        />
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Locations of {customer?.name}</h3>
          <button className="primary-button" onClick={() => locations.openCreate()}>
            + Add Location
          </button>
        </div>

        <ChildrenTable
          resource={locations}
          columns={columns}
          loadingMessage="Loading locations..."
          emptyMessage="No locations for this client yet."
          onRowClick={(location) => navigate(`/locations/${location.id}`)}
        />
      </section>

      <ResourceModal resource={locations} entity="Location" fields={FORM_FIELDS} />
    </div>
  );
}

export default CustomerDetailPage;
