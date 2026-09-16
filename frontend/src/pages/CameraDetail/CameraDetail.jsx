import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { camerasApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import NotOnMqttBadge from "../../components/common/NotOnMqttBadge";
import { formatTimestamp } from "../../utils/formatTimestamp";

import CrudModal from "../../components/crud/CrudModal";

const FORM_FIELDS = [
  { name: "name", label: "Name", type: "text" },
  { name: "camera_identifier", label: "Camera Identifier", type: "text" },
  { name: "channel", label: "Channel", type: "text" },
  { name: "active", label: "Active", type: "checkbox" },
];

function CameraDetail() {
  const { cameraId } = useParams();
  const navigate = useNavigate();

  const [camera, setCamera] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const loadCamera = useCallback(async () => {
    try {
      const data = await camerasApi.get(cameraId);
      setCamera(data);
    } catch {
      setNotFound(true);
    }
  }, [cameraId]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadCamera);

  const resource = useCrudResource({
    api: camerasApi,
    emptyFormData: {
      name: "",
      camera_identifier: "",
      channel: 1,
      active: true,
    },
    filters: { device: camera?.device },
    mapFormToPayload: (formData) => ({
      name: formData.name.trim(),
      camera_identifier: formData.camera_identifier.trim(),
      channel: Number(formData.channel) || 1,
      active: Boolean(formData.active),
      device_id: camera?.device,
    }),
  });

  function openEdit() {
    resource.openEdit({
      id: camera.id,
      name: camera.name,
      camera_identifier: camera.camera_identifier,
      channel: camera.channel,
      active: camera.active,
    });
  }

  async function handleSubmit() {
    await resource.handleSubmit();
    await loadCamera();
  }

  if (notFound) {
    return (
      <div className="page">
        <p className="dashboard-error">Camera not found.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Breadcrumbs
        trail={camera?.breadcrumb?.slice(0, -1)}
        trailingLabel={camera?.name ?? "..."}
      />

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
              <button
                className="secondary-button"
                onClick={async () => {
                  try {
                    await camerasApi.approve(camera.id);
                    await loadCamera();
                  } catch {
                    // Best-effort; the badge just stays visible if this fails.
                  }
                }}
              >
                Approve
              </button>
            )}
            <button className="secondary-button" onClick={openEdit}>
              Edit Camera
            </button>
          </>
        )}
      </PageHeader>

      {camera && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{camera.name}</h2>
                <StatusBadge status={camera.status} />
                {camera.pending_review && <PendingReviewBadge />}
                {!camera.on_mqtt && <NotOnMqttBadge />}
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Device</span>
                  <strong
                    className="breadcrumb-crumb"
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate(`/devices/${camera.device}`)}
                  >
                    {camera.device_name}
                  </strong>
                </div>
                <div className="detail-meta-item">
                  <span>Channel</span>
                  <strong>{camera.channel}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Camera Identifier</span>
                  <strong>{camera.camera_identifier}</strong>
                </div>
                {camera.serial_number && (
                  <div className="detail-meta-item">
                    <span>Serial Number</span>
                    <strong>{camera.serial_number}</strong>
                  </div>
                )}
                {(camera.latitude !== null && camera.latitude !== undefined) && (
                  <div className="detail-meta-item">
                    <span>Coordinates</span>
                    <strong>
                      {camera.latitude}, {camera.longitude}
                    </strong>
                  </div>
                )}
                <div className="detail-meta-item">
                  <span>Last Seen</span>
                  <strong>{formatTimestamp(camera.last_seen)}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Status</span>
                  <strong>{camera.active ? "Active" : "Inactive"}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {camera && camera.license_data && Object.keys(camera.license_data).length > 0 && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>License</h3>
          </div>

          <div className="component-detail-list">
            <div className="component-detail-row">
              <span>Licensed</span>
              <StatusBadge
                status={camera.license_data.licensed ? "online" : "critical"}
                label={camera.license_data.licensed ? "Licensed" : "Not Licensed"}
              />
            </div>

            {camera.license_data.begin_date && (
              <div className="component-detail-row">
                <span>Begin Date</span>
                <strong>{camera.license_data.begin_date}</strong>
              </div>
            )}

            {camera.license_data.end_date && (
              <div className="component-detail-row">
                <span>End Date</span>
                <strong>{camera.license_data.end_date}</strong>
              </div>
            )}

            {camera.license_data.days_left !== null &&
              camera.license_data.days_left !== undefined && (
                <div className="component-detail-row">
                  <span>Days Left</span>
                  <strong>{camera.license_data.days_left}</strong>
                </div>
              )}

            {camera.license_data.last_validation_ok !== null &&
              camera.license_data.last_validation_ok !== undefined && (
                <div className="component-detail-row">
                  <span>Last Validation</span>
                  <StatusBadge
                    status={camera.license_data.last_validation_ok ? "online" : "warning"}
                    label={camera.license_data.last_validation_ok ? "Validated" : "Failed"}
                  />
                </div>
              )}

            {camera.license_data.last_validation_error && (
              <div className="component-detail-row">
                <span>Validation Error</span>
                <strong>{camera.license_data.last_validation_error}</strong>
              </div>
            )}

            {camera.license_data.last_validation_at && (
              <div className="component-detail-row">
                <span>Last Validated At</span>
                <strong>{formatTimestamp(camera.license_data.last_validation_at)}</strong>
              </div>
            )}
          </div>
        </section>
      )}

      {camera && camera.alerts && camera.alerts.some((alert) => alert.active) && (
        <section className="detail-section">
          <div className="detail-section-header">
            <h3>Alerts</h3>
          </div>

          <div className="entity-alerts-list">
            {camera.alerts
              .filter((alert) => alert.active)
              .map((alert) => (
                <div className="entity-alert-row active" key={alert.id}>
                  <div className="entity-alert-main">
                    <StatusBadge status="warning" label="Active" />
                    <span>{alert.message}</span>
                  </div>
                  <time>{formatTimestamp(alert.created_at)}</time>
                </div>
              ))}
          </div>
        </section>
      )}

      {resource.modalMode && (
        <CrudModal
          mode={resource.modalMode}
          title="Edit Camera"
          onClose={resource.closeModal}
          onSubmit={handleSubmit}
          loading={resource.saving}
        >
          <div className="crud-form">
            {FORM_FIELDS.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={resource.formData[field.name]}
                onChange={resource.handleFormChange}
                disabled={resource.saving}
              />
            ))}
          </div>
        </CrudModal>
      )}
    </div>
  );
}

export default CameraDetail;
