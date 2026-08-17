import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard/Dashboard";
import Countries from "./pages/Countries/Countries";
import Clients from "./pages/Clients/Clients";
import Locations from "./pages/Locations/Locations";
import Devices from "./pages/Devices/Devices";
import Cameras from "./pages/Cameras/Cameras";
import Alerts from "./pages/Alerts/Alerts";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/countries" element={<Countries />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/locations" element={<Locations />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/cameras" element={<Cameras />} />
          <Route path="/alerts" element={<Alerts />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;