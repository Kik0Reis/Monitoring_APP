// short names of each alert type, shown in the alert lists
export const ALERT_TYPE_LABELS = {
  DEVICE_OFFLINE: "Offline",
  DEVICE_HEALTH: "Health",
  DEVICE_ERROR: "Error",
  MQTT_ERROR: "MQTT",
  SYSTEM_ERROR: "System",
  CAMERA_ALERT: "Camera",
  CAMERA_ERROR: "Camera Error",
  CAMERA_OFFLINE: "Camera Offline",
};

// returns the short name of an alert type
export function alertTypeLabel(type) {
  return ALERT_TYPE_LABELS[type] ?? type ?? "Alert";
}

// returns the dot colour (critical, warning or info) for an alert severity
export function severityTone(severity) {
  const value = String(severity ?? "WARNING").toUpperCase();

  if (value === "CRITICAL") return "critical";
  if (value === "WARNING") return "warning";
  return "info";
}
