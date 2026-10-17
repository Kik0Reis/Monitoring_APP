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
import { camerasApi, devicesApi } from "../../services/api";
import { formatTimestamp } from "../../utils/formatTimestamp";
import { STATUS_OPTIONS } from "../../utils/statusOptions";

const EMPTY_FORM = { name: "", device_id: "", camera_identifier: "", channel: 1, active: true };

// the list of cameras
function CamerasPage() {
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const devices = useOptions(devicesApi.list);
  const [deviceFilter, setDeviceFilter] = useState("");

  // the dashboard counters open this page already filtered, for example /cameras?status=OFFLINE
  // the url is only read once, later filter changes are not written back to it
  const [searchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get("status") ?? "");

  const resource = useCrudResource({
    api: camerasApi,
    emptyFormData: EMPTY_FORM,
    filters: { device: deviceFilter, status: statusFilter },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      device_id: formData.device_id,
      camera_identifier: formData.camera_identifier.trim(),
      channel: Number(formData.channel) || 1,
      active: Boolean(formData.active),
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      device_id: item.device ?? "",
      camera_identifier: item.camera_identifier,
      channel: item.channel,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Camera name is required.";
      if (!formData.device_id) return "Device is required.";
      if (!formData.camera_identifier.trim()) return "Camera identifier is required.";
      return null;
    },
  });

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(resource.reload);

  const deviceOptions = useMemo(() => devices.map((device) => ({ value: device.id, label: device.name })), [devices]);

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Office Camera 1" },
      { name: "device_id", label: "Device", type: "select", options: deviceOptions },
      { name: "camera_identifier", label: "Camera Identifier", type: "text" },
      { name: "channel", label: "Channel", type: "text", placeholder: "1" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [deviceOptions]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          {!row.on_mqtt && <NotOnMqttBadge />}
          <span className="entity-subtext">{row.device_name}</span>
        </span>
      ),
    },
    { key: "channel", header: "Ch." },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("camera", row.id)} /> },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "active", header: "Active", render: (row) => <ActiveBadge active={row.active} /> },
    { key: "last_seen", header: "Last Seen", render: (row) => formatTimestamp(row.last_seen) },
  ];

  return (
    <div className="page cameras">
      <PageHeader
        eyebrow="Management"
        title="Cameras"
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        <button className="primary-button" onClick={() => resource.openCreate()}>
          + Add Camera
        </button>
      </PageHeader>

      <div className="filter-bar">
        <SearchBar value={resource.search} onChange={resource.setSearch} placeholder="Search cameras..." />
        <FilterSelect value={deviceFilter} onChange={setDeviceFilter} allLabel="All devices" options={deviceOptions} />
        <FilterSelect value={statusFilter} onChange={setStatusFilter} allLabel="All statuses" options={STATUS_OPTIONS} />
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading cameras..."
        emptyMessage="No cameras found."
        onRowClick={(camera) => navigate(`/cameras/${camera.id}`)}
        actions={(camera) => <RowActions item={camera} resource={resource} />}
      />

      <Pagination {...resource.pagination} />

      <ResourceModal
        resource={resource}
        entity="Camera"
        fields={formFields}
        details={(camera) => [
          ["Name", camera.name],
          ["Device", camera.device_name],
          ["Channel", camera.channel],
          ["Status", camera.status],
        ]}
      />
    </div>
  );
}

export default CamerasPage;
