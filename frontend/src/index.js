import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import "@/theme-prep-refined.css";
import App from "@/App";
import * as serviceWorkerRegistration from "@/serviceWorkerRegistration";

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
