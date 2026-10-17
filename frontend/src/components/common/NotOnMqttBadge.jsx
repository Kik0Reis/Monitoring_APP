// shown on a device or camera that the last mqtt reconciliation did not find on the broker
// unlike online and offline this is never based on time, so it is safe to delete the record when it shows
function NotOnMqttBadge() {
  return <span className="not-on-mqtt-badge">Not on MQTT</span>;
}

export default NotOnMqttBadge;
