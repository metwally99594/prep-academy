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
