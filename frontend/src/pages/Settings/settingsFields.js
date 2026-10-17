const RESTART_MQTT = "Restart app-mqtt to apply.";
const RESTART_HEARTBEAT = "Restart heartbeat to apply.";

// the sections of the settings page and the fields of each one, to add a setting put a field here
// the field names are the ones the backend accepts (see core/serializers.py)
// placeholder can be a function of the form, the password uses it to say whether one is set
export const SECTIONS = [
  {
    title: "MQTT Connection",
    hint: RESTART_MQTT,
    fields: [
      { name: "mqtt_host", label: "Host", type: "text" },
      { name: "mqtt_port", label: "Port", type: "number", min: 1, max: 65535 },
      { name: "mqtt_username", label: "Username", type: "text" },
      {
        name: "mqtt_password",
        label: "Password",
        type: "password",
        placeholder: (form) => (form.mqtt_password_set ? "Set (leave blank to keep)" : "Not set"),
      },
      { name: "mqtt_keepalive", label: "Keepalive (s)", type: "number", min: 5, max: 3600 },
      { name: "mqtt_tls", label: "TLS", type: "checkbox" },
    ],
  },
  {
    title: "MQTT Reconciliation",
    hint: RESTART_MQTT,
    fields: [
      { name: "mqtt_reconcile_interval_minutes", label: "Interval (min)", type: "number", min: 1, max: 1440 },
      { name: "mqtt_reconcile_window_seconds", label: "Window (s)", type: "number", min: 1, max: 600 },
    ],
  },
  {
    title: "Heartbeat Retention",
    hint: RESTART_HEARTBEAT,
    fields: [
      { name: "heartbeat_retention_days", label: "Keep heartbeats (days)", type: "number", min: 1, max: 3650 },
      { name: "heartbeat_cleanup_interval_hours", label: "Cleanup every (hours)", type: "number", min: 1, max: 720 },
    ],
  },
  {
    title: "Alert Retention",
    hint: RESTART_HEARTBEAT,
    fields: [
      { name: "alert_retention_days", label: "Keep resolved alerts (days)", type: "number", min: 1, max: 3650 },
      {
        name: "alert_stale_hours",
        label: "Auto-resolve error alerts after (hours)",
        type: "number",
        min: 1,
        max: 720,
      },
      {
        name: "alert_visible_hours",
        label: "Hide error alerts from view after (hours)",
        type: "number",
        min: 1,
        max: 720,
      },
    ],
  },
  {
    title: "Detection Retention",
    hint: RESTART_HEARTBEAT,
    fields: [
      { name: "detection_retention_days", label: "Keep detections (days)", type: "number", min: 1, max: 3650 },
      {
        name: "detection_visible_hours",
        label: "Hide detections from view after (hours)",
        type: "number",
        min: 1,
        max: 720,
      },
    ],
  },
];

const ALL_FIELDS = SECTIONS.flatMap((section) => section.fields);

// the form with every field empty (checkboxes off)
export const EMPTY_FORM = {
  mqtt_password_set: false,
  ...Object.fromEntries(ALL_FIELDS.map((field) => [field.name, field.type === "checkbox" ? false : ""])),
};

// builds the object sent to the backend: number fields as numbers, and no password when it was left blank
export function buildPayload(form) {
  const payload = { ...form };

  for (const field of ALL_FIELDS) {
    if (field.type === "number") {
      payload[field.name] = Number(form[field.name]);
    }
  }

  if (!payload.mqtt_password) {
    delete payload.mqtt_password;
  }

  return payload;
}
