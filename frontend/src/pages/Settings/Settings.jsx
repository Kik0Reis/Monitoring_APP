import { useEffect, useState } from "react";

import PageHeader from "../../components/common/PageHeader";
import FormField from "../../components/common/FormField";
import { settingsApi } from "../../services/api";

import "./Settings.css";

const RESTART_MQTT = "Restart app-mqtt to apply.";
const RESTART_HEARTBEAT = "Restart heartbeat to apply.";

const EMPTY_FORM = {
  mqtt_host: "",
  mqtt_port: "",
  mqtt_username: "",
  mqtt_password: "",
  mqtt_password_set: false,
  mqtt_keepalive: "",
  mqtt_tls: false,
  mqtt_reconcile_interval_minutes: "",
  mqtt_reconcile_window_seconds: "",
  heartbeat_retention_days: "",
  heartbeat_cleanup_interval_hours: "",
  alert_retention_days: "",
};

function Settings() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const data = await settingsApi.get();
        if (!ignore) {
          setForm({ ...EMPTY_FORM, ...data, mqtt_password: "" });
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load settings.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, []);

  const handleChange = (event) => {
    const { name, type, value, checked } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    setSaved(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);

    const payload = {
      ...form,
      mqtt_port: Number(form.mqtt_port),
      mqtt_keepalive: Number(form.mqtt_keepalive),
      mqtt_reconcile_interval_minutes: Number(form.mqtt_reconcile_interval_minutes),
      mqtt_reconcile_window_seconds: Number(form.mqtt_reconcile_window_seconds),
      heartbeat_retention_days: Number(form.heartbeat_retention_days),
      heartbeat_cleanup_interval_hours: Number(form.heartbeat_cleanup_interval_hours),
      alert_retention_days: Number(form.alert_retention_days),
    };

    if (!payload.mqtt_password) {
      delete payload.mqtt_password;
    }

    try {
      const data = await settingsApi.update(payload);
      setForm({ ...EMPTY_FORM, ...data, mqtt_password: "" });
      setSaved(true);
    } catch (err) {
      setError(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page settings-page">
      <PageHeader eyebrow="Configuration" title="Settings" />

      {error && <p className="error-message">{error}</p>}
      {saved && <p className="settings-saved-message">Saved.</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <section className="detail-section">
            <div className="detail-section-header">
              <h3>MQTT Connection</h3>
            </div>
            <p className="settings-section-hint">{RESTART_MQTT}</p>
            <div className="settings-grid">
              <FormField
                field={{ name: "mqtt_host", label: "Host", type: "text" }}
                value={form.mqtt_host}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{ name: "mqtt_port", label: "Port", type: "number", min: 1, max: 65535 }}
                value={form.mqtt_port}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{ name: "mqtt_username", label: "Username", type: "text" }}
                value={form.mqtt_username}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{
                  name: "mqtt_password",
                  label: "Password",
                  type: "password",
                  placeholder: form.mqtt_password_set ? "Set (leave blank to keep)" : "Not set",
                }}
                value={form.mqtt_password}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{ name: "mqtt_keepalive", label: "Keepalive (s)", type: "number", min: 5, max: 3600 }}
                value={form.mqtt_keepalive}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{ name: "mqtt_tls", label: "TLS", type: "checkbox" }}
                value={form.mqtt_tls}
                onChange={handleChange}
                disabled={saving}
              />
            </div>
          </section>

          <section className="detail-section">
            <div className="detail-section-header">
              <h3>MQTT Reconciliation</h3>
            </div>
            <p className="settings-section-hint">{RESTART_MQTT}</p>
            <div className="settings-grid">
              <FormField
                field={{
                  name: "mqtt_reconcile_interval_minutes",
                  label: "Interval (min)",
                  type: "number",
                  min: 1,
                  max: 1440,
                }}
                value={form.mqtt_reconcile_interval_minutes}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{
                  name: "mqtt_reconcile_window_seconds",
                  label: "Window (s)",
                  type: "number",
                  min: 1,
                  max: 600,
                }}
                value={form.mqtt_reconcile_window_seconds}
                onChange={handleChange}
                disabled={saving}
              />
            </div>
          </section>

          <section className="detail-section">
            <div className="detail-section-header">
              <h3>Heartbeat Retention</h3>
            </div>
            <p className="settings-section-hint">{RESTART_HEARTBEAT}</p>
            <div className="settings-grid">
              <FormField
                field={{
                  name: "heartbeat_retention_days",
                  label: "Keep heartbeats (days)",
                  type: "number",
                  min: 1,
                  max: 3650,
                }}
                value={form.heartbeat_retention_days}
                onChange={handleChange}
                disabled={saving}
              />
              <FormField
                field={{
                  name: "heartbeat_cleanup_interval_hours",
                  label: "Cleanup every (hours)",
                  type: "number",
                  min: 1,
                  max: 720,
                }}
                value={form.heartbeat_cleanup_interval_hours}
                onChange={handleChange}
                disabled={saving}
              />
            </div>
          </section>

          <section className="detail-section">
            <div className="detail-section-header">
              <h3>Alert Retention</h3>
            </div>
            <p className="settings-section-hint">{RESTART_HEARTBEAT}</p>
            <div className="settings-grid">
              <FormField
                field={{
                  name: "alert_retention_days",
                  label: "Keep resolved alerts (days)",
                  type: "number",
                  min: 1,
                  max: 3650,
                }}
                value={form.alert_retention_days}
                onChange={handleChange}
                disabled={saving}
              />
            </div>
          </section>

          <div className="settings-actions">
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default Settings;
