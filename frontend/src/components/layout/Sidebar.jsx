import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Globe,
  Users,
  MapPin,
  Cpu,
  Camera,
  Bell,
  Settings,
} from "lucide-react";

function Sidebar() {
  const navigation = [
    { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { label: "Countries", path: "/countries", icon: Globe },
    { label: "Clients", path: "/clients", icon: Users },
    { label: "Locations", path: "/locations", icon: MapPin },
    { label: "Devices", path: "/devices", icon: Cpu },
    { label: "Cameras", path: "/cameras", icon: Camera },
    { label: "Alerts", path: "/alerts", icon: Bell },
    { label: "Settings", path: "/settings", icon: Settings },
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
            <item.icon className="sidebar-link-icon" size={18} strokeWidth={2} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;
