import StatusBadge from "./StatusBadge";

/**
 * Whether a device/camera/location is switched on (the `active` flag on the
 * record) -- not the same thing as online/offline. Inactive is shown grey
 * rather than red on purpose: it's a deliberate "off", and red is reserved
 * for things that are actually wrong.
 */
function ActiveBadge({ active }) {
  return active ? (
    <StatusBadge status="active" label="Active" />
  ) : (
    <StatusBadge status="unknown" label="Inactive" />
  );
}

export default ActiveBadge;
