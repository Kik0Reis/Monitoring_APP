import { NavLink } from "react-router-dom";

function Sidebar() {
  const navigation = [
    {
      label: "Dashboard",
      path: "/dashboard",
    },
    {
      label: "Countries",
      path: "/countries",
    },
    {
      label: "Clients",
      path: "/clients",
    },
    {
      label: "Locations",
      path: "/locations",
    },
    {
      label: "Devices",
      path: "/devices",
    },
    {
      label: "Cameras",
      path: "/cameras",
    },
    {
      label: "Alerts",
      path: "/alerts",
    },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-text">AiTecServ Monitor App</span>
      </div>

      <nav className="sidebar-nav">
        {navigation.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-link-icon" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;