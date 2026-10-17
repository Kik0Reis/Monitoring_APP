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
import { countriesApi, customersApi } from "../../services/api";

const EMPTY_FORM = { name: "", description: "", active: true };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Acme Corp" },
  { name: "description", label: "Description", type: "textarea" },
  { name: "active", label: "Active", type: "checkbox" },
];

// the page of one country with its clients
function CountryDetailPage() {
  const { countryId } = useParams();
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const { record: country, notFound, lastUpdated, refreshing, refresh, approve } = useRecord(countriesApi, countryId);

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
    mapItemToFormData: (item) => ({ name: item.name, description: item.description, active: item.active }),
    validate: (formData) => (formData.name.trim() ? null : "Client name is required."),
  });

  if (notFound) {
    return <NotFound entity="Country" />;
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
    { key: "locations_count", header: "Locations", render: (row) => row.locations_count ?? 0 },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("customer", row.id)} /> },
    { key: "active", header: "Status", render: (row) => <ActiveBadge active={row.active} /> },
  ];

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
          <button className="secondary-button" onClick={approve}>
            Approve
          </button>
        )}
      </PageHeader>

      {country && (
        <DetailSummary
          title={country.name}
          badges={
            <>
              {country.pending_review && <PendingReviewBadge />}
              <RollupIndicator node={rollup.get("country", country.id)} showLabel />
            </>
          }
          meta={[
            { label: "Code", value: country.code },
            { label: "Clients", value: country.customers_count ?? 0 },
          ]}
        />
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Clients in {country?.name}</h3>
          <button className="primary-button" onClick={() => customers.openCreate()}>
            + Add Client
          </button>
        </div>

        <ChildrenTable
          resource={customers}
          columns={columns}
          loadingMessage="Loading clients..."
          emptyMessage="No clients in this country yet."
          onRowClick={(client) => navigate(`/clients/${client.id}`)}
        />
      </section>

      <ResourceModal resource={customers} entity="Client" fields={FORM_FIELDS} />
    </div>
  );
}

export default CountryDetailPage;
