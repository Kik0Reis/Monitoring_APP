import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";
import AlertsPage from "./pages/Alerts/AlertsPage";
import CameraDetailPage from "./pages/CameraDetail/CameraDetailPage";
import CamerasPage from "./pages/Cameras/CamerasPage";
import ClientsPage from "./pages/Clients/ClientsPage";
import CountriesPage from "./pages/Countries/CountriesPage";
import CountryDetailPage from "./pages/CountryDetail/CountryDetailPage";
import CustomerDetailPage from "./pages/CustomerDetail/CustomerDetailPage";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import DeviceDetailPage from "./pages/DeviceDetail/DeviceDetailPage";
import DevicesPage from "./pages/Devices/DevicesPage";
import LocationDetailPage from "./pages/LocationDetail/LocationDetailPage";
import LocationsPage from "./pages/Locations/LocationsPage";
import MonitorViewsPage from "./pages/MonitorViews/MonitorViewsPage";
import SettingsPage from "./pages/Settings/SettingsPage";

// every page of the app, to add a new page put it in this list
const PAGES = [
  { path: "/dashboard", element: <DashboardPage /> },
  { path: "/monitor/views", element: <MonitorViewsPage /> },
  { path: "/countries", element: <CountriesPage /> },
  { path: "/countries/:countryId", element: <CountryDetailPage /> },
  { path: "/clients", element: <ClientsPage /> },
  { path: "/clients/:customerId", element: <CustomerDetailPage /> },
  { path: "/locations", element: <LocationsPage /> },
  { path: "/locations/:locationId", element: <LocationDetailPage /> },
  { path: "/devices", element: <DevicesPage /> },
  { path: "/devices/:deviceId", element: <DeviceDetailPage /> },
  { path: "/cameras", element: <CamerasPage /> },
  { path: "/cameras/:cameraId", element: <CameraDetailPage /> },
  { path: "/alerts", element: <AlertsPage /> },
  { path: "/settings", element: <SettingsPage /> },
];

// sets up the router, every page is shown inside the main layout
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          {PAGES.map((page) => (
            <Route key={page.path} path={page.path} element={page.element} />
          ))}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
