import { memo } from "react";
import { User } from "lucide-react";

function fmtConvTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays < 7) return d.toLocaleDateString("de-AT", { weekday: "short" });
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" });
}

export const ConversationItem = memo(function ConversationItem({ conv, isActive, userId, onClick }) {
  const info = conv.participants_info || {};
  const otherId = (conv.participants || []).find(id => id !== userId);
  const other = otherId ? (info[otherId] || { name: "Unbekannt" }) : { name: "Unbekannt" };
  const hasUnread = (conv.unread_count || 0) > 0;
  const isMe = conv.last_message_sender_id === userId;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left flex items-start gap-3 px-4 py-3 border-b border-border/20 transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary ${
        isActive ? "bg-primary/5 border-l-2 border-l-primary" : "border-l-2 border-l-transparent"
      }`}
      aria-pressed={isActive}
    >
      <div className="relative mt-0.5 shrink-0">
        <div className="w-9 h-9 rounded-full bg-primary/15 flex items-center justify-center">
          <User className="w-4 h-4 text-primary" />
        </div>
        {hasUnread && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-primary rounded-full border-2 border-background" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2 mb-0.5">
          <span className={`text-sm truncate ${hasUnread ? "font-semibold" : "font-medium"}`}>
            {other.name}
            {other.is_admin && (
              <span className="ml-1.5 text-[9px] px-1 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold tracking-wide uppercase">
                Admin
              </span>
            )}
          </span>
          <span className="text-[11px] text-muted-foreground/55 shrink-0">
            {fmtConvTime(conv.last_message_at)}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <p className={`text-xs truncate flex-1 leading-snug ${hasUnread ? "text-foreground" : "text-muted-foreground"}`}>
            {isMe && <span className="text-muted-foreground/50">Du: </span>}
            {conv.last_message_preview || <span className="italic">Unterhaltung starten…</span>}
          </p>
          {hasUnread && (
            <span className="w-5 h-5 bg-primary rounded-full text-[10px] font-bold text-primary-foreground flex items-center justify-center shrink-0">
              {conv.unread_count > 9 ? "9+" : conv.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
});
