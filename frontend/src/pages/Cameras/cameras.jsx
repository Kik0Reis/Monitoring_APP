import { useEffect, useState } from "react";
import { camerasApi, devicesApi } from "../../services/api";
import CrudModal from "../../components/crud/CrudModal";
import "./cameras.css";

function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [devices, setDevices] = useState([]);

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalMode, setModalMode] = useState(null);
  const [selectedCamera, setSelectedCamera] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    device_id: "",
    camera_identifier: "",
    channel: 1,
    active: true,
  });

  const [saving, setSaving] = useState(false);

  async function loadCameras() {
    try {
      setLoading(true);
      setError("");

      const data = await camerasApi.list(
        `?search=${encodeURIComponent(search)}`
      );

      setCameras(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDevices() {
    try {
      const data = await devicesApi.list();

      setDevices(data.results ?? data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCameras();
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    loadDevices();
  }, []);

  function handleSearchChange(event) {
    setSearch(event.target.value);
  }

  function openCreateModal() {
    setSelectedCamera(null);

    setFormData({
      name: "",
      device_id: "",
      camera_identifier: "",
      channel: 1,
      active: true,
    });

    setModalMode("create");
  }

  function openViewModal(camera) {
    setSelectedCamera(camera);
    setModalMode("view");
  }

  function openEditModal(camera) {
    setSelectedCamera(camera);

    setFormData({
      name: camera.name,
      device_id: camera.device?.id ?? camera.device_id ?? "",
      camera_identifier: camera.camera_identifier,
      channel: camera.channel,
      active: camera.active,
    });

    setModalMode("edit");
  }

  function closeModal() {
    setModalMode(null);
    setSelectedCamera(null);
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
        device_id: Number(formData.device_id),
        camera_identifier: formData.camera_identifier,
        channel: Number(formData.channel),
        active: formData.active,
      };

      if (modalMode === "create") {
        await camerasApi.create(payload);
      }

      if (modalMode === "edit") {
        await camerasApi.update(
          selectedCamera.id,
          payload
        );
      }

      closeModal();
      await loadCameras();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(camera) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${camera.name}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await camerasApi.delete(camera.id);

      setCameras((previous) =>
        previous.filter(
          (item) => item.id !== camera.id
        )
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="cameras">

      <header className="page-header">
        <div>
          <p className="page-eyebrow">Management</p>
          <h1>Cameras</h1>
        </div>

        <button
          className="primary-button"
          onClick={openCreateModal}
        >
          + Add Camera
        </button>
      </header>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search camera..."
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
        <table className="cameras-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Device</th>
              <th>Identifier</th>
              <th>Channel</th>
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
                  Loading cameras...
                </td>
              </tr>
            ) : cameras.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="empty-row"
                >
                  No cameras found.
                </td>
              </tr>
            ) : (
              cameras.map((camera) => (
                <tr
                  key={camera.id}
                  onDoubleClick={() =>
                    openViewModal(camera)
                  }
                >
                  <td>
                    <span className="camera-name">
                      {camera.name}
                    </span>
                  </td>

                  <td>
                    {camera.device_name ??
                      camera.device?.name ??
                      "—"}
                  </td>

                  <td>
                    {camera.camera_identifier}
                  </td>

                  <td>
                    {camera.channel}
                  </td>

                  <td>
                    <span
                      className={`camera-status camera-status-${camera.status?.toLowerCase()}`}
                    >
                      <span className="status-dot" />
                      {camera.status}
                    </span>
                  </td>

                  <td className="actions-col">
                    <button
                      className="icon-button"
                      aria-label={`View ${camera.name}`}
                      onClick={() =>
                        openViewModal(camera)
                      }
                    >
                      👁
                    </button>

                    <button
                      className="icon-button"
                      aria-label={`Edit ${camera.name}`}
                      onClick={() =>
                        openEditModal(camera)
                      }
                    >
                      ✎
                    </button>

                    <button
                      className="icon-button danger"
                      aria-label={`Delete ${camera.name}`}
                      onClick={() =>
                        handleDelete(camera)
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
              ? "Add Camera"
              : modalMode === "edit"
              ? "Edit Camera"
              : selectedCamera?.name
          }
          onClose={closeModal}
          onSubmit={handleSubmit}
          submitLabel={
            modalMode === "create"
              ? "Create Camera"
              : "Save Changes"
          }
          loading={saving}
        >
          {modalMode === "view" ? (
            <div className="camera-details">

              <div className="detail-field">
                <span>Name</span>
                <strong>
                  {selectedCamera?.name}
                </strong>
              </div>

              <div className="detail-field">
                <span>Device</span>
                <strong>
                  {selectedCamera?.device_name ??
                    selectedCamera?.device?.name ??
                    "—"}
                </strong>
              </div>

              <div className="detail-field">
                <span>Camera Identifier</span>
                <strong>
                  {selectedCamera?.camera_identifier}
                </strong>
              </div>

              <div className="detail-field">
                <span>Channel</span>
                <strong>
                  {selectedCamera?.channel}
                </strong>
              </div>

              <div className="detail-field">
                <span>Status</span>
                <strong>
                  {selectedCamera?.status}
                </strong>
              </div>

              <div className="detail-field">
                <span>Last Seen</span>
                <strong>
                  {selectedCamera?.last_seen ?? "Never"}
                </strong>
              </div>

              <div className="detail-field">
                <span>Active</span>
                <strong>
                  {selectedCamera?.active
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
                  placeholder="Camera name"
                />
              </label>

              <label>
                Device

                <select
                  name="device_id"
                  value={formData.device_id}
                  onChange={handleFormChange}
                >
                  <option value="">
                    Select device
                  </option>

                  {devices
                    .filter(
                      (device) =>
                        device.active &&
                        device.device_type === "EDGE"
                    )
                    .map((device) => (
                      <option
                        key={device.id}
                        value={device.id}
                      >
                        {device.name}
                      </option>
                    ))}
                </select>
              </label>

              <label>
                Camera Identifier

                <input
                  name="camera_identifier"
                  value={formData.camera_identifier}
                  onChange={handleFormChange}
                  placeholder="camera-01"
                />
              </label>

              <label>
                Channel

                <input
                  type="number"
                  name="channel"
                  min="1"
                  value={formData.channel}
                  onChange={handleFormChange}
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

export default Cameras;