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
    let error;

    try {
      error = await response.json();
    } catch {
      error = null;
    }

    throw new Error(
      error?.detail ||
        error?.message ||
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