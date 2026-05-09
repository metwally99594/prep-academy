import { memo, useState, useCallback } from "react";
import { User, CornerDownRight, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

function formatRelative(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "gerade eben";
  if (mins < 60) return `vor ${mins} Min.`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `vor ${hrs} Std.`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `vor ${days} Tag${days !== 1 ? "en" : ""}`;
  return new Date(isoStr).toLocaleDateString("de-AT", { day: "numeric", month: "short" });
}

export const CommentItem = memo(function CommentItem({
  comment,
  userId,
  onSubmitReply,
  depth = 0,
}) {
  const [showReply, setShowReply] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isMe = comment.author_id === userId;
  const isOptimistic = !!comment._optimistic;

  const handleReply = useCallback(async () => {
    if (!replyText.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmitReply(comment.id, replyText.trim());
      setReplyText("");
      setShowReply(false);
    } finally {
      setSubmitting(false);
    }
  }, [replyText, submitting, comment.id, onSubmitReply]);

  const handleReplyKeyDown = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleReply();
    }
    if (e.key === "Escape") {
      setShowReply(false);
      setReplyText("");
    }
  }, [handleReply]);

  return (
    <div
      className={[
        depth > 0 ? "ml-8 pl-4 border-l-2 border-border/30" : "",
        isOptimistic ? "opacity-60" : "",
      ].join(" ")}
    >
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-3.5 h-3.5 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <span className="text-xs font-semibold">{comment.author_name}</span>
            {isMe && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-semibold">
                Du
              </span>
            )}
            <span className="text-[10px] text-muted-foreground">
              {formatRelative(comment.created_at)}
            </span>
            {isOptimistic && (
              <Loader2 className="w-2.5 h-2.5 animate-spin text-muted-foreground" />
            )}
          </div>
          <div className="rounded-xl rounded-tl-sm bg-muted/60 px-3 py-2">
            <MarkdownRenderer content={comment.content} />
          </div>
          {/* Reply button only on top-level comments, not on optimistic ones */}
          {depth === 0 && !isOptimistic && (
            <button
              onClick={() => setShowReply(v => !v)}
              className={`mt-1.5 text-[10px] flex items-center gap-1 transition-colors ${
                showReply ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <CornerDownRight className="w-3 h-3" />
              {showReply ? "Abbrechen" : "Antworten"}
            </button>
          )}
        </div>
      </div>

      {/* Inline reply editor */}
      {showReply && (
        <div
          className="ml-9 mt-2 flex gap-2 items-end"
          style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
        >
          <textarea
            className="flex-1 rounded-xl border bg-background/50 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder={`Antwort an ${comment.author_name}…`}
            value={replyText}
            onChange={e => setReplyText(e.target.value)}
            onKeyDown={handleReplyKeyDown}
            maxLength={2000}
            rows={2}
            autoFocus
          />
          <Button
            size="icon"
            className="shrink-0 w-9 h-9"
            onClick={handleReply}
            disabled={submitting || !replyText.trim()}
            aria-label="Antwort senden"
          >
            {submitting
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Send className="w-3.5 h-3.5" />
            }
          </Button>
        </div>
      )}
    </div>
  );
});
