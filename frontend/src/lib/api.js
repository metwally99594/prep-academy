import axios from "axios";

const envUrl = (process.env.REACT_APP_BACKEND_URL || "").trim().replace(/\/$/, "");
const isBrowser = typeof window !== "undefined";
const isLocalHost =
  isBrowser &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export const BACKEND_URL = envUrl || (isLocalHost ? "http://127.0.0.1:8000" : "");
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

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
      if (isBrowser) window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;
