import { useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { ArrowLeft, AlertCircle } from "lucide-react";
import { usePost } from "@/hooks/usePost";
import { PostHeader } from "@/components/community/PostHeader";
import { PostActions } from "@/components/community/PostActions";
import { CommentSection } from "@/components/community/CommentSection";
import { AIInsightBlock } from "@/components/community/AIInsightBlock";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

function PostMedia({ media }) {
  if (!media || media.length === 0) return null;
  return (
    <div className="space-y-3">
      {media.map((m, i) => (
        <div key={m.id || i} className="relative w-full rounded-xl overflow-hidden border border-border/40 bg-muted/20" style={{ aspectRatio: m.media_type === "video" ? "16/9" : "4/3" }}>
          {m.media_type === "video" ? (
            <video
              src={m.data_uri}
              className="absolute inset-0 w-full h-full object-contain"
              controls
              preload="metadata"
            />
          ) : (
            <img
              src={m.data_uri}
              alt=""
              className="absolute inset-0 w-full h-full object-contain"
              loading="lazy"
            />
          )}
        </div>
      ))}
    </div>
  );
}

function PostSkeleton() {
  return (
    <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-4 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-muted shrink-0" />
        <div className="h-3 bg-muted rounded w-32" />
        <div className="h-3 bg-muted rounded w-16 ml-auto" />
      </div>
      <div className="h-5 bg-muted rounded w-3/4" />
      <div className="space-y-2">
        <div className="h-3 bg-muted rounded w-full" />
        <div className="h-3 bg-muted rounded w-5/6" />
        <div className="h-3 bg-muted rounded w-4/6" />
      </div>
      <div className="flex gap-2 pt-1">
        <div className="h-8 bg-muted rounded-xl w-16" />
        <div className="h-8 bg-muted rounded-xl w-16" />
        <div className="h-8 bg-muted rounded-xl w-20" />
      </div>
    </div>
  );
}

function CommentSectionSkeleton() {
  return (
    <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-4 animate-pulse">
      <div className="h-4 bg-muted rounded w-32" />
      {[1, 2].map(i => (
        <div key={i} className="flex gap-2.5">
          <div className="w-7 h-7 rounded-full bg-muted shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 bg-muted rounded w-24" />
            <div className="h-10 bg-muted rounded-xl rounded-tl-sm w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CommunityPostPage() {
  const { postId } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuth();

  const { post, comments, userReaction, loading, error, applyReaction } = usePost(token, postId);

  const handleReacted = useCallback((reaction, stats) => {
    applyReaction(reaction, stats);
  }, [applyReaction]);

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
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-4" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <ArrowLeft className="w-4 h-4" />
        Zurück
      </button>

      {/* Post */}
      {loading || !post ? (
        <PostSkeleton />
      ) : (
        <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-4">
          <PostHeader
            authorName={post.author_name}
            createdAt={post.created_at}
            type={post.type}
            tags={[...(post.specialty_tags || []), ...(post.topic_tags || [])]}
          />
          <div>
            <h1 className="text-base font-bold leading-snug mb-3">{post.title}</h1>
            <MarkdownRenderer content={post.content} />
          </div>
          <PostMedia media={post.media} />
          <PostActions
            token={token}
            post={post}
            userReaction={userReaction}
            onReacted={handleReacted}
          />
        </div>
      )}

      {/* AI Insight Block — only when post is loaded */}
      {!loading && post && <AIInsightBlock post={post} />}

      {/* Comments */}
      {loading ? (
        <CommentSectionSkeleton />
      ) : (
        <CommentSection
          postId={postId}
          token={token}
          userId={user?.id}
          userName={user?.name}
          initialComments={comments}
          commentCount={post?.stats?.comment_count ?? 0}
        />
      )}
    </div>
  );
}
