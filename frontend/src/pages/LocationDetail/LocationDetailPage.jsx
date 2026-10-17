import { useNavigate, useParams } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import PageHeader from "../../components/common/PageHeader";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import StatusBadge from "../../components/common/StatusBadge";
import ChildrenTable from "../../components/crud/ChildrenTable";
import ResourceModal from "../../components/crud/ResourceModal";
import DetailSummary from "../../components/detail/DetailSummary";
import NotFound from "../../components/detail/NotFound";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useRecord } from "../../hooks/useRecord";
import { devicesApi, locationsApi } from "../../services/api";
import { formatTimestamp } from "../../utils/formatTimestamp";

const EMPTY_FORM = { name: "", mqtt_identifier: "", serial_number: "", active: true };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Edge 01" },
  { name: "mqtt_identifier", label: "MQTT Identifier", type: "text", placeholder: "edge-01" },
  { name: "serial_number", label: "Serial Number", type: "text", placeholder: "EDGE-01" },
  { name: "active", label: "Active", type: "checkbox" },
];

// the page of one location with its devices
function LocationDetailPage() {
  const { locationId } = useParams();
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const { record: location, notFound, lastUpdated, refreshing, refresh, approve } = useRecord(locationsApi, locationId);

  const devices = useCrudResource({
    api: devicesApi,
    emptyFormData: EMPTY_FORM,
    filters: { location: locationId },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      mqtt_identifier: formData.mqtt_identifier.trim(),
      serial_number: formData.serial_number.trim(),
      active: Boolean(formData.active),
      location_id: locationId,
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      mqtt_identifier: item.mqtt_identifier,
      serial_number: item.serial_number,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Device name is required.";
      if (!formData.mqtt_identifier.trim()) return "MQTT identifier is required.";
      if (!formData.serial_number.trim()) return "Serial number is required.";
      return null;
    },
  });

  if (notFound) {
    return <NotFound entity="Location" />;
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
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "active", header: "Active", render: (row) => <ActiveBadge active={row.active} /> },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("device", row.id)} /> },
    { key: "cameras_count", header: "Cameras", render: (row) => row.cameras_count ?? 0 },
    { key: "last_seen", header: "Last Seen", render: (row) => formatTimestamp(row.last_seen) },
  ];

  return (
    <div className="page">
      <Breadcrumbs trail={location?.breadcrumb?.slice(0, -1)} trailingLabel={location?.name ?? "..."} />

      <PageHeader
        eyebrow="Location"
        title={location?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {location?.pending_review && (
          <button className="secondary-button" onClick={approve}>
            Approve
          </button>
        )}
      </PageHeader>

      {location && (
        <DetailSummary
          title={location.name}
          badges={
            <>
              <ActiveBadge active={location.active} />
              {location.pending_review && <PendingReviewBadge />}
              <RollupIndicator node={rollup.get("location", location.id)} showLabel />
            </>
          }
          meta={[
            { label: "Client", value: location.customer?.name },
            { label: "Devices", value: location.devices_count ?? 0 },
            location.description && { label: "Description", value: location.description },
          ]}
        />
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Devices at {location?.name}</h3>
          <button className="primary-button" onClick={() => devices.openCreate()}>
            + Add Device
          </button>
        </div>

        <ChildrenTable
          resource={devices}
          columns={columns}
          loadingMessage="Loading devices..."
          emptyMessage="No devices at this location yet."
          onRowClick={(device) => navigate(`/devices/${device.id}`)}
        />
      </section>

      <ResourceModal resource={devices} entity="Device" fields={FORM_FIELDS} />
    </div>
  );
}

export default LocationDetailPage;
