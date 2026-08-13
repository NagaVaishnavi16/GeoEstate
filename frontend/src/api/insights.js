const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export async function getInsights() {
  if (!API_BASE_URL) throw new Error("VITE_API_BASE_URL is not configured.");
  const response = await fetch(`${API_BASE_URL}/api/v1/insights`);
  if (!response.ok) throw new Error("Insights are temporarily unavailable.");
  return response.json();
}
