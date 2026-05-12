import { useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { ArrowLeft, AlertCircle, Pencil, Trash2, Check, X, Loader2 } from "lucide-react";
import { usePost } from "@/hooks/usePost";
import { PostHeader } from "@/components/community/PostHeader";
import { PostActions } from "@/components/community/PostActions";
import { CommentSection } from "@/components/community/CommentSection";
import { AIInsightBlock } from "@/components/community/AIInsightBlock";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { Button } from "@/components/ui/button";

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

  const { post, comments, userReaction, loading, error, load, applyReaction, updatePost, deletePost } = usePost(token, postId);

  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleReacted = useCallback((reaction, stats) => {
    applyReaction(reaction, stats);
  }, [applyReaction]);

  const handleEditStart = useCallback(() => {
    if (!post) return;
    setEditTitle(post.title || "");
    setEditContent(post.content || "");
    setEditing(true);
  }, [post]);

  const handleEditCancel = useCallback(() => {
    setEditing(false);
  }, []);

  const handleEditSave = useCallback(async () => {
    if (!editTitle.trim() || !editContent.trim() || editSubmitting) return;
    setEditSubmitting(true);
    try {
      await updatePost({ title: editTitle.trim(), content: editContent.trim() });
      setEditing(false);
    } catch (e) {
      // error toast handled in updatePost
    } finally {
      setEditSubmitting(false);
    }
  }, [editTitle, editContent, editSubmitting, updatePost]);

  const handleDeleteConfirm = useCallback(async () => {
    setDeleting(true);
    try {
      await deletePost();
      navigate("/community");
    } catch {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }, [deletePost, navigate]);

  const isAuthor = post && user && post.author_id === user.id;

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => load()}
            className="text-xs font-medium text-destructive underline hover:no-underline shrink-0"
          >
            Erneut versuchen
          </button>
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
          <div className="flex items-start justify-between gap-2">
            <PostHeader
              authorName={post.author_name}
              createdAt={post.created_at}
              type={post.type}
              tags={[...(post.specialty_tags || []), ...(post.topic_tags || [])]}
            />
            {isAuthor && !editing && (
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={handleEditStart}
                  className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                  aria-label="Beitrag bearbeiten"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-destructive transition-colors"
                  aria-label="Beitrag löschen"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {editing ? (
            <div className="space-y-3">
              <input
                type="text"
                className="w-full rounded-xl border bg-background/50 px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                value={editTitle}
                onChange={e => setEditTitle(e.target.value)}
                autoFocus
              />
              <textarea
                className="w-full rounded-xl border bg-background/50 px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                rows={6}
              />
              <div className="flex gap-2 justify-end">
                <Button size="sm" variant="ghost" onClick={handleEditCancel} disabled={editSubmitting}>
                  <X className="w-3.5 h-3.5 mr-1" />
                  Abbrechen
                </Button>
                <Button size="sm" onClick={handleEditSave} disabled={editSubmitting || !editTitle.trim() || !editContent.trim()}>
                  {editSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Check className="w-3.5 h-3.5 mr-1" />}
                  Speichern
                </Button>
              </div>
            </div>
          ) : (
            <>
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
            </>
          )}
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && !editing && (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 space-y-3">
          <p className="text-sm font-semibold">Beitrag endgültig löschen?</p>
          <p className="text-xs text-muted-foreground">Diese Aktion kann nicht rückgängig gemacht werden.</p>
          <div className="flex gap-2">
            <Button variant="destructive" size="sm" onClick={handleDeleteConfirm} disabled={deleting}>
              {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Trash2 className="w-3.5 h-3.5 mr-1" />}
              Löschen
            </Button>
            <Button variant="outline" size="sm" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Abbrechen
            </Button>
          </div>
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
