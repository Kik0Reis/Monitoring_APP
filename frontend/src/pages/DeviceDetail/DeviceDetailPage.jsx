import { useNavigate, useParams } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import CollapsibleSection from "../../components/common/CollapsibleSection";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import PageHeader from "../../components/common/PageHeader";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import StatusBadge from "../../components/common/StatusBadge";
import ChildrenTable from "../../components/crud/ChildrenTable";
import ResourceModal from "../../components/crud/ResourceModal";
import AlertSections from "../../components/detail/AlertSections";
import DetailSummary from "../../components/detail/DetailSummary";
import NotFound from "../../components/detail/NotFound";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useRecord } from "../../hooks/useRecord";
import { alertsApi, camerasApi, devicesApi } from "../../services/api";
import { formatTimestamp } from "../../utils/formatTimestamp";
import { ComponentsSection, HeartbeatSection, SystemInfoSection } from "./components/DeviceSections";

const EMPTY_FORM = { name: "", camera_identifier: "", channel: 1, active: true };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text", placeholder: "Office Camera 1" },
  { name: "camera_identifier", label: "Camera Identifier", type: "text" },
  { name: "channel", label: "Channel", type: "text", placeholder: "1" },
  { name: "active", label: "Active", type: "checkbox" },
];

// returns the name of the first breadcrumb entry of a type, or a dash
function crumbName(breadcrumb, type) {
  return breadcrumb?.find((entry) => entry.type === type)?.name ?? "—";
}

// the page of one device: status, alerts, health and its cameras
function DeviceDetailPage() {
  const { deviceId } = useParams();
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const { record: device, notFound, reload, lastUpdated, refreshing, refresh, approve } = useRecord(devicesApi, deviceId);

  const cameras = useCrudResource({
    api: camerasApi,
    emptyFormData: EMPTY_FORM,
    filters: { device: deviceId },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      camera_identifier: formData.camera_identifier.trim(),
      channel: Number(formData.channel) || 1,
      active: Boolean(formData.active),
      device_id: deviceId,
    }),
    mapItemToFormData: (item) => ({
      name: item.name,
      camera_identifier: item.camera_identifier,
      channel: item.channel,
      active: item.active,
    }),
    validate: (formData) => {
      if (!formData.name.trim()) return "Camera name is required.";
      if (!formData.camera_identifier.trim()) return "Camera identifier is required.";
      return null;
    },
  });

  // resolves one alert of this device, if it fails the row just stays visible
  async function resolveAlert(alert) {
    try {
      await alertsApi.resolveDevice(alert.id);
      await reload();
    } catch {
      // nothing to do
    }
  }

  if (notFound) {
    return <NotFound entity="Device" />;
  }

  const cameraColumns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          {!row.on_mqtt && <NotOnMqttBadge />}
        </span>
      ),
    },
    { key: "channel", header: "Ch." },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "active", header: "Active", render: (row) => <ActiveBadge active={row.active} /> },
    { key: "health", header: "Health", render: (row) => <RollupIndicator node={rollup.get("camera", row.id)} /> },
    { key: "last_seen", header: "Last Seen", render: (row) => formatTimestamp(row.last_seen) },
  ];

  return (
    <div className="page">
      <Breadcrumbs trail={device?.breadcrumb?.slice(0, -1)} trailingLabel={device?.name ?? "..."} />

      <PageHeader
        eyebrow="Device"
        title={device?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {device?.pending_review && (
          <button className="secondary-button" onClick={approve}>
            Approve
          </button>
        )}
      </PageHeader>

      {device && (
        <DetailSummary
          title={device.name}
          badges={
            <>
              <StatusBadge status={device.status} />
              {device.pending_review && <PendingReviewBadge />}
              {!device.on_mqtt && <NotOnMqttBadge />}
              <RollupIndicator node={rollup.get("device", device.id)} showLabel />
            </>
          }
          meta={[
            { label: "Location", value: device.location?.name },
            { label: "Customer", value: crumbName(device.breadcrumb, "customer") },
            { label: "Country", value: crumbName(device.breadcrumb, "country") },
            { label: "Serial Number", value: device.serial_number },
            { label: "MQTT Identifier", value: device.mqtt_identifier },
            { label: "Device Type", value: device.device_type },
            { label: "Last Seen", value: formatTimestamp(device.last_seen) },
            { label: "Active", value: <ActiveBadge active={device.active} />, bare: true },
            { label: "Cameras", value: device.cameras_count ?? 0 },
          ]}
        />
      )}

      <AlertSections alerts={device?.alerts} onResolve={resolveAlert} />
      <HeartbeatSection heartbeat={device?.latest_heartbeat} />
      <ComponentsSection componentStatuses={device?.component_statuses} />
      <SystemInfoSection systemInfo={device?.system_info} />

      <CollapsibleSection
        title={`Cameras on ${device?.name ?? "..."}`}
        count={cameras.items.length}
        defaultOpen
        actions={
          <button className="primary-button" onClick={() => cameras.openCreate()}>
            + Add Camera
          </button>
        }
      >
        <ChildrenTable
          resource={cameras}
          columns={cameraColumns}
          loadingMessage="Loading cameras..."
          emptyMessage="No cameras on this device yet."
          onRowClick={(camera) => navigate(`/cameras/${camera.id}`)}
        />
      </CollapsibleSection>

      <ResourceModal resource={cameras} entity="Camera" fields={FORM_FIELDS} />
    </div>
  );
}

export default DeviceDetailPage;
