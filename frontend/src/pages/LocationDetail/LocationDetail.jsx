import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, Pencil, Trash2 } from "lucide-react";

import { locationsApi, devicesApi } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import Breadcrumbs from "../../components/common/Breadcrumbs";
import DataTable from "../../components/common/DataTable";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import ActiveBadge from "../../components/common/ActiveBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import CrudModal from "../../components/crud/CrudModal";
import RollupIndicator from "../../components/common/RollupIndicator";
import { useMonitorRollup } from "../../hooks/useMonitorRollup";
import { formatTimestamp } from "../../utils/formatTimestamp";

const EMPTY_FORM = {
  name: "",
  mqtt_identifier: "",
  serial_number: "",
  active: true,
};

function LocationDetail() {
  const { locationId } = useParams();
  const navigate = useNavigate();

  const [location, setLocation] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const loadLocation = useCallback(async () => {
    try {
      const data = await locationsApi.get(locationId);
      setLocation(data);
    } catch {
      setNotFound(true);
    }
  }, [locationId]);

  const { lastUpdated, refreshing, refresh } = useAutoRefresh(loadLocation);
  const rollup = useMonitorRollup();

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
    return (
      <div className="page">
        <p className="dashboard-error">Location not found.</p>
      </div>
    );
  }

  const formFields = [
    { name: "name", label: "Name", type: "text", placeholder: "Edge 01" },
    { name: "mqtt_identifier", label: "MQTT Identifier", type: "text", placeholder: "edge-01" },
    { name: "serial_number", label: "Serial Number", type: "text", placeholder: "EDGE-01" },
    { name: "active", label: "Active", type: "checkbox" },
  ];

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
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "active",
      header: "Active",
      render: (row) => <ActiveBadge active={row.active} />,
    },
    {
      key: "health",
      header: "Health",
      render: (row) => <RollupIndicator node={rollup.get("device", row.id)} />,
    },
    {
      key: "cameras_count",
      header: "Cameras",
      render: (row) => row.cameras_count ?? 0,
    },
    {
      key: "last_seen",
      header: "Last Seen",
      render: (row) => formatTimestamp(row.last_seen),
    },
  ];

  async function handleApproveLocation() {
    try {
      await locationsApi.approve(location.id);
      await loadLocation();
    } catch {
      // Best-effort; the badge just stays visible if this fails.
    }
  }

  async function handleApproveDevice(item) {
    await devicesApi.approve(item.id);
    await devices.reload();
  }

  return (
    <div className="page">
      <Breadcrumbs
        trail={location?.breadcrumb?.slice(0, -1)}
        trailingLabel={location?.name ?? "..."}
      />

      <PageHeader
        eyebrow="Location"
        title={location?.name ?? "Loading..."}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      >
        {location?.pending_review && (
          <button className="secondary-button" onClick={handleApproveLocation}>
            Approve
          </button>
        )}
      </PageHeader>

      {location && (
        <div className="detail-summary">
          <div className="detail-summary-main">
            <div>
              <div className="detail-summary-title">
                <h2>{location.name}</h2>
                <StatusBadge status={location.active ? "active" : "inactive"} />
                {location.pending_review && <PendingReviewBadge />}
                <RollupIndicator node={rollup.get("location", location.id)} showLabel />
              </div>

              <div className="detail-summary-meta">
                <div className="detail-meta-item">
                  <span>Client</span>
                  <strong>{location.customer?.name}</strong>
                </div>
                <div className="detail-meta-item">
                  <span>Devices</span>
                  <strong>{location.devices_count ?? 0}</strong>
                </div>
                {location.description && (
                  <div className="detail-meta-item">
                    <span>Description</span>
                    <strong>{location.description}</strong>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="detail-section">
        <div className="detail-section-header">
          <h3>Devices at {location?.name}</h3>
          <button className="primary-button" onClick={() => devices.openCreate()}>
            + Add Device
          </button>
        </div>

        {devices.error && <div className="error-message">{devices.error}</div>}

        <DataTable
          columns={columns}
          rows={devices.items}
          loading={devices.loading}
          loadingMessage="Loading devices..."
          emptyMessage="No devices at this location yet."
          onRowClick={(device) => navigate(`/devices/${device.id}`)}
          actions={(device) => (
            <>
              {device.pending_review && (
                <button
                  className="icon-button"
                  title="Approve"
                  onClick={() => handleApproveDevice(device)}
                >
                  <Check size={16} />
                </button>
              )}
              <button className="icon-button" onClick={() => devices.openEdit(device)}>
                <Pencil size={16} />
              </button>
              <button
                className="icon-button danger"
                onClick={() => devices.handleDelete(device)}
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        />
      </section>

      {devices.modalMode && (
        <CrudModal
          mode={devices.modalMode}
          title={devices.modalMode === "create" ? "Add Device" : "Edit Device"}
          onClose={devices.closeModal}
          onSubmit={devices.handleSubmit}
          loading={devices.saving}
        >
          <div className="crud-form">
            {formFields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={devices.formData[field.name]}
                onChange={devices.handleFormChange}
                disabled={devices.saving}
              />
            ))}
          </div>
        </CrudModal>
      )}
    </div>
  );
}

export default LocationDetail;
