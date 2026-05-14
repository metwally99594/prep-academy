import { useState, useEffect } from "react";
import { API } from "@/lib/api";

// Phase 1: Raw fetch — bypasses axios, interceptors, and auth entirely
function RawFetch({ url, label }) {
  const [status, setStatus] = useState("pending");
  const [ms, setMs] = useState(null);
  const [body, setBody] = useState(null);

  useEffect(() => {
    const t0 = performance.now();
    fetch(url, { signal: AbortSignal.timeout(10000) })
      .then(async (r) => {
        setMs(Math.round(performance.now() - t0));
        setStatus(r.ok ? `✅ ${r.status}` : `❌ ${r.status}`);
        try { setBody(await r.json()); } catch { setBody(null); }
      })
      .catch((e) => {
        setMs(Math.round(performance.now() - t0));
        setStatus(`❌ ${e.name}: ${e.message}`);
      });
  }, [url]);

  return (
    <div style={row}>
      <b>{label}</b>
      <span style={{ color: status.startsWith("✅") ? "#4ade80" : "#f87171" }}>{status}</span>
      {ms !== null && <span style={{ color: "#9ca3af" }}>{ms}ms</span>}
      {body && <pre style={pre}>{JSON.stringify(body, null, 2)}</pre>}
    </div>
  );
}

// Phase 2: localStorage + token check
function StorageCheck() {
  const token = localStorage.getItem("token");
  const theme = localStorage.getItem("theme");
  const splash = sessionStorage.getItem("splashSeen");
  return (
    <div style={row}>
      <b>LocalStorage</b>
      <span>token: {token ? `✅ present (${token.slice(0, 20)}...)` : "⬜ none"}</span>
      <span>theme: {theme || "⬜ not set"}</span>
      <span>splashSeen: {splash || "⬜ not set"}</span>
    </div>
  );
}

// Phase 3: Service Worker status
function SWCheck() {
  const [swInfo, setSwInfo] = useState("checking...");
  useEffect(() => {
    if (!("serviceWorker" in navigator)) { setSwInfo("❌ not supported"); return; }
    navigator.serviceWorker.getRegistrations().then((regs) => {
      if (regs.length === 0) {
        setSwInfo("✅ none registered");
      } else {
        setSwInfo(`⚠️ ${regs.length} SW registered: ${regs.map(r => r.scope).join(", ")}`);
      }
    }).catch((e) => setSwInfo(`❌ ${e.message}`));
  }, []);
  return (
    <div style={row}>
      <b>Service Worker</b>
      <span style={{ color: swInfo.startsWith("✅") ? "#4ade80" : swInfo.startsWith("⚠️") ? "#fb923c" : "#f87171" }}>{swInfo}</span>
    </div>
  );
}

// Phase 4: Cache API status
function CacheCheck() {
  const [cacheInfo, setCacheInfo] = useState("checking...");
  useEffect(() => {
    if (!("caches" in window)) { setCacheInfo("not supported"); return; }
    caches.keys().then((keys) => {
      if (keys.length === 0) {
        setCacheInfo("✅ no caches");
      } else {
        setCacheInfo(`⚠️ ${keys.length} cache(s): ${keys.join(", ")}`);
      }
    }).catch((e) => setCacheInfo(`❌ ${e.message}`));
  }, []);
  return (
    <div style={row}>
      <b>Cache API</b>
      <span style={{ color: cacheInfo.startsWith("✅") ? "#4ade80" : "#fb923c" }}>{cacheInfo}</span>
    </div>
  );
}

