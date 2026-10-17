import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import "./layout.css";

// page frame with the sidebar on the left and the current page on the right
function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
