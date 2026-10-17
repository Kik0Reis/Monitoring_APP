import { useNavigate, useParams } from "react-router-dom";

import ActiveBadge from "../../components/common/ActiveBadge";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import PageHeader from "../../components/common/PageHeader";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import RollupIndicator from "../../components/common/RollupIndicator";
import StatusBadge from "../../components/common/StatusBadge";
import ResourceModal from "../../components/crud/ResourceModal";
import AlertSections from "../../components/detail/AlertSections";
import DetailSummary from "../../components/detail/DetailSummary";
import NotFound from "../../components/detail/NotFound";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { useRecord } from "../../hooks/useRecord";
import { alertsApi, camerasApi } from "../../services/api";
import { formatTimestamp } from "../../utils/formatTimestamp";
import LicenseSection from "./components/LicenseSection";

const EMPTY_FORM = { name: "", camera_identifier: "", channel: 1, active: true };

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text" },
  { name: "camera_identifier", label: "Camera Identifier", type: "text" },
  { name: "channel", label: "Channel", type: "text" },
  { name: "active", label: "Active", type: "checkbox" },
];

// the page of one camera: status, alerts, detections and license
function CameraDetailPage() {
  const { cameraId } = useParams();
  const navigate = useNavigate();
  const rollup = useMonitorRollup();
  const { record: camera, notFound, reload, lastUpdated, refreshing, refresh, approve } = useRecord(camerasApi, cameraId);

  // only used for the edit popup, the page does not need the list of cameras
  const editor = useCrudResource({
    api: camerasApi,
    autoLoad: false,
    emptyFormData: EMPTY_FORM,
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      camera_identifier: formData.camera_identifier.trim(),
      channel: Number(formData.channel) || 1,
      active: Boolean(formData.active),
      device_id: camera?.device,
    }),
  });

  // saves the edit and reloads the camera
  async function saveEdit() {
    await editor.handleSubmit();
    await reload();
  }

  // resolves one alert of this camera, if it fails the row just stays visible
  async function resolveAlert(alert) {
    try {
      await alertsApi.resolveCamera(alert.id);
      await reload();
    } catch {
      // nothing to do
    }
  }

  if (notFound) {
    return <NotFound entity="Camera" />;
  }

  const hasCoordinates = camera && camera.latitude !== null && camera.latitude !== undefined;

  return (
    <div className="page">
      <Breadcrumbs trail={camera?.breadcrumb?.slice(0, -1)} trailingLabel={camera?.name ?? "..."} />

      <PageHeader
        eyebrow="Camera"
        title={camera?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {camera && (
          <>
            {camera.pending_review && (
              <button className="secondary-button" onClick={approve}>
                Approve
              </button>
            )}
            <button className="secondary-button" onClick={() => editor.openEdit(camera)}>
              Edit Camera
            </button>
          </>
        )}
      </PageHeader>

      {camera && (
        <DetailSummary
          title={camera.name}
          badges={
            <>
              <StatusBadge status={camera.status} />
              {camera.pending_review && <PendingReviewBadge />}
              {!camera.on_mqtt && <NotOnMqttBadge />}
              <RollupIndicator node={rollup.get("camera", camera.id)} showLabel />
            </>
          }
          meta={[
            {
              label: "Device",
              bare: true,
              value: (
                <strong
                  className="breadcrumb-crumb"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/devices/${camera.device}`)}
                >
                  {camera.device_name}
                </strong>
              ),
            },
            { label: "Channel", value: camera.channel },
            { label: "Camera Identifier", value: camera.camera_identifier },
            camera.serial_number && { label: "Serial Number", value: camera.serial_number },
            hasCoordinates && { label: "Coordinates", value: `${camera.latitude}, ${camera.longitude}` },
            { label: "Last Seen", value: formatTimestamp(camera.last_seen) },
            { label: "Active", value: <ActiveBadge active={camera.active} />, bare: true },
          ]}
        />
      )}

      <AlertSections alerts={camera?.alerts} detections={camera?.detections} onResolve={resolveAlert} />
      <LicenseSection license={camera?.license_data} />

      <ResourceModal resource={editor} entity="Camera" fields={FORM_FIELDS} onSubmit={saveEdit} />
    </div>
  );
}

export default CameraDetailPage;
