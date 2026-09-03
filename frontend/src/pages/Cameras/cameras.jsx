import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Eye, Pencil, Trash2 } from "lucide-react";

import { camerasApi, devicesApi, fetchAll } from "../../services/api";
import { useCrudResource } from "../../hooks/useCrudResource";
import { useAutoRefresh } from "../../hooks/useAutoRefresh";

import PageHeader from "../../components/common/PageHeader";
import SearchBar from "../../components/common/SearchBar";
import DataTable from "../../components/common/DataTable";
import Pagination from "../../components/common/Pagination";
import FormField from "../../components/common/FormField";
import StatusBadge from "../../components/common/StatusBadge";
import PendingReviewBadge from "../../components/common/PendingReviewBadge";
import CrudModal from "../../components/crud/CrudModal";

import "./Cameras.css";

const EMPTY_FORM = {
  name: "",
  device_id: "",
  camera_identifier: "",
  channel: 1,
  active: true,
};

function Cameras() {
  const navigate = useNavigate();
  const [devices, setDevices] = useState([]);
  const [deviceFilter, setDeviceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    fetchAll(devicesApi.list).then(setDevices).catch(() => {});
  }, []);

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

  async function handleApprove(camera) {
    try {
      await camerasApi.approve(camera.id);
      await resource.reload();
    } catch (err) {
      resource.setError(err.message);
    }
  }

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Office Camera 1" },
      {
        name: "device_id",
        label: "Device",
        type: "select",
        options: devices.map((d) => ({ value: d.id, label: d.name })),
      },
      { name: "camera_identifier", label: "Camera Identifier", type: "text" },
      { name: "channel", label: "Channel", type: "text", placeholder: "1" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [devices]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          <span className="entity-subtext">{row.device_name}</span>
        </span>
      ),
    },
    { key: "channel", header: "Ch." },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "last_seen",
      header: "Last Seen",
      render: (row) =>
        row.last_seen ? new Date(row.last_seen).toLocaleString() : "—",
    },
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
        <SearchBar
          value={resource.search}
          onChange={resource.setSearch}
          placeholder="Search cameras..."
        />

        <select
          className="filter-select"
          value={deviceFilter}
          onChange={(event) => setDeviceFilter(event.target.value)}
        >
          <option value="">All devices</option>
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.name}
            </option>
          ))}
        </select>

        <select
          className="filter-select"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">All statuses</option>
          <option value="ONLINE">Online</option>
          <option value="OFFLINE">Offline</option>
          <option value="UNKNOWN">Unknown</option>
        </select>
      </div>

      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage="Loading cameras..."
        emptyMessage="No cameras found."
        onRowClick={(camera) => navigate(`/cameras/${camera.id}`)}
        actions={(camera) => (
          <>
            {camera.pending_review && (
              <button
                className="icon-button"
                aria-label={`Approve ${camera.name}`}
                title="Approve"
                onClick={() => handleApprove(camera)}
              >
                <Check size={16} />
              </button>
            )}
            <button
              className="icon-button"
              aria-label={`View ${camera.name}`}
              onClick={() => resource.openView(camera)}
            >
              <Eye size={16} />
            </button>
            <button
              className="icon-button"
              aria-label={`Edit ${camera.name}`}
              onClick={() => resource.openEdit(camera)}
            >
              <Pencil size={16} />
            </button>
            <button
              className="icon-button danger"
              aria-label={`Delete ${camera.name}`}
              onClick={() => resource.handleDelete(camera)}
            >
              <Trash2 size={16} />
            </button>
          </>
        )}
      />

      <Pagination
        page={resource.page}
        setPage={resource.setPage}
        count={resource.count}
        hasNext={resource.hasNext}
        hasPrevious={resource.hasPrevious}
      />

      {resource.modalMode && (
        <CrudModal
          mode={resource.modalMode}
          title={
            resource.modalMode === "create"
              ? "Add Camera"
              : resource.modalMode === "edit"
              ? "Edit Camera"
              : "Camera Details"
          }
          onClose={resource.closeModal}
          onSubmit={resource.handleSubmit}
          loading={resource.saving}
        >
          {resource.modalMode === "view" ? (
            <div className="crud-details">
              <div className="crud-detail">
                <span>Name</span>
                <strong>{resource.selected?.name}</strong>
              </div>
              <div className="crud-detail">
                <span>Device</span>
                <strong>{resource.selected?.device_name}</strong>
              </div>
              <div className="crud-detail">
                <span>Channel</span>
                <strong>{resource.selected?.channel}</strong>
              </div>
              <div className="crud-detail">
                <span>Status</span>
                <strong>{resource.selected?.status}</strong>
              </div>
            </div>
          ) : (
            <div className="crud-form">
              {formFields.map((field) => (
                <FormField
                  key={field.name}
                  field={field}
                  value={resource.formData[field.name]}
                  onChange={resource.handleFormChange}
                  disabled={resource.saving}
                />
              ))}
            </div>
          )}
        </CrudModal>
      )}
    </div>
  );
}

export default Cameras;
