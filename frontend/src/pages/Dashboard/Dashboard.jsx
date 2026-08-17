const summaryCards = [
  {
    label: "Dispositivos",
    value: "52",
    description: "Total de dispositivos",
  },
  {
    label: "Online",
    value: "41",
    description: "Dispositivos online",
  },
  {
    label: "Offline",
    value: "3",
    description: "Dispositivos offline",
  },
  {
    label: "Câmaras",
    value: "18",
    description: "Câmaras registadas",
  },
];

const recentAlerts = [
  {
    type: "Offline",
    device: "Edge 01",
    location: "Município de Leiria",
    time: "10:32",
  },
  {
    type: "Health",
    device: "Edge 04",
    location: "Lisboa",
    time: "10:18",
  },
  {
    type: "Camera",
    device: "Camera 03",
    location: "Leiria",
    time: "09:51",
  },
];

const installationStatus = [
  {
    name: "Município de Leiria",
    status: "ONLINE",
    cameras: 8,
  },
  {
    name: "Lisboa",
    status: "ONLINE",
    cameras: 5,
  },
  {
    name: "Porto",
    status: "OFFLINE",
    cameras: 3,
  },
];

function StatusDot({ status }) {
  return (
    <span
      className={`status-dot status-dot-${status.toLowerCase()}`}
    />
  );
}

function Dashboard() {
  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Monitoring</p>
          <h1>Dashboard</h1>
        </div>

        <button className="primary-button">
          Refresh
        </button>
      </header>

      <section className="summary-grid">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span className="summary-card-label">
              {card.label}
            </span>

            <strong className="summary-card-value">
              {card.value}
            </strong>

            <span className="summary-card-description">
              {card.description}
            </span>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel">
          <div className="panel-header">
            <div>
              <p className="panel-eyebrow">Monitoring</p>
              <h2>Recent Alerts</h2>
            </div>

            <button className="text-button">
              See All
            </button>
          </div>

          <div className="alert-list">
            {recentAlerts.map((alert, index) => (
              <div className="alert-row" key={index}>
                <div className="alert-row-main">
                  <StatusDot
                    status={
                      alert.type === "Offline"
                        ? "offline"
                        : "warning"
                    }
                  />

                  <div>
                    <strong>{alert.device}</strong>
                    <span>{alert.location}</span>
                  </div>
                </div>

                <div className="alert-row-meta">
                  <span>{alert.type}</span>
                  <time>{alert.time}</time>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="dashboard-panel">
          <div className="panel-header">
            <div>
              <p className="panel-eyebrow">Locations</p>
              <h2>Locations with problems </h2>
            </div>

            <button className="text-button">
              See All
            </button>
          </div>

          <div className="installation-list">
            {installationStatus.map((installation) => (
              <div
                className="installation-row"
                key={installation.name}
              >
                <div className="installation-name">
                  <StatusDot status={installation.status} />

                  <strong>{installation.name}</strong>
                </div>

                <span>
                  {installation.cameras} Cameras
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}

export default Dashboard;