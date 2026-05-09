import { memo } from "react";
import { User } from "lucide-react";

const TYPE_LABELS = {
  discussion: "Diskussion",
  question: "Frage",
  case_study: "Fallstudie",
  resource: "Ressource",
};

const TYPE_COLORS = {
  discussion: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  question: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  case_study: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  resource: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

function formatRelative(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "gerade eben";
  if (mins < 60) return `vor ${mins} Min.`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `vor ${hrs} Std.`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `vor ${days} Tag${days > 1 ? "en" : ""}`;
  return new Date(isoStr).toLocaleDateString("de-AT", { day: "numeric", month: "short" });
}

export const PostHeader = memo(function PostHeader({ authorName, createdAt, type, tags = [] }) {
  const typeLabel = TYPE_LABELS[type] || type;
  const typeColor = TYPE_COLORS[type] || "bg-muted text-muted-foreground";

  return (
    <div className="flex items-start gap-2 flex-wrap">
      <div className="w-7 h-7 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
        <User className="w-3.5 h-3.5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold truncate">{authorName}</span>
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md ${typeColor}`}>
            {typeLabel}
          </span>
          <span className="text-xs text-muted-foreground ml-auto shrink-0">{formatRelative(createdAt)}</span>
        </div>
        {tags.length > 0 && (
          <div className="flex gap-1 flex-wrap mt-1">
            {tags.slice(0, 4).map(tag => (
              <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});
