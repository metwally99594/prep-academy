import axios from "axios";

const envUrl = (process.env.REACT_APP_BACKEND_URL || "").trim().replace(/\/$/, "");
const isBrowser = typeof window !== "undefined";
const isLocalHost =
  isBrowser &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

// Strip env var if it points to localhost but we're on a real deployment domain.
// This prevents REACT_APP_BACKEND_URL=http://127.0.0.1:8000 from being baked
// into production builds when the env var is set in the Vercel dashboard.
const effectiveUrl =
  isBrowser && !isLocalHost && envUrl && (envUrl.includes("127.0.0.1") || envUrl.includes("localhost"))
    ? ""
    : envUrl;

const PRODUCTION_API_URL = "https://prep-academy.onrender.com";

export const BACKEND_URL = effectiveUrl || (isLocalHost ? "http://127.0.0.1:8000" : PRODUCTION_API_URL);
export const API = `${BACKEND_URL}/api`;

const apiClient = axios.create({ baseURL: API });

apiClient.interceptors.request.use((config) => {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof localStorage !== "undefined" &&
      localStorage.getItem("token") &&
      !error.config?.url?.includes("/auth/")
    ) {
      localStorage.removeItem("token");
      if (isBrowser) window.dispatchEvent(new CustomEvent("auth:logout"));
    }
    return Promise.reject(error);
  }
);

// Fetch with timeout using AbortController.
// Rejects cleanly after `timeoutMs` if no response. Safe fallback for cold
// Render starts or slow networks — homepage sections render with empty state.
export function fetchWithTimeout(url, options = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  return axios.get(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(id));
}

export default apiClient;
