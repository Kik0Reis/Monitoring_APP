// base url of the api, VITE_API_BASE_URL can change it per environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// turns an error response from the api into a readable message
async function readErrorMessage(response) {
  let error = null;

  try {
    error = await response.json();
  } catch {
    // the response has no json body
  }

  if (error?.detail) return error.detail;
  if (error?.message) return error.message;

  // validation errors from django look like {field: ["message", ...]}
  if (error && typeof error === "object") {
    const messages = Object.entries(error).flatMap(([field, fieldMessages]) =>
      Array.isArray(fieldMessages)
        ? fieldMessages.map((message) => `${field}: ${message}`)
        : [`${field}: ${fieldMessages}`]
    );

    if (messages.length > 0) return messages.join(" ");
  }

  return "Something went wrong while communicating with the API.";
}

// sends a request to the api and returns the json body, or null when there is none
export async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// loads every page of a paginated list, used to fill dropdowns that need all the options
export async function fetchAll(listFn, params = "") {
  const MAX_PAGES = 50;
  let url = params;
  let results = [];

  for (let page = 0; url !== null && page < MAX_PAGES; page += 1) {
    const data = await listFn(url);

    if (data && Array.isArray(data.results)) {
      results = results.concat(data.results);
      url = data.next ? `?${new URL(data.next).searchParams.toString()}` : null;
    } else {
      results = results.concat(data ?? []);
      url = null;
    }
  }

  return results;
}
