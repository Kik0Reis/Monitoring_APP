/**
 * Shown on a Device/Camera when the last MQTT reconciliation cycle
 * didn't see it on the broker at all (Device.on_mqtt / Camera.on_mqtt
 * === false). Unlike the ONLINE/OFFLINE status badge, this is never
 * time-based -- it only appears once a full reconcile cycle genuinely
 * couldn't find it, which is what makes it safe to delete with
 * confidence.
 */
function NotOnMqttBadge() {
  return <span className="not-on-mqtt-badge">Not on MQTT</span>;
}

export default NotOnMqttBadge;
