import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

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
