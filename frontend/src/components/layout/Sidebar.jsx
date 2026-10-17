import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Bell, Camera, ChevronDown, Cpu, LayoutDashboard, LayoutList, Settings } from "lucide-react";

// the sidebar menu, an item with children is an expandable group
// Countries, Clients and Locations have no entry here, they are reached from the tree and the breadcrumbs
const NAV_ITEMS = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  {
    label: "Monitor",
    icon: LayoutList,
    children: [
      { label: "Views", path: "/monitor/views", icon: LayoutList },
      { label: "Devices", path: "/devices", icon: Cpu },
      { label: "Cameras", path: "/cameras", icon: Camera },
    ],
  },
  { label: "Alerts", path: "/alerts", icon: Bell },
  { label: "Settings", path: "/settings", icon: Settings },
];

// builds the class of a sidebar link from the active state of the router
function linkClass(extra) {
  return ({ isActive }) => `sidebar-link ${extra} ${isActive ? "active" : ""}`;
}

// a single link of the menu
function SidebarLink({ item, sub = false }) {
  return (
    <NavLink to={item.path} className={linkClass(sub ? "sidebar-sublink" : "")}>
      <item.icon className="sidebar-link-icon" size={sub ? 16 : 18} strokeWidth={2} />
      <span>{item.label}</span>
    </NavLink>
  );
}

// an expandable group of links, it starts open when one of its pages is the current page
function SidebarGroup({ item }) {
  const location = useLocation();
  const groupActive = item.children.some((child) => location.pathname.startsWith(child.path));
  const [open, setOpen] = useState(groupActive);

  return (
    <>
      <button
        type="button"
        className={`sidebar-link sidebar-group-toggle ${groupActive ? "active" : ""}`}
        onClick={() => setOpen((isOpen) => !isOpen)}
        aria-expanded={open}
      >
        <item.icon className="sidebar-link-icon" size={18} strokeWidth={2} />
        <span>{item.label}</span>
        <ChevronDown className={`sidebar-group-chevron ${open ? "open" : ""}`} size={16} strokeWidth={2} />
      </button>

      {open && (
        <div className="sidebar-group">
          {item.children.map((child) => (
            <SidebarLink key={child.path} item={child} sub />
          ))}
        </div>
      )}
    </>
  );
}

// the left menu of the app
function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-text">AiTecServ Monitor App</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) =>
          item.children ? <SidebarGroup key={item.label} item={item} /> : <SidebarLink key={item.path} item={item} />
        )}
      </nav>
    </aside>
  );
}

export default Sidebar;
