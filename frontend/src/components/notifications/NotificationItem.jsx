import { memo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, Trophy, Flame, Zap, Lock, Unlock, XCircle,
  MessageCircle, MessageSquare, ThumbsUp, AtSign, Flag, Users,
} from "lucide-react";

const ICON_MAP = {
  bell: Bell,
  trophy: Trophy,
  flame: Flame,
  zap: Zap,
  lock: Lock,
  unlock: Unlock,
  "x-circle": XCircle,
  "message-circle": MessageCircle,
  "message-square": MessageSquare,
  "thumbs-up": ThumbsUp,
  "at-sign": AtSign,
  flag: Flag,
  users: Users,
};

const TYPE_COLORS = {
  community_comment:  "bg-blue-500/10 text-blue-500",
  community_reply:    "bg-violet-500/10 text-violet-500",
  community_reaction: "bg-emerald-500/10 text-emerald-500",
  community_mention:  "bg-primary/10 text-primary",
  report:             "bg-red-500/10 text-red-500",
  report_reply:       "bg-emerald-500/10 text-emerald-500",
  access_request:     "bg-amber-500/10 text-amber-500",
  access_granted:     "bg-emerald-500/10 text-emerald-500",
  access_rejected:    "bg-red-500/10 text-red-500",
  level_up:           "bg-amber-500/10 text-amber-500",
  streak_warning:     "bg-orange-500/10 text-orange-500",
};

function buildDeepLink(notif) {
  const { type, data } = notif;
  if (!data) return null;
  if (type === "community_comment" || type === "community_reply" || type === "community_mention") {
    if (data.target_id) return `/community/${data.post_id || data.target_id}`;
  }
  if (type === "community_reaction") {
    if (data.target_type === "post" && data.target_id) return `/community/${data.target_id}`;
    if (data.target_type === "comment" && data.post_id) return `/community/${data.post_id}`;
  }
  if (type === "level_up") return "/stats";
  if (type === "access_granted" || type === "access_rejected") return "/billing";
  if (type === "report" || type === "report_reply") return "/admin";
  return null;
}

function formatRelative(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Gerade eben";
  if (mins < 60) return `Vor ${mins} Min.`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Vor ${hrs} Std.`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `Vor ${days} Tag${days !== 1 ? "en" : ""}`;
  return new Date(isoStr).toLocaleDateString("de-AT", { day: "numeric", month: "short" });
}

export const NotificationItem = memo(function NotificationItem({ notif }) {
  const navigate = useNavigate();
  const Icon = ICON_MAP[notif.icon] || Bell;
  const colorClass = TYPE_COLORS[notif.type] || "bg-primary/10 text-primary";
  const link = buildDeepLink(notif);

  return (
    <div
      className={`flex gap-3 px-4 py-3 border-b border-border/30 last:border-0 transition-colors ${
        !notif.read ? "bg-primary/3" : ""
      } ${link ? "cursor-pointer hover:bg-accent/50" : ""}`}
      onClick={() => link && navigate(link)}
      role={link ? "button" : undefined}
      tabIndex={link ? 0 : undefined}
      onKeyDown={e => { if (link && (e.key === "Enter" || e.key === " ")) navigate(link); }}
      aria-label={notif.title}
    >
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${colorClass}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-medium leading-snug">{notif.title}</span>
          <div className="flex items-center gap-1.5 shrink-0">
            {!notif.read && <span className="w-2 h-2 bg-primary rounded-full" aria-label="Ungelesen" />}
            <span className="text-[10px] text-muted-foreground whitespace-nowrap">
              {formatRelative(notif.created_at)}
            </span>
          </div>
        </div>
        {notif.message && (
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">
            {notif.message}
          </p>
        )}
      </div>
    </div>
  );
});
