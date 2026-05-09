import { memo } from "react";

const SEVERITY_CONFIG = {
  critical: { label: "Kritisch", className: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/20" },
  high:     { label: "Hoch",     className: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20" },
  medium:   { label: "Mittel",   className: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" },
  low:      { label: "Niedrig",  className: "bg-muted text-muted-foreground border-border/50" },
};

const ACTION_CONFIG = {
  approve: { label: "Genehmigt", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" },
  hide:    { label: "Ausgeblendet", className: "bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/20" },
  delete:  { label: "Gelöscht",  className: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20" },
  queue:   { label: "In Warteschlange", className: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" },
};

export const ModerationStatusPill = memo(function ModerationStatusPill({ severity, action }) {
  const cfg = action ? ACTION_CONFIG[action] : SEVERITY_CONFIG[severity || "low"];
  if (!cfg) return null;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold tracking-wide uppercase ${cfg.className}`}>
      {cfg.label}
    </span>
  );
});
