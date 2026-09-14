// VITE_API_BASE_URL lets this be set per environment (staging, prod, another
// dev's machine); falls back to the local backend when unset.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let error = null;

    try {
      error = await response.json();
    } catch {
      // no JSON body, fall through to the generic message below
    }

    if (error?.detail) {
      throw new Error(error.detail);
    }

    if (error?.message) {
      throw new Error(error.message);
    }

    // Django serializer validation errors: {field: ["msg", ...]}
    if (error && typeof error === "object") {
      const messages = Object.entries(error).flatMap(([field, messages]) => {
        if (Array.isArray(messages)) {
          return messages.map((message) => `${field}: ${message}`);
        }

        return [`${field}: ${messages}`];
      });

      if (messages.length > 0) {
        throw new Error(messages.join(" "));
      }
    }

    throw new Error("Something went wrong while communicating with the API.");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/**
 * Fetches every page of a paginated list endpoint. Only used to populate
 * dropdowns that need the full option set, not just the first page.
 */
export async function fetchAll(listFn, params = "") {
  let url = params;
  let results = [];
  let guard = 0;

  while (url !== null && guard < 50) {
    const data = await listFn(url);

    if (data && Array.isArray(data.results)) {
      results = results.concat(data.results);

      if (data.next) {
        const nextUrl = new URL(data.next);
        url = `?${nextUrl.searchParams.toString()}`;
      } else {
        url = null;
      }
    } else {
      results = results.concat(data ?? []);
      url = null;
    }

    guard += 1;
  }

  return results;
}

/**
 * Standard list/get/create/update/delete for a REST resource, plus
 * "approve" for the ones that carry a pending_review flag (anything
 * that can be auto-provisioned from MQTT).
 */
function makeCrudApi(resourcePath, { approvable = false } = {}) {
  const api = {
    list(params = "") {
      return apiRequest(`/${resourcePath}/${params}`);
    },

    get(id) {
      return apiRequest(`/${resourcePath}/${id}/`);
    },

    create(data) {
      return apiRequest(`/${resourcePath}/`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    update(id, data) {
      return apiRequest(`/${resourcePath}/${id}/`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },

    delete(id) {
      return apiRequest(`/${resourcePath}/${id}/`, {
        method: "DELETE",
      });
    },
  };

  if (approvable) {
    api.approve = (id) =>
      apiRequest(`/${resourcePath}/${id}/approve/`, { method: "POST" });
  }

  return api;
}

export const countriesApi = makeCrudApi("countries", { approvable: true });
export const customersApi = makeCrudApi("customers", { approvable: true });
export const locationsApi = makeCrudApi("locations", { approvable: true });
export const devicesApi = makeCrudApi("devices", { approvable: true });
export const camerasApi = makeCrudApi("cameras", { approvable: true });

// Device/camera health & connectivity problems (offline, unhealthy
// component, MQTT/system errors, camera errors). Active-only by default.
export const problemsApi = {
  list(params = "") {
    return apiRequest(`/problems/${params}`);
  },
};

// Real camera detections reported over MQTT (smoke, person, etc). Plain
// chronological event log, no active/resolved concept.
export const detectionsApi = {
  list(params = "") {
    return apiRequest(`/detections/${params}`);
  },
};

export const dashboardApi = {
  get() {
    return apiRequest("/dashboard/");
  },
};

// Reads/writes backend/.env directly (see core/env_settings.py on the
// backend). mqtt_password is write-only: omit it to leave it unchanged.
export const settingsApi = {
  get() {
    return apiRequest("/settings/");
  },
  update(data) {
    return apiRequest("/settings/", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};
