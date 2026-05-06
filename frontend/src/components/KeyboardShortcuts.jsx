import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Keyboard, X, Search, BarChart3, BookOpen, Brain, FileText, Headphones, Home } from "lucide-react";

const SHORTCUTS = [
  { keys: ["Ctrl", "K"], action: "Suche öffnen", icon: Search },
  { keys: ["Ctrl", "/"], action: "Shortcuts anzeigen", icon: Keyboard },
  { keys: ["G", "D"], action: "Zum Dashboard", icon: BarChart3 },
  { keys: ["G", "N"], action: "Zum Notebook", icon: Brain },
  { keys: ["G", "Q"], action: "Zum Quiz", icon: BookOpen },
  { keys: ["G", "A"], action: "Zum Analyzer", icon: FileText },
  { keys: ["G", "P"], action: "Zum Podcast", icon: Headphones },
  { keys: ["G", "H"], action: "Zur Startseite", icon: Home },
];

export default function KeyboardShortcuts() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [gPressed, setGPressed] = useState(false);

  useEffect(() => {
    let gTimer;

    const onKeyDown = (e) => {
      // Don't fire when typing in inputs
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;

      // Ctrl+K → search
      if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        navigate("/search");
        return;
      }

      // Ctrl+/ → show shortcuts
      if (e.ctrlKey && e.key === "/") {
        e.preventDefault();
        setShowModal(m => !m);
        return;
      }

      // Escape → close modal
      if (e.key === "Escape") {
        setShowModal(false);
        setGPressed(false);
        return;
      }

      // G + letter navigation (vim-style)
      if (e.key === "g" && !e.ctrlKey && !e.metaKey) {
        setGPressed(true);
        gTimer = setTimeout(() => setGPressed(false), 1000);
        return;
      }

      if (gPressed) {
        clearTimeout(gTimer);
        setGPressed(false);
        const routes = { d: "/dashboard", n: "/notebook", q: "/guest-quiz", a: "/analyzer", p: "/podcast", h: "/" };
        if (routes[e.key]) navigate(routes[e.key]);
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); clearTimeout(gTimer); };
  }, [navigate, gPressed]);

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative w-full max-w-md rounded-2xl border shadow-2xl overflow-hidden"
        style={{ background: '#0c1229', borderColor: 'rgba(201,168,76,0.15)' }}
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(201,168,76,0.08)' }}>
          <div className="flex items-center gap-2">
            <Keyboard size={16} style={{ color: '#c9a84c' }} />
            <span className="font-semibold text-sm">Tastenkürzel</span>
          </div>
          <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground transition-colors">
            <X size={16} />
          </button>
        </div>
        <div className="p-4 space-y-1">
          {SHORTCUTS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={i} className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Icon size={14} />
                  <span>{s.action}</span>
                </div>
                <div className="flex items-center gap-1">
                  {s.keys.map((k, j) => (
                    <span key={j} className="px-2 py-0.5 rounded text-xs font-mono"
                      style={{ background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.12)', color: '#c9a84c' }}>
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        <div className="px-5 py-3 text-xs text-muted-foreground/40 text-center" style={{ borderTop: '1px solid rgba(201,168,76,0.05)' }}>
          Drücken Sie <kbd className="px-1 rounded" style={{ background: 'rgba(201,168,76,0.08)' }}>Esc</kbd> zum Schließen
        </div>
      </div>
    </div>
  );
}
