import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Eye, Pencil, Trash2 } from "lucide-react";

import { devicesApi, locationsApi, fetchAll } from "../../services/api";
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

import "./Devices.css";

const EMPTY_FORM = {
  name: "",
  location_id: "",
  mqtt_identifier: "",
  serial_number: "",
  active: true,
};

function Devices() {
  const navigate = useNavigate();
  const [locations, setLocations] = useState([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    fetchAll(locationsApi.list).then(setLocations).catch(() => {});
  }, []);

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

  async function handleApprove(device) {
    try {
      await devicesApi.approve(device.id);
      await resource.reload();
    } catch (err) {
      resource.setError(err.message);
    }
  }

  const formFields = useMemo(
    () => [
      { name: "name", label: "Name", type: "text", placeholder: "Edge 01" },
      {
        name: "location_id",
        label: "Location",
        type: "select",
        options: locations.map((l) => ({ value: l.id, label: l.name })),
      },
      { name: "mqtt_identifier", label: "MQTT Identifier", type: "text", placeholder: "edge-01" },
      { name: "serial_number", label: "Serial Number", type: "text", placeholder: "EDGE-01" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
    [locations]
  );

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <span className="entity-name">
          {row.name}
          {row.pending_review && <PendingReviewBadge />}
          <span className="entity-subtext">{row.location?.name}</span>
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "cameras_count",
      header: "Cameras",
      render: (row) => row.cameras_count ?? 0,
    },
    {
      key: "last_seen",
      header: "Last Seen",
      render: (row) =>
        row.last_seen ? new Date(row.last_seen).toLocaleString() : "—",
    },
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
        <SearchBar
          value={resource.search}
          onChange={resource.setSearch}
          placeholder="Search devices..."
        />

        <select
          className="filter-select"
          value={locationFilter}
          onChange={(event) => setLocationFilter(event.target.value)}
        >
          <option value="">All locations</option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
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
        loadingMessage="Loading devices..."
        emptyMessage="No devices found."
        onRowClick={(device) => navigate(`/devices/${device.id}`)}
        actions={(device) => (
          <>
            {device.pending_review && (
              <button
                className="icon-button"
                aria-label={`Approve ${device.name}`}
                title="Approve"
                onClick={() => handleApprove(device)}
              >
                <Check size={16} />
              </button>
            )}
            <button
              className="icon-button"
              aria-label={`View ${device.name}`}
              onClick={() => resource.openView(device)}
            >
              <Eye size={16} />
            </button>
            <button
              className="icon-button"
              aria-label={`Edit ${device.name}`}
              onClick={() => resource.openEdit(device)}
            >
              <Pencil size={16} />
            </button>
            <button
              className="icon-button danger"
              aria-label={`Delete ${device.name}`}
              onClick={() => resource.handleDelete(device)}
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
              ? "Add Device"
              : resource.modalMode === "edit"
              ? "Edit Device"
              : "Device Details"
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
                <span>Location</span>
                <strong>{resource.selected?.location?.name}</strong>
              </div>
              <div className="crud-detail">
                <span>Status</span>
                <strong>{resource.selected?.status}</strong>
              </div>
              <div className="crud-detail">
                <span>MQTT Identifier</span>
                <strong>{resource.selected?.mqtt_identifier}</strong>
              </div>
              <div className="crud-detail">
                <span>Serial Number</span>
                <strong>{resource.selected?.serial_number}</strong>
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

export default Devices;
