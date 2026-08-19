import { useEffect, useState } from "react";
import { devicesApi, locationsApi } from "../../services/api";
import CrudModal from "../../components/crud/CrudModal";
import "./devices.css";

const PAGE_SIZE = 5;

function Devices() {
  const [devices, setDevices] = useState([]);
  const [locations, setLocations] = useState([]);

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selectedDevice, setSelectedDevice] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    location_id: "",
    mqtt_identifier: "",
    serial_number: "",
    active: true,
  });

  const [saving, setSaving] = useState(false);

  async function loadDevices() {
    try {
      setLoading(true);
      setError("");

      const data = await devicesApi.list(
        `?search=${encodeURIComponent(search)}`
      );

      setDevices(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadLocations() {
    try {
      const data = await locationsApi.list();

      setLocations(data.results ?? data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadDevices();
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    loadLocations();
  }, []);

  function handleSearchChange(event) {
    setSearch(event.target.value);
  }

  function openCreateModal() {
    setSelectedDevice(null);

    setFormData({
      name: "",
      location_id: "",
      mqtt_identifier: "",
      serial_number: "",
      active: true,
    });

    setModalMode("create");
  }

  function openViewModal(device) {
    setSelectedDevice(device);
    setModalMode("view");
  }

  function openEditModal(device) {
    setSelectedDevice(device);

    setFormData({
      name: device.name,
      location_id: device.location?.id ?? "",
      mqtt_identifier: device.mqtt_identifier,
      serial_number: device.serial_number,
      active: device.active,
    });

    setModalMode("edit");
  }

  function closeModal() {
    setModalMode(null);
    setSelectedDevice(null);
  }

  function handleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit() {
    setSaving(true);
    setError("");

    try {
      const payload = {
        name: formData.name,
        location_id: Number(formData.location_id),
        mqtt_identifier: formData.mqtt_identifier,
        serial_number: formData.serial_number,
        active: formData.active,
      };

      if (modalMode === "create") {
        await devicesApi.create(payload);
      }

      if (modalMode === "edit") {
        await devicesApi.update(
          selectedDevice.id,
          payload
        );
      }

      closeModal();
      await loadDevices();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(device) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${device.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await devicesApi.delete(device.id);

      setDevices((previous) =>
        previous.filter(
          (item) => item.id !== device.id
        )
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="devices">

      <header className="page-header">
        <div>
          <p className="page-eyebrow">Management</p>
          <h1>Devices</h1>
        </div>

        <button
          className="primary-button"
          onClick={openCreateModal}
        >
          + Add Device
        </button>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search device..."
          value={search}
          onChange={handleSearchChange}
        />
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="table-card">
        <table className="devices-table">

          <thead>
            <tr>
              <th>Name</th>
              <th>Location</th>
              <th>MQTT Identifier</th>
              <th>Serial Number</th>
              <th>Status</th>
              <th className="actions-col">
                Actions
              </th>
            </tr>
          </thead>

          <tbody>

            {loading ? (
              <tr>
                <td
                  colSpan={6}
                  className="empty-row"
                >
                  Loading devices...
                </td>
              </tr>
            ) : devices.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="empty-row"
                >
                  No devices found.
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr
                  key={device.id}
                  onDoubleClick={() =>
                    openViewModal(device)
                  }
                >

                  <td>
                    <span className="device-name">
                      {device.name}
                    </span>
                  </td>

                  <td>
                    {device.location?.name ?? "—"}
                  </td>

                  <td>
                    {device.mqtt_identifier}
                  </td>

                  <td>
                    {device.serial_number}
                  </td>

                  <td>
                    <span
                      className={`device-status device-status-${device.status?.toLowerCase()}`}
                    >
                      <span className="status-dot" />
                      {device.status}
                    </span>
                  </td>

                  <td className="actions-col">

                    <button
                      className="icon-button"
                      aria-label={`View ${device.name}`}
                      onClick={() =>
                        openViewModal(device)
                      }
                    >
                      👁
                    </button>

                    <button
                      className="icon-button"
                      aria-label={`Edit ${device.name}`}
                      onClick={() =>
                        openEditModal(device)
                      }
                    >
                      ✎
                    </button>

                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${device.name}`}
                      onClick={() =>
                        handleDelete(device)
                      }
                    >
                      🗑
                    </button>

                  </td>

                </tr>
              ))
            )}

          </tbody>

        </table>
      </div>

      {modalMode && (
        <CrudModal
          mode={modalMode}
          title={
            modalMode === "create"
              ? "Add Device"
              : modalMode === "edit"
              ? "Edit Device"
              : selectedDevice?.name
          }
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={
            modalMode === "create"
              ? "Create Device"
              : "Save Changes"
          }
          loading={saving}
        >

          {modalMode === "view" ? (
            <div className="device-details">

              <div className="detail-field">
                <span>Name</span>
                <strong>
                  {selectedDevice?.name}
                </strong>
              </div>

              <div className="detail-field">
                <span>Location</span>
                <strong>
                  {selectedDevice?.location?.name ?? "—"}
                </strong>
              </div>

              <div className="detail-field">
                <span>MQTT Identifier</span>
                <strong>
                  {selectedDevice?.mqtt_identifier}
                </strong>
              </div>

              <div className="detail-field">
                <span>Serial Number</span>
                <strong>
                  {selectedDevice?.serial_number}
                </strong>
              </div>

              <div className="detail-field">
                <span>Device Type</span>
                <strong>
                  {selectedDevice?.device_type}
                </strong>
              </div>

              <div className="detail-field">
                <span>Status</span>
                <strong>
                  {selectedDevice?.status}
                </strong>
              </div>

              <div className="detail-field">
                <span>Last Seen</span>
                <strong>
                  {selectedDevice?.last_seen ?? "Never"}
                </strong>
              </div>

              <div className="detail-field">
                <span>Active</span>
                <strong>
                  {selectedDevice?.active
                    ? "Yes"
                    : "No"}
                </strong>
              </div>

            </div>
          ) : (
            <div className="crud-form">

              <label>
                Name

                <input
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="Device name"
                />
              </label>

              <label>
                Location

                <select
                  name="location_id"
                  value={formData.location_id}
                  onChange={handleFormChange}
                >
                  <option value="">
                    Select location
                  </option>

                  {locations.map((location) => (
                    <option
                      key={location.id}
                      value={location.id}
                    >
                      {location.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                MQTT Identifier

                <input
                  name="mqtt_identifier"
                  value={formData.mqtt_identifier}
                  onChange={handleFormChange}
                  placeholder="edge-01"
                />
              </label>

              <label>
                Serial Number

                <input
                  name="serial_number"
                  value={formData.serial_number}
                  onChange={handleFormChange}
                  placeholder="EDGE-001"
                />
              </label>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  name="active"
                  checked={formData.active}
                  onChange={handleFormChange}
                />

                Active
              </label>

            </div>
          )}

        </CrudModal>
      )}

    </div>
  );
}

export default Devices;