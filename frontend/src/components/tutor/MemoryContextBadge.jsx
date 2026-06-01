import { useEffect, useState } from "react";
import { useAuth, API } from "@/App";
import axios from "axios";
import { Brain, ChevronDown, ChevronUp } from "lucide-react";

/**
 * Memory of Mistakes — Alpha-A Tutor badge.
 *
 * Fetches /api/tutor/context/memory once on mount and renders a compact
 * collapsible indicator below the Tutor chat header. Default collapsed.
 * Hidden entirely when the user has no weak concepts on record.
 */
export default function MemoryContextBadge() {
  const { token } = useAuth();
  const [context, setContext] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    (async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const { data } = await axios.get(`${API}/tutor/context/memory`, { headers });
        if (!cancelled) {
          setContext(data);
          setLoaded(true);
        }
      } catch {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!loaded || !context) return null;
  const weaknesses = context.top_weaknesses || [];
  const recentCount = context.recent_wrongs_7d_count || 0;
  if (weaknesses.length === 0) return null;

  return (
    <div
      className="px-3 py-1.5 border-b"
      style={{ borderColor: "rgba(59,130,246,0.15)", background: "rgba(124,58,237,0.05)" }}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left text-xs flex items-center justify-between text-white/70 hover:text-white/90"
      >
        <span className="flex items-center gap-1.5">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          Memory Context: {weaknesses.length} weak concept{weaknesses.length !== 1 ? "s" : ""}
          {recentCount > 0 ? ` · ${recentCount} wrong in 7d` : ""}
        </span>
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {expanded && (
        <div className="mt-2 pl-5 text-xs space-y-1 text-white/60">
          <div>The Tutor is being told about:</div>
          {weaknesses.map((w, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="text-purple-400">•</span>
              <span>{w.concept}</span>
              {w.specialty_id && (
                <span className="text-white/40">({w.specialty_id})</span>
              )}
            </div>
          ))}
          {context.weakest_specialty && (
            <div className="text-white/50 mt-1">
              Weakest specialty: {context.weakest_specialty}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