// Phase 5: Auth/me with current token
function AuthMeCheck() {
  const [result, setResult] = useState("pending...");
  const [ms, setMs] = useState(null);
  useEffect(() => {
    const token = localStorage.getItem("token");
    const t0 = performance.now();
    fetch(`${API}/auth/me`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: AbortSignal.timeout(10000),
    })
      .then(async (r) => {
        setMs(Math.round(performance.now() - t0));
        const body = await r.json().catch(() => ({}));
        if (r.ok) {
          setResult(`✅ ${r.status} — user: ${body.email || body.name || JSON.stringify(body)}`);
        } else {
          setResult(`❌ ${r.status} — ${JSON.stringify(body)}`);
        }
      })
      .catch((e) => {
        setMs(Math.round(performance.now() - t0));
        setResult(`❌ ${e.name}: ${e.message}`);
      });
  }, []);
  return (
    <div style={row}>
      <b>/auth/me</b>
      <span style={{ color: result.startsWith("✅") ? "#4ade80" : result === "pending..." ? "#9ca3af" : "#f87171" }}>{result}</span>
      {ms !== null && <span style={{ color: "#9ca3af" }}>{ms}ms</span>}
    </div>
  );
}

export default function DebugPage() {
  return (
    <div style={page}>
      <h1 style={{ color: "#f9fafb", fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        PrepAcademy — Diagnostic Report
      </h1>
      <p style={{ color: "#6b7280", fontSize: 12, marginBottom: 24 }}>
        {new Date().toISOString()} · {window.location.href}
      </p>

      <section style={section}>
        <h2 style={heading}>Phase 1 — Backend Health</h2>
        <RawFetch url={`${API}/health`} label="/api/health" />
        <RawFetch url={`${API}/specialties`} label="/api/specialties" />
        <RawFetch url={`${API}/exam-types`} label="/api/exam-types" />
      </section>

      <section style={section}>
        <h2 style={heading}>Phase 2 — Auth Flow</h2>
        <StorageCheck />
        <AuthMeCheck />
      </section>

      <section style={section}>
        <h2 style={heading}>Phase 3 — Browser State</h2>
        <SWCheck />
        <CacheCheck />
        <div style={row}>
          <b>React mounted</b>
          <span style={{ color: "#4ade80" }}>✅ yes (you see this page)</span>
        </div>
        <div style={row}>
          <b>API base URL</b>
          <span style={{ color: "#9ca3af" }}>{API}</span>
        </div>
        <div style={row}>
          <b>User Agent</b>
          <span style={{ color: "#9ca3af", fontSize: 11 }}>{navigator.userAgent}</span>
        </div>
      </section>

      <section style={section}>
        <h2 style={heading}>Actions</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button style={btn} onClick={() => { localStorage.removeItem("token"); window.location.reload(); }}>
            Clear token + reload
          </button>
          <button style={btn} onClick={() => { caches.keys().then(ks => ks.forEach(k => caches.delete(k))); navigator.serviceWorker?.getRegistrations().then(rs => rs.forEach(r => r.unregister())); alert("Cleared"); }}>
            Nuke SW + caches
          </button>
          <button style={btn} onClick={() => window.location.href = "/"}>
            Go home
          </button>
          <button style={btn} onClick={() => window.location.reload()}>
            Refresh diagnostics
          </button>
        </div>
      </section>
    </div>
  );
}

const page = { minHeight: "100vh", background: "#0a0e1a", padding: "32px 24px", fontFamily: "ui-monospace, monospace", fontSize: 13 };
const section = { marginBottom: 28, padding: 16, background: "#111827", borderRadius: 8, border: "1px solid #1f2937" };
const heading = { color: "#3b82f6", fontSize: 13, fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.1em" };
const row = { display: "flex", flexDirection: "column", gap: 4, padding: "10px 0", borderBottom: "1px solid #1f2937" };
const pre = { background: "#0d1117", color: "#86efac", padding: 8, borderRadius: 4, fontSize: 11, overflow: "auto", maxHeight: 120, margin: "4px 0 0" };
const btn = { padding: "6px 14px", background: "#1f2937", color: "#f9fafb", border: "1px solid #374151", borderRadius: 6, cursor: "pointer", fontSize: 12 };
