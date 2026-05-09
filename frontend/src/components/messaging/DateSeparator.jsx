import { memo } from "react";

function fmtSeparatorDate(iso) {
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();
  if (isToday) return "Heute";
  if (isYesterday) return "Gestern";
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays < 7) return d.toLocaleDateString("de-AT", { weekday: "long" });
  return d.toLocaleDateString("de-AT", { day: "numeric", month: "long", year: diffDays > 365 ? "numeric" : undefined });
}

export const DateSeparator = memo(function DateSeparator({ date }) {
  return (
    <div className="flex items-center gap-3 my-4 select-none">
      <div className="flex-1 h-px bg-border/40" />
      <span className="text-[11px] text-muted-foreground/55 font-medium px-1">
        {fmtSeparatorDate(date)}
      </span>
      <div className="flex-1 h-px bg-border/40" />
    </div>
  );
});

export const UnreadDivider = memo(function UnreadDivider() {
  return (
    <div className="flex items-center gap-3 my-3 select-none">
      <div className="flex-1 h-px bg-primary/30" />
      <span className="text-[10px] text-primary/70 font-semibold px-2 py-0.5 rounded-full border border-primary/20 bg-primary/5">
        Neue Nachrichten
      </span>
      <div className="flex-1 h-px bg-primary/30" />
    </div>
  );
});
