import { memo, useState } from "react";
import { MessageCircle } from "lucide-react";
import { ReactionButton } from "./ReactionButton";
import { useReaction } from "@/hooks/useReaction";

export const PostActions = memo(function PostActions({
  token,
  post,
  userReaction,
  onReacted,
  onCommentClick,
  compact = false,
}) {
  const { react } = useReaction(token);
  const [pending, setPending] = useState(false);

  const stats = post.stats || {};
  const commentCount = stats.comment_count ?? 0;

  const handleReact = async (reaction) => {
    if (pending) return;
    setPending(true);

    let optimisticReaction = userReaction;
    let optimisticStats = { ...stats };

    // Compute optimistic delta
    const isSame = userReaction === reaction;
    if (isSame) {
      // toggle off
      optimisticReaction = null;
      optimisticStats[`${reaction}_count`] = Math.max(0, (stats[`${reaction}_count`] ?? 0) - 1);
    } else {
      // switch or new
      if (userReaction) {
        optimisticStats[`${userReaction}_count`] = Math.max(0, (stats[`${userReaction}_count`] ?? 0) - 1);
      }
      optimisticReaction = reaction;
      optimisticStats[`${reaction}_count`] = (stats[`${reaction}_count`] ?? 0) + 1;
    }

    onReacted?.(optimisticReaction, optimisticStats);

    try {
      await react({
        targetType: "post",
        targetId: post.id,
        reaction,
        currentReaction: userReaction,
        onCommit: (finalReaction, finalStats) => {
          onReacted?.(finalReaction, finalStats ?? optimisticStats);
        },
        onRollback: () => {
          onReacted?.(userReaction, stats);
        },
      });
    } finally {
      setPending(false);
    }
  };

  return (
    <div className={`flex items-center gap-2 ${compact ? "" : "flex-wrap"}`}>
      <ReactionButton
        type="upvote"
        count={stats.upvote_count ?? 0}
        active={userReaction === "upvote"}
        onClick={() => handleReact("upvote")}
        disabled={pending}
      />
      <ReactionButton
        type="downvote"
        count={stats.downvote_count ?? 0}
        active={userReaction === "downvote"}
        onClick={() => handleReact("downvote")}
        disabled={pending}
      />
      {onCommentClick && (
        <button
          onClick={onCommentClick}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Kommentare anzeigen"
        >
          <MessageCircle className="w-3.5 h-3.5" />
          <span>{commentCount}</span>
        </button>
      )}
    </div>
  );
});
