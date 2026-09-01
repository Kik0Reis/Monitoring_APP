// Hardcoding this would break the app for anyone who isn't running the
// backend on localhost:8000 (staging, production, another dev's machine
// with a different port). VITE_API_BASE_URL lets that be configured per
// environment; it defaults to the local dev backend when unset.
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
      // Response body wasn't JSON (or was empty) — fall through to the
      // generic error message below.
    }

    if (error?.detail) {
      throw new Error(error.detail);
    }

    if (error?.message) {
      throw new Error(error.message);
    }

    // Django serializer validation errors
    if (error && typeof error === "object") {
      const messages = Object.entries(error)
        .flatMap(([field, messages]) => {
          if (Array.isArray(messages)) {
            return messages.map(
              (message) => `${field}: ${message}`
            );
          }

          return [`${field}: ${messages}`];
        });

      if (messages.length > 0) {
        throw new Error(messages.join(" "));
      }
    }

    throw new Error(
      "Something went wrong while communicating with the API."
    );
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/**
 * Fetches every page of a (potentially paginated) list endpoint.
 *
 * Used only to populate dropdowns (e.g. "which country does this client
 * belong to") where we need the full set of options, not just the first
 * page of results.
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
 * Shared "approve" action for resources that can be auto-provisioned
 * from MQTT (countries/customers/locations/devices) and therefore carry
 * a pending_review flag. Confirms a human has looked at the record.
 */
function makeApprove(resourcePath) {
  return function approve(id) {
    return apiRequest(`/${resourcePath}/${id}/approve/`, {
      method: "POST",
    });
  };
}

export const countriesApi = {
  list(params = "") {
    return apiRequest(`/countries/${params}`);
  },

  get(id) {
    return apiRequest(`/countries/${id}/`);
  },

  create(data) {
    return apiRequest("/countries/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiRequest(`/countries/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id) {
    return apiRequest(`/countries/${id}/`, {
      method: "DELETE",
    });
  },

  approve: makeApprove("countries"),
};

export const customersApi = {
  list(params = "") {
    return apiRequest(`/customers/${params}`);
  },

  get(id) {
    return apiRequest(`/customers/${id}/`);
  },

  create(data) {
    return apiRequest("/customers/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiRequest(`/customers/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id) {
    return apiRequest(`/customers/${id}/`, {
      method: "DELETE",
    });
  },

  approve: makeApprove("customers"),
};

export const locationsApi = {
  list(params = "") {
    return apiRequest(`/locations/${params}`);
  },

  get(id) {
    return apiRequest(`/locations/${id}/`);
  },

  create(data) {
    return apiRequest("/locations/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiRequest(`/locations/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id) {
    return apiRequest(`/locations/${id}/`, {
      method: "DELETE",
    });
  },

  approve: makeApprove("locations"),
};

export const devicesApi = {
  list(params = "") {
    return apiRequest(`/devices/${params}`);
  },

  get(id) {
    return apiRequest(`/devices/${id}/`);
  },

  create(data) {
    return apiRequest("/devices/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiRequest(`/devices/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id) {
    return apiRequest(`/devices/${id}/`, {
      method: "DELETE",
    });
  },

  approve: makeApprove("devices"),
};

export const camerasApi = {
  list(params = "") {
    return apiRequest(`/cameras/${params}`);
  },

  get(id) {
    return apiRequest(`/cameras/${id}/`);
  },

  create(data) {
    return apiRequest("/cameras/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiRequest(`/cameras/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id) {
    return apiRequest(`/cameras/${id}/`, {
      method: "DELETE",
    });
  },

  approve: makeApprove("cameras"),
};

// Device/camera health & connectivity problems (offline, unhealthy
// component, MQTT/system errors, camera errors). Active-only by default.
export const problemsApi = {
  list(params = "") {
    return apiRequest(`/problems/${params}`);
  },
};

// Real camera detections reported over MQTT (smoke, person, etc.). Plain
// chronological event log, no active/resolved concept.
export const detectionsApi = {
  list(params = "") {
    return apiRequest(`/detections/${params}`);
  },
};

export const dashboardApi = {
  async get() {
    const response = await fetch(
      `${API_BASE_URL}/dashboard/`
    );

    if (!response.ok) {
      throw new Error(
        "Failed to load dashboard."
      );
    }

    return response.json();
  },
};