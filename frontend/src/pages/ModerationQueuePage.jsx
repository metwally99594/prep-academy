import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/App";
import { ShieldAlert, AlertCircle, Loader2, RefreshCcw, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useModerationQueue } from "@/hooks/useModerationQueue";
import { useAuditLog } from "@/hooks/useAuditLog";
import { ModerationQueueItem } from "@/components/moderation/ModerationQueueItem";
import { InfiniteScrollSentinel } from "@/components/community/InfiniteScrollSentinel";

const TABS = [
  { key: "pending",  label: "Ausstehend",  reviewed: false },
  { key: "reviewed", label: "Überprüft",   reviewed: true },
  { key: "audit",    label: "Audit-Log",   reviewed: null },
];

const SEVERITIES = [
  { value: "", label: "Alle" },
  { value: "critical", label: "Kritisch" },
  { value: "high",     label: "Hoch" },
  { value: "medium",   label: "Mittel" },
  { value: "low",      label: "Niedrig" },
];

const ACTION_LABELS = {
  approve: { label: "Genehmigt", class: "text-emerald-600 bg-emerald-500/10" },
  hide:    { label: "Ausgeblendet", class: "text-slate-600 bg-slate-500/10" },
  delete:  { label: "Gelöscht", class: "text-red-600 bg-red-500/10" },
};

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

function AuditSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="rounded-xl border border-border/40 bg-card p-4 animate-pulse">
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-muted shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted rounded w-32" />
              <div className="h-3 bg-muted rounded w-2/3" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatAuditTs(ts) {
  const d = new Date(ts * 1000);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `vor ${mins} Min.`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `vor ${hrs} Std.`;
  return d.toLocaleDateString("de-AT", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function ModerationQueuePage() {
  const { token } = useAuth();
  const [tab, setTab] = useState("pending");
  const [severity, setSeverity] = useState("");
  const [cursor, setCursor] = useState(0);
  const { items, loading, loadingMore, hasMore, error, load, loadMore, takeAction } =
    useModerationQueue(token);
  const audit = useAuditLog(token);

  const reviewed = TABS.find(t => t.key === tab)?.reviewed ?? false;
  const isAudit = tab === "audit";

  // Load when tab or severity changes
  useEffect(() => {
    if (isAudit) {
      audit.load();
    } else {
      load(reviewed, severity);
      setCursor(0);
    }
  }, [tab, severity]);

  // Keyboard shortcuts (only for pending tab)
  useEffect(() => {
    if (isAudit || reviewed || items.length === 0) return;
    const handler = (e) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
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
  }, [items, cursor, reviewed, isAudit]);

  const handleAction = useCallback(async (item, action, note = null) => {
    await takeAction(item, action, note);
    setCursor(c => Math.max(0, c - 1));
    const labels = { approve: "Genehmigt", hide: "Ausgeblendet", delete: "Gelöscht" };
    toast.success(labels[action] || "Aktion durchgeführt");
  }, [takeAction]);

  const handleTabChange = (key) => {
    setTab(key);
    if (key === "audit") {
      setSeverity("");
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isAudit ? 'bg-slate-500/10' : 'bg-amber-500/10'}`}>
            {isAudit ? <ClipboardList className="w-5 h-5 text-slate-500" /> : <ShieldAlert className="w-5 h-5 text-amber-500" />}
          </div>
          <div>
            <h1 className="text-lg font-bold">Moderationswarteschlange</h1>
            {!isAudit && (
              <p className="text-xs text-muted-foreground">
                Tastatur: <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">↑↓</kbd> navigieren ·{" "}
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">A</kbd> genehmigen ·{" "}
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">H</kbd> ausblenden ·{" "}
                <kbd className="px-1 py-0.5 rounded bg-muted text-[10px] font-mono">D</kbd> löschen
              </p>
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => isAudit ? audit.load() : load(reviewed, severity)}
          disabled={loading || audit.loading}
        >
          <RefreshCcw className={`w-3.5 h-3.5 ${loading || audit.loading ? "animate-spin" : ""}`} />
          Aktualisieren
        </Button>
      </div>

      {/* Tab bar */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
        <div className="flex gap-1 bg-muted/40 rounded-xl p-1">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => handleTabChange(t.key)}
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
        {!isAudit && (
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
        )}
      </div>

      {/* Error */}
      {(error || audit.error) && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error || audit.error}
        </div>
      )}

      {/* Audit Log */}
      {isAudit ? (
        audit.loading ? (
          <AuditSkeleton />
        ) : audit.items.length === 0 ? (
          <div className="text-center py-16">
            <ClipboardList className="w-12 h-12 mx-auto mb-3 text-muted-foreground/20" />
            <p className="text-sm text-muted-foreground">Keine Audit-Einträge</p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {audit.items.map((entry) => {
                const actionInfo = ACTION_LABELS[entry.action] || { label: entry.action, class: "text-muted-foreground bg-muted/50" };
                return (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-border/40 bg-card px-4 py-3"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${actionInfo.class}`}>
                        {actionInfo.label}
                      </span>
                      <span className="text-[10px] font-mono text-muted-foreground uppercase">
                        {entry.target_type}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {entry.target_id?.slice(0, 8)}…
                      </span>
                      {entry.reason && (
                        <span className="text-[10px] text-muted-foreground italic">
                          „{entry.reason}“
                        </span>
                      )}
                      <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                        {formatAuditTs(entry.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground">
                        von {entry.admin_name || entry.admin_id?.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            {audit.hasMore && (
              <InfiniteScrollSentinel
                onVisible={audit.loadMore}
                loading={audit.loadingMore}
              />
            )}
          </>
        )
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
