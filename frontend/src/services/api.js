const API_BASE_URL = "http://localhost:8000/api";

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
      error = null;
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
};