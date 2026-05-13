export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      typeof data === "object" && data !== null && "detail" in data
        ? data.detail
        : "The request could not be completed.";
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(" ") : message);
  }

  return data;
}

export async function apiRequest(path, { method = "GET", body, token, isForm = false } = {}) {
  const headers = {
    Accept: "application/json",
  };

  if (body !== undefined && !isForm) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });

  return parseResponse(response);
}

export const apiClient = {
  get: (path, token) => apiRequest(path, { token }),
  post: (path, body, token) => apiRequest(path, { method: "POST", body, token }),
  postForm: (path, body, token) => apiRequest(path, { method: "POST", body, token, isForm: true }),
  put: (path, body, token) => apiRequest(path, { method: "PUT", body, token }),
};
