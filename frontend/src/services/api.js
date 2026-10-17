import { apiRequest } from "./http";
import { scopeQuery } from "../utils/scope";

export { fetchAll } from "./http";

// builds list, get, create, update and delete for a rest resource, approve is added for resources created from mqtt
function makeCrudApi(resourcePath, { approvable = false } = {}) {
  const api = {
    list: (params = "") => apiRequest(`/${resourcePath}/${params}`),
    get: (id) => apiRequest(`/${resourcePath}/${id}/`),
    create: (data) => apiRequest(`/${resourcePath}/`, { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) => apiRequest(`/${resourcePath}/${id}/`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id) => apiRequest(`/${resourcePath}/${id}/`, { method: "DELETE" }),
  };

  if (approvable) {
    api.approve = (id) => apiRequest(`/${resourcePath}/${id}/approve/`, { method: "POST" });
  }

  return api;
}

export const countriesApi = makeCrudApi("countries", { approvable: true });
export const customersApi = makeCrudApi("customers", { approvable: true });
export const locationsApi = makeCrudApi("locations", { approvable: true });
export const devicesApi = makeCrudApi("devices", { approvable: true });
export const camerasApi = makeCrudApi("cameras", { approvable: true });

// problems of devices and cameras (offline, unhealthy components, errors)
export const problemsApi = {
  list: (params = "") => apiRequest(`/problems/${params}`),
};

// events detected by the cameras
export const detectionsApi = {
  list: (params = "") => apiRequest(`/detections/${params}`),
};

// manually resolves an alert, it is created again if the problem is reported again
export const alertsApi = {
  resolveDevice: (id) => apiRequest(`/alerts/device/${id}/resolve/`, { method: "POST" }),
  resolveCamera: (id) => apiRequest(`/alerts/camera/${id}/resolve/`, { method: "POST" }),

  // resolves an alert from its combined id, like "device-42" or "camera-17"
  resolveById(compositeId) {
    const [kind, rawId] = String(compositeId).split("-");

    if (kind === "device") return this.resolveDevice(rawId);
    if (kind === "camera") return this.resolveCamera(rawId);

    return Promise.reject(new Error(`Unknown alert id: ${compositeId}`));
  },
};

// country > customer > location > device > camera tree, with the scope inactive records are hidden or shown
export const monitorApi = {
  tree: ({ scope } = {}) => apiRequest(`/monitor/tree/${scope ? `?${scopeQuery(scope)}` : ""}`),
};

// everything the dashboard page shows
export const dashboardApi = {
  get: ({ scope } = {}) => apiRequest(`/dashboard/${scope ? `?${scopeQuery(scope)}` : ""}`),
};

// settings stored in the backend .env file, leave mqtt_password out to keep the current one
export const settingsApi = {
  get: () => apiRequest("/settings/"),
  update: (data) => apiRequest("/settings/", { method: "PUT", body: JSON.stringify(data) }),
};
