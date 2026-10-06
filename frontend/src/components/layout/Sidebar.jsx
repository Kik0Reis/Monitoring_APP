import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  LayoutList,
  Cpu,
  Camera,
  Bell,
  Settings,
  ChevronDown,
} from "lucide-react";

// "Monitor" groups the tree view together with the flat Devices/Cameras
// lists -- Countries/Clients/Locations still exist as their own pages
// (linked to from the tree and from breadcrumbs), they just don't get a
// top-level sidebar entry of their own anymore.
const MONITOR_ITEMS = [
  { label: "Views", path: "/monitor/views", icon: LayoutList },
  { label: "Devices", path: "/devices", icon: Cpu },
  { label: "Cameras", path: "/cameras", icon: Camera },
];

function Sidebar() {
  const location = useLocation();

  const monitorActive = MONITOR_ITEMS.some((item) =>
    location.pathname.startsWith(item.path)
  );

  const [monitorOpen, setMonitorOpen] = useState(monitorActive);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-text">AiTecServ Monitor App</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
        >
          <LayoutDashboard className="sidebar-link-icon" size={18} strokeWidth={2} />
          <span>Dashboard</span>
        </NavLink>

        <button
          type="button"
          className={`sidebar-link sidebar-group-toggle ${monitorActive ? "active" : ""}`}
          onClick={() => setMonitorOpen((open) => !open)}
          aria-expanded={monitorOpen}
        >
          <LayoutList className="sidebar-link-icon" size={18} strokeWidth={2} />
          <span>Monitor</span>
          <ChevronDown
            className={`sidebar-group-chevron ${monitorOpen ? "open" : ""}`}
            size={16}
            strokeWidth={2}
          />
        </button>

        {monitorOpen && (
          <div className="sidebar-group">
            {MONITOR_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `sidebar-link sidebar-sublink ${isActive ? "active" : ""}`
                }
              >
                <item.icon className="sidebar-link-icon" size={16} strokeWidth={2} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        )}

        <NavLink
          to="/alerts"
          className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
        >
          <Bell className="sidebar-link-icon" size={18} strokeWidth={2} />
          <span>Alerts</span>
        </NavLink>

        <NavLink
          to="/settings"
          className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
        >
          <Settings className="sidebar-link-icon" size={18} strokeWidth={2} />
          <span>Settings</span>
        </NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;
