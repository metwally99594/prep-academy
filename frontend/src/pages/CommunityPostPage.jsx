import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { ArrowLeft, AlertCircle, User, Loader2, Send } from "lucide-react";
import { toast } from "sonner";
import { usePost } from "@/hooks/usePost";
import { PostHeader } from "@/components/community/PostHeader";
import { PostActions } from "@/components/community/PostActions";
import { Button } from "@/components/ui/button";

function CommentBubble({ comment, userId }) {
  const isMe = comment.author_id === userId;
  return (
    <div className={`flex gap-3 ${isMe ? "flex-row-reverse" : ""}`}>
      <div className="w-7 h-7 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
        <User className="w-3.5 h-3.5 text-primary" />
      </div>
      <div className={`max-w-[80%] ${isMe ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold">{comment.author_name}</span>
          <span className="text-[10px] text-muted-foreground">
            {new Date(comment.created_at).toLocaleString("de-AT", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <div className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${isMe ? "bg-primary text-primary-foreground rounded-tr-sm" : "bg-muted rounded-tl-sm"}`}>
          {comment.content}
        </div>
      </div>
    </div>
  );
}

function CommentSkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="w-7 h-7 rounded-full bg-muted shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 bg-muted rounded w-24" />
        <div className="h-10 bg-muted rounded-2xl rounded-tl-sm w-3/4" />
      </div>
    </div>
  );
}

export default function CommunityPostPage() {
  const { postId } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const userId = user?.id;

  const { post, comments, userReaction, loading, error, addComment, applyReaction } = usePost(token, postId);

  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleReacted = useCallback((reaction, stats) => {
    applyReaction(reaction, stats);
  }, [applyReaction]);

  const handleSubmitComment = useCallback(async () => {
    if (!commentText.trim()) return;
    setSubmitting(true);
    try {
      await addComment(commentText.trim());
      setCommentText("");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Senden");
    } finally {
      setSubmitting(false);
    }
  }, [commentText, addComment]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 flex flex-col gap-4">
      {/* Back */}
      <button
        onClick={() => navigate("/community")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <ArrowLeft className="w-4 h-4" />
        Community
      </button>

      {/* Post */}
      {loading || !post ? (
        <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-4 animate-pulse">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-muted" />
            <div className="h-3 bg-muted rounded w-32" />
          </div>
          <div className="h-5 bg-muted rounded w-2/3" />
          <div className="space-y-2">
            <div className="h-3 bg-muted rounded w-full" />
            <div className="h-3 bg-muted rounded w-5/6" />
            <div className="h-3 bg-muted rounded w-4/6" />
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-4">
          <PostHeader
            authorName={post.author_name}
            createdAt={post.created_at}
            type={post.type}
            tags={[...(post.specialty_tags || []), ...(post.topic_tags || [])]}
          />
          <div>
            <h1 className="text-base font-bold leading-snug mb-2">{post.title}</h1>
            <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">{post.content}</p>
          </div>
          <PostActions
            token={token}
            post={post}
            userReaction={userReaction}
            onReacted={handleReacted}
          />
        </div>
      )}

      {/* Comments */}
      <div className="rounded-2xl border border-border/40 bg-card p-5">
        <h2 className="text-sm font-semibold mb-4">
          Kommentare{!loading && post ? ` (${post.stats?.comment_count ?? comments.length})` : ""}
        </h2>

        <div className="space-y-4 mb-5">
          {loading ? (
            <>
              <CommentSkeleton />
              <CommentSkeleton />
            </>
          ) : comments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Noch keine Kommentare — schreiben Sie den ersten!
            </p>
          ) : (
            comments.map(c => (
              <CommentBubble key={c.id} comment={c} userId={userId} />
            ))
          )}
        </div>

        {/* Comment input */}
        <div className="flex gap-2 items-end">
          <textarea
            className="flex-1 rounded-xl border bg-background/50 px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary min-h-[44px] max-h-32"
            placeholder="Kommentar schreiben…"
            value={commentText}
            onChange={e => setCommentText(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmitComment();
              }
            }}
            maxLength={2000}
            rows={1}
          />
          <Button
            size="icon"
            onClick={handleSubmitComment}
            disabled={submitting || !commentText.trim()}
            className="shrink-0 w-10 h-10"
            aria-label="Kommentar senden"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
