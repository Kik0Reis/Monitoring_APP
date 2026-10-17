import AlertRow from "./AlertRow";
import ProblemRow from "./ProblemRow";

// draws the rows of a panel, the panel kind decides how each row looks
// handlers: { openAlert, openDevice, openLocation, resolveAlert }
function PanelRows({ panel, items, handlers }) {
  if (panel.kind === "device") {
    return items.map((device) => (
      <ProblemRow
        key={device.id}
        item={device}
        status={device.status}
        title={`${device.name} - ${device.location_name ?? "—"}`}
        onOpen={handlers.openDevice}
      />
    ));
  }

  if (panel.kind === "location") {
    return items.map((location) => (
      <ProblemRow
        key={location.id}
        item={location}
        status={location.status ?? "offline"}
        title={location.name}
        onOpen={handlers.openLocation}
      />
    ));
  }

  return items.map((alert) => (
    <AlertRow
      key={alert.id}
      item={alert}
      showDot={panel.showDot !== false}
      onOpen={handlers.openAlert}
      onResolve={handlers.resolveAlert}
    />
  ));
}

export default PanelRows;
