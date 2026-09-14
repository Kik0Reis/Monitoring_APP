import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard/Dashboard";
import Countries from "./pages/Countries/countries";
import Clients from "./pages/Clients/clients";
import Locations from "./pages/Locations/locations";
import Devices from "./pages/Devices/devices";
import Cameras from "./pages/Cameras/cameras";
import Alerts from "./pages/Alerts/alerts";

import CountryDetail from "./pages/CountryDetail/CountryDetail";
import CustomerDetail from "./pages/CustomerDetail/CustomerDetail";
import LocationDetail from "./pages/LocationDetail/LocationDetail";
import DeviceDetail from "./pages/DeviceDetail/DeviceDetail";
import CameraDetail from "./pages/CameraDetail/CameraDetail";
import Settings from "./pages/Settings/Settings";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />

          <Route path="/countries" element={<Countries />} />
          <Route path="/countries/:countryId" element={<CountryDetail />} />

          <Route path="/clients" element={<Clients />} />
          <Route path="/clients/:customerId" element={<CustomerDetail />} />

          <Route path="/locations" element={<Locations />} />
          <Route path="/locations/:locationId" element={<LocationDetail />} />

          <Route path="/devices" element={<Devices />} />
          <Route path="/devices/:deviceId" element={<DeviceDetail />} />

          <Route path="/cameras" element={<Cameras />} />
          <Route path="/cameras/:cameraId" element={<CameraDetail />} />

          <Route path="/alerts" element={<Alerts />} />

          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
