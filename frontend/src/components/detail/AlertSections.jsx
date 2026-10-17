import CollapsibleSection from "../common/CollapsibleSection";
import EntityAlertRow from "./EntityAlertRow";

// the Offline, Errors and (for cameras) Detections sections of a device or camera page
// only active alerts are listed, a section is hidden when it has nothing to show
// health alerts are not listed here because they already set the status badge and the component cards
function AlertSections({ alerts = [], detections, onResolve }) {
  const active = alerts.filter((alert) => alert.active);

  const sections = [
    { title: "Offline", items: active.filter((alert) => alert.category === "offline"), defaultOpen: true },
    { title: "Errors", items: active.filter((alert) => alert.category === "error"), defaultOpen: true },
    {
      title: "Detections",
      items: (detections ?? []).filter((alert) => alert.active),
      defaultOpen: false,
      label: "Detected",
    },
  ];

  return sections
    .filter((section) => section.items.length > 0)
    .map((section) => (
      <CollapsibleSection
        key={section.title}
        title={section.title}
        count={section.items.length}
        defaultOpen={section.defaultOpen}
      >
        <div className="entity-alerts-list">
          {section.items.map((alert) => (
            <EntityAlertRow key={alert.id} alert={alert} label={section.label} onResolve={onResolve} />
          ))}
        </div>
      </CollapsibleSection>
    ));
}

export default AlertSections;
