import { SCOPE } from "../../../utils/scope";

// small table that explains the indicators of the tree
// it always has the same rows and every text fits one line, so the tree below never moves when the scope changes
function IndicatorsTable({ scope }) {
  const activeOnly = scope === SCOPE.ACTIVE;
  const only = activeOnly ? "active " : "";

  const rows = [
    {
      indicator: <span className="tree-status-dot tree-status-critical" />,
      name: "Red",
      meaning: `Offline: an ${only}device or camera in this branch is offline`,
    },
    {
      indicator: <span className="tree-status-dot tree-status-warning" />,
      name: "Amber",
      meaning: `Error: an active error alert on an ${only}device or camera in this branch`,
    },
    {
      indicator: <span className="tree-status-dot tree-status-ok" />,
      name: "Green",
      meaning: "All clear: nothing offline and no error alerts",
    },
    {
      indicator: <span className="tree-indicator tree-detections-badge">3</span>,
      name: "Number",
      meaning: `Recent detections from ${only}cameras in this branch`,
    },
    {
      indicator: <span className="tree-inactive-tag">Inactive</span>,
      name: "",
      meaning: activeOnly
        ? "Switched off: hidden, and it does not change the colours"
        : "Switched off: shown, and it changes the colours",
    },
  ];

  return (
    <table className="tree-key-table">
      <thead>
        <tr>
          <th>Indicator</th>
          <th>Meaning</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name || "inactive"}>
            <td>
              <span className="tree-key-indicator">
                {row.indicator} {row.name}
              </span>
            </td>
            <td>{row.meaning}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default IndicatorsTable;
