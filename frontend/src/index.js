import React from "react";
import ReactDOM from "react-dom/client";
import * as Sentry from "@sentry/react";
import "@/index.css";
import "@/theme-prep-refined.css";
import App from "@/App";
import * as serviceWorkerRegistration from "@/serviceWorkerRegistration";

if (process.env.REACT_APP_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.REACT_APP_SENTRY_DSN,
    environment: process.env.NODE_ENV,
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 0,
  });
}

// WebMCP is an optional browser capability. Keep the tools read-only and
// feature-detect the API so normal browsers are unaffected.
const registerWebMCP = () => {
  const modelContext = navigator.modelContext;
  if (!modelContext || typeof modelContext.provideContext !== "function") return;

  const backendUrl = (process.env.REACT_APP_BACKEND_URL || "https://prep-academy.onrender.com").replace(/\/$/, "");
  const json = async (path) => {
    const response = await fetch(`${backendUrl}/api${path}`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    return response.json();
  };

  modelContext.provideContext({
    tools: [
      {
        name: "prep_academy_overview",
        description: "Get public Prep Academy platform statistics and available exam areas.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false },
        execute: async () => {
          const [specialties, exams] = await Promise.all([json("/specialties"), json("/exam-types")]);
          return { content: [{ type: "text", text: JSON.stringify({ specialties, exams }) }] };
        },
      },
      {
        name: "prep_academy_guest_questions",
        description: "Fetch a small public sample of medical practice questions without authentication.",
        inputSchema: {
          type: "object",
          properties: { limit: { type: "integer", minimum: 1, maximum: 10, default: 3 } },
          additionalProperties: false,
        },
        execute: async ({ limit = 3 } = {}) => {
          const questions = await json(`/guest/questions?limit=${Math.min(10, Math.max(1, Number(limit) || 3))}`);
          return { content: [{ type: "text", text: JSON.stringify(questions) }] };
        },
      },
    ],
  });
};

try { registerWebMCP(); } catch (error) { console.debug("WebMCP unavailable", error); }

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

serviceWorkerRegistration.register({
  onUpdate: () => {
    if (window.confirm("Neue Version verfügbar. Seite neu laden?")) {
      window.location.reload();
    }
  },
});

requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    const ls = document.getElementById("loading-screen");
    if (ls) {
      ls.style.transition = "opacity 0.3s ease";
      ls.style.opacity = "0";
      ls.style.pointerEvents = "none";
      setTimeout(() => { ls.remove?.(); }, 350);
    }
  });
});
