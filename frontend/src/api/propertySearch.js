const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function naturalSearch(query) {
  if (!API_BASE_URL) {
    throw new ApiError("VITE_API_BASE_URL is not configured.");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/search/natural`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit: 50, offset: 0 }),
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("The property service returned an invalid response.", response.status);
  }

  if (!response.ok) {
    throw new ApiError(payload.detail ?? "Unable to complete the search right now.", response.status);
  }
  return payload;
}
