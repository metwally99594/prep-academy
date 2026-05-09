import { memo } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";

export const ReactionButton = memo(function ReactionButton({
  type,
  count,
  active,
  onClick,
  disabled,
}) {
  const isUp = type === "upvote";
  const Icon = isUp ? ThumbsUp : ThumbsDown;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-colors
        ${active
          ? isUp
            ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
            : "bg-rose-500/15 text-rose-600 dark:text-rose-400"
          : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
        } disabled:opacity-40 disabled:cursor-not-allowed`}
      aria-pressed={active}
      aria-label={isUp ? "Upvote" : "Downvote"}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{count ?? 0}</span>
    </button>
  );
});
