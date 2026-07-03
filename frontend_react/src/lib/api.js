// Thin fetch wrappers around the Flask backend API.
// The backend contract (routes + JSON shapes) is unchanged from the
// original project — this file only mirrors what frontend/js/*.js
// used to call directly.
//
// PRODUCTION DEPLOYMENT: the frontend (Vercel) and backend (Render /
// Railway / your own server) are typically deployed separately, on
// different origins. Set VITE_API_BASE_URL (in frontend_react/.env,
// or as an env var in your Vercel project settings) to the backend's
// full URL, e.g. https://ai-office-analytics-api.onrender.com — every
// request below is built against that base. Leave it unset for local
// dev / same-origin deployments (Flask serving the built frontend
// itself) and all URLs stay relative, exactly as before.
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

/** Turns a backend-relative path (e.g. "/photo/abc.jpg") into an absolute
 * URL against API_BASE. Used for <img>/<video> src attributes, which
 * unlike fetch() can't be routed through a same-origin dev proxy. */
export function resolveUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path}`;
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`);
  return res.json();
}

// -------- dashboard / live status --------

export const getDashboardSummary = () => getJson("/api/dashboard_summary");
export const getCurrentEmployee = () => getJson("/api/current_employee");
export const getActivityLog = (limit = 50) => getJson(`/api/activity_log?limit=${limit}`);
export const getOpenSessions = () => getJson("/api/open_sessions");
export const getCameraStatus = () => getJson("/camera_status");

// -------- browser camera pipeline --------
// Sends one captured webcam frame (as a JPEG Blob) to the backend for
// face recognition. The backend runs the exact same recognizer /
// attendance-engine pipeline as the legacy server-camera stream and
// returns the annotated JPEG back. This is what lets face recognition
// work after deployment, since a cloud server has no physical camera
// of its own — the visitor's browser supplies the video instead.
export async function detectFrame(blob) {
  const formData = new FormData();
  formData.append("frame", blob, "frame.jpg");
  const res = await fetch(`${API_BASE}/api/detect_frame`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(`detect_frame failed (${res.status})`);
  return res.blob();
}

// -------- employees --------

export const listEmployees = () => getJson("/api/employees");

export async function saveEmployee({ id, name, hourlyRate, photoFile }) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("hourly_rate", hourlyRate);
  if (photoFile) formData.append("photo", photoFile);

  const url = id ? `${API_BASE}/api/employees/${id}` : `${API_BASE}/api/employees`;
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, { method, body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to save employee.");
  return data;
}

export async function deleteEmployee(id) {
  const res = await fetch(`${API_BASE}/api/employees/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || "Failed to delete employee.");
  }
  return res.json();
}

// -------- reports / payments --------

export function getRecords({ employeeId, date, limit = 200 } = {}) {
  const params = new URLSearchParams();
  if (employeeId) params.set("employee_id", employeeId);
  if (date) params.set("date", date);
  if (limit) params.set("limit", limit);
  return getJson(`/api/records?${params.toString()}`);
}
