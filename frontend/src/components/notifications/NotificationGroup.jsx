import { memo } from "react";
import { NotificationItem } from "./NotificationItem";

function groupByDate(notifications) {
  const groups = [];
  const seen = new Map();

  for (const n of notifications) {
    const d = new Date(n.created_at);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    let label;
    if (d.toDateString() === today.toDateString()) {
      label = "Heute";
    } else if (d.toDateString() === yesterday.toDateString()) {
      label = "Gestern";
    } else {
      label = d.toLocaleDateString("de-AT", { weekday: "long", day: "numeric", month: "long" });
    }

    if (!seen.has(label)) {
      seen.set(label, []);
      groups.push({ label, items: seen.get(label) });
    }
    seen.get(label).push(n);
  }

  return groups;
}

export const NotificationGroup = memo(function NotificationGroup({ notifications }) {
  const groups = groupByDate(notifications);

  return (
    <div className="space-y-4">
      {groups.map(group => (
        <div key={group.label} className="rounded-2xl border border-border/40 bg-card overflow-hidden">
          <div className="px-4 py-2 border-b border-border/30 bg-muted/30">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
              {group.label}
            </span>
          </div>
          <div>
            {group.items.map(n => (
              <NotificationItem key={n.id} notif={n} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
});
