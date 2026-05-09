import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { ShieldAlert, AlertCircle, Loader2, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useModerationQueue } from "@/hooks/useModerationQueue";
import { ModerationQueueItem } from "@/components/moderation/ModerationQueueItem";
import { InfiniteScrollSentinel } from "@/components/community/InfiniteScrollSentinel";

const TABS = [
  { key: "pending",  label: "Ausstehend",  reviewed: false },
  { key: "reviewed", label: "Überprüft",   reviewed: true },
];

const SEVERITIES = [
  { value: "", label: "Alle" },
  { value: "critical", label: "Kritisch" },
  { value: "high",     label: "Hoch" },
  { value: "medium",   label: "Mittel" },
  { value: "low",      label: "Niedrig" },
];

function QueueSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="rounded-xl border border-border/40 bg-card p-4 animate-pulse">
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-muted shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex gap-2">
                <div className="h-4 bg-muted rounded w-20" />
                <div className="h-4 bg-muted rounded w-16" />
                <div className="h-4 bg-muted rounded w-24" />
              </div>
              <div className="h-3 bg-muted rounded w-full" />
              <div className="h-3 bg-muted rounded w-4/5" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ModerationQueuePage() {
  const { token } = useAuth();
  const [tab, setTab] = useState("pending");
  const [severity, setSeverity] = useState("");
  const [cursor, setCursor] = useState(0);
  const { items, loading, loadingMore, hasMore, error, load, loadMore, takeAction } =
    useModerationQueue(token);

  const reviewed = TABS.find(t => t.key === tab)?.reviewed ?? false;

  // Load when tab or severity changes
  useEffect(() => {
    load(reviewed, severity);
    setCursor(0);
  }, [tab, severity]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
      if (items.length === 0 || reviewed) return;
      const item = items[cursor];
      if (!item) return;
      if (e.key === "ArrowDown") { setCursor(c => Math.min(c + 1, items.length - 1)); e.preventDefault(); }
      else if (e.key === "ArrowUp") { setCursor(c => Math.max(c - 1, 0)); e.preventDefault(); }
      else if (e.key === "a" || e.key === "A") { handleAction(item, "approve"); }
      else if (e.key === "h" || e.key === "H") { handleAction(item, "hide"); }
      else if (e.key === "d" || e.key === "D") { handleAction(item, "delete"); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [items, cursor, reviewed]);

  const handleAction = useCallback(async (item, action, note = null) => {
    await takeAction(item, action, note);
    // Move cursor up if we deleted the last item
    setCursor(c => Math.max(0, c - 1));
    const labels = { approve: "Genehmigt", hide: "Ausgeblendet", delete: "Gelöscht" };
    toast.success(labels[action] || "Aktion durchgeführt");
  }, [takeAction]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-lg font-bold">Moderationswarteschlange</h1>
            <p className="text-xs text-muted-foreground">
              Tastatur: <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">↑↓</kbd> navigieren ·{" "}
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">A</kbd> genehmigen ·{" "}
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">H</kbd> ausblenden ·{" "}
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">D</kbd> löschen
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => load(reviewed, severity)}
          disabled={loading}
        >
          <RefreshCcw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Aktualisieren
        </Button>
      </div>

      {/* Tab + severity bar */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
        <div className="flex gap-1 bg-muted/40 rounded-xl p-1">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                tab === t.key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {SEVERITIES.map(s => (
            <button
              key={s.value}
              onClick={() => setSeverity(s.value)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                severity === s.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Queue list */}
      {loading ? (
        <QueueSkeleton />
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <ShieldAlert className="w-12 h-12 mx-auto mb-3 text-muted-foreground/20" />
          <p className="text-sm text-muted-foreground">
            {tab === "pending" ? "Keine ausstehenden Einträge" : "Keine überprüften Einträge"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, idx) => (
            <ModerationQueueItem
              key={item.id}
              item={item}
              isFocused={idx === cursor && !reviewed}
              onFocus={() => setCursor(idx)}
              onAction={handleAction}
              reviewed={reviewed}
            />
          ))}
        </div>
      )}

      {!loading && hasMore && (
        <InfiniteScrollSentinel
          onVisible={() => loadMore(reviewed, severity)}
          loading={loadingMore}
        />
      )}
    </div>
  );
}
