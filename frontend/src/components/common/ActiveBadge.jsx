import StatusBadge from "./StatusBadge";

// shows whether a record is switched on (its active flag), this is not the same as online or offline
// inactive is grey and not red on purpose, it is a deliberate off and red is for things that are wrong
function ActiveBadge({ active }) {
  return active ? (
    <StatusBadge status="active" label="Active" />
  ) : (
    <StatusBadge status="unknown" label="Inactive" />
  );
}

export default ActiveBadge;
