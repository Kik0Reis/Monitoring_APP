import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import DataTable from "../../components/common/DataTable";
import FilterSelect from "../../components/common/FilterSelect";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import PageHeader from "../../components/common/PageHeader";
import Pagination from "../../components/common/Pagination";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import SearchBar from "../../components/common/SearchBar";
import StatusBadge from "../../components/common/StatusBadge";
import ResourceModal from "../../components/crud/ResourceModal";
import RowActions from "../../components/crud/RowActions";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useOptions } from "../../hooks/useOptions";
import { devicesApi, locationsApi } from "../../services/api";
import { formatTimestamp } from "../../utils/formatTimestamp";
import { STATUS_OPTIONS } from "../../utils/statusOptions";

const EMPTY_FORM = { name: "", location_id: "", mqtt_identifier: "", serial_number: "", active: true };

// the list of devices
function DevicesPage() {
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const locations = useOptions(locationsApi.list);
  const [locationFilter, setLocationFilter] = useState("");

  // the dashboard counters open this page already filtered, for example /devices?status=OFFLINE
  // the url is only read once, later filter changes are not written back to it
  const [searchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get("status") ?? "");

  const resource = useCrudResource({
    api: devicesApi,
    emptyFormData: EMPTY_FORM,
    filters: { location: locationFilter, status: statusFilter },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      location_id: formData.location_id,
      mqtt_identifier: formData.mqtt_identifier.trim(),
      serial_number: formData.serial_number.trim(),
      active: Boolean(formData.active),
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      location_id: item.location?.id ?? "",
      mqtt_identifier: item.mqtt_identifier,
      serial_number: item.serial_number,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Device name is required.";
      if (!formData.location_id) return "Location is required.";
      if (!formData.mqtt_identifier.trim()) return "MQTT identifier is required.";
      if (!formData.serial_number.trim()) return "Serial number is required.";
      return null;
    },
  });

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(resource.reload);

  const locationOptions = useMemo(
    () => locations.map((location) => ({ value: location.id, label: location.name })),
    [locations]
  );

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Edge 01" },
      { name: "location_id", label: "Location", type: "select", options: locationOptions },
      { name: "mqtt_identifier", label: "MQTT Identifier", type: "text", placeholder: "edge-01" },
      { name: "serial_number", label: "Serial Number", type: "text", placeholder: "EDGE-01" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [locationOptions]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => {
        const customer = row.breadcrumb?.find((entry) => entry.type === "customer");
        const country = row.breadcrumb?.find((entry) => entry.type === "country");

        return (
          <span className="entity-name">
            {row.name}
            {row.pending_review && <PendingReviewBadge />}
            {!row.on_mqtt && <NotOnMqttBadge />}
            <span className="entity-subtext">
              {row.location?.name}
              {customer && ` · ${customer.name}`}
              {country && ` · ${country.name}`}
            </span>
          </span>
        );
      },
    },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("device", row.id)} /> },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "active", header: "Active", render: (row) => <ActiveBadge active={row.active} /> },
    { key: "cameras_count", header: "Cameras", render: (row) => row.cameras_count ?? 0 },
    { key: "last_seen", header: "Last Seen", render: (row) => formatTimestamp(row.last_seen) },
  ];

  return (
    <div className="page devices">
      <PageHeader
        eyebrow="Management"
        title="Devices"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <button className="primary-button" onClick={() => resource.openCreate()}>
          + Add Device
        </button>
      </PageHeader>

      <div className="filter-bar">
        <SearchBar value={resource.search} onChange={resource.setSearch} placeholder="Search devices..." />
        <FilterSelect value={locationFilter} onChange={setLocationFilter} allLabel="All locations" options={locationOptions} />
        <FilterSelect value={statusFilter} onChange={setStatusFilter} allLabel="All statuses" options={STATUS_OPTIONS} />
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading devices..."
        emptyMessage="No devices found."
        onRowClick={(device) => navigate(`/devices/${device.id}`)}
        actions={(device) => <RowActions item={device} resource={resource} />}
      />

      <Pagination {...resource.pagination} />

      <ResourceModal
        resource={resource}
        entity="Device"
        fields={formFields}
        details={(device) => [
          ["Name", device.name],
          ["Location", device.location?.name],
          ["Status", device.status],
          ["MQTT Identifier", device.mqtt_identifier],
          ["Serial Number", device.serial_number],
        ]}
      />
    </div>
  );
}

export default DevicesPage;
