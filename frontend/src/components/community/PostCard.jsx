import { memo, useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PostHeader } from "./PostHeader";
import { PostActions } from "./PostActions";
import { MoreHorizontal, Pencil, Trash2, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";
import { toast } from "sonner";
import { TRANSITIONS } from "@/lib/theme";

function stripMarkdown(text = "") {
  return text
    .replace(/#{1,6}\s+/g, "")
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/`{1,3}[^`]*`{1,3}/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^>\s+/gm, "")
    .replace(/[-*+]\s/g, "")
    .replace(/\n+/g, " ")
    .trim();
}

function MediaPreview({ media }) {
  if (media.length === 0) return null;
  const first = media[0];
  return (
    <div className="relative w-full mt-1.5 rounded-xl overflow-hidden border border-border/30 bg-muted/10 shadow-sm" style={{ aspectRatio: "16/9" }}>
      {first.media_type === "video" ? (
        <video
          src={first.data_uri}
          className="absolute inset-0 w-full h-full object-cover"
          controls
          preload="metadata"
        />
      ) : (
        <img
          src={first.data_uri}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
          loading="lazy"
        />
      )}
    </div>
  );
}

export const PostCard = memo(function PostCard({ post: initialPost, token, userId, onDelete }) {
  const navigate = useNavigate();
  const [post, setPost] = useState(initialPost);
  const [userReaction, setUserReaction] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleReacted = (reaction, stats) => {
    setUserReaction(reaction);
    setPost(prev => ({ ...prev, stats: stats ?? prev.stats }));
  };

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await apiClient.delete(`/community/posts/${post.id}`, { timeout: 12000 });
      toast.success("Beitrag gelöscht");
      onDelete?.(post.id);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Löschen");
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
      setMenuOpen(false);
    }
  }, [post.id, onDelete]);

  const isAuthor = userId && post.author_id === userId;
  const allTags = [...(post.specialty_tags || []), ...(post.topic_tags || [])];
  const rawPreview = stripMarkdown(post.content || "");
  const preview = rawPreview.slice(0, 200) + (rawPreview.length > 200 ? "…" : "");
  const postMedia = post.media || [];

  return (
    <article
      className="rounded-xl border border-border/40 bg-card shadow-sm hover:shadow-md hover:border-border/60 transition-all duration-200 cursor-pointer group"
      onClick={() => navigate(`/community/${post.id}`)}
    >
      <div className="p-4 sm:p-5 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <PostHeader
            authorName={post.author_name}
            createdAt={post.created_at}
            type={post.type}
            tags={allTags}
          />
          {isAuthor && (
            <div className="relative shrink-0" ref={menuRef}>
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(v => !v); }}
                className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground hover:text-foreground transition-colors duration-150 opacity-0 group-hover:opacity-100 focus:opacity-100"
                aria-label="Mehr"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-8 z-20 w-40 rounded-xl border border-border/50 bg-card shadow-xl overflow-hidden animate-fade-in">
                  {confirmDelete ? (
                    <div className="p-3 space-y-2">
                      <p className="text-xs font-medium">Wirklich löschen?</p>
                      <div className="flex gap-1.5">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                          disabled={deleting}
                          className="flex-1 px-2 py-1.5 text-[10px] rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 font-medium"
                        >
                          {deleting ? <Loader2 className="w-3 h-3 animate-spin mx-auto" /> : "Löschen"}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setConfirmDelete(false); }}
                          className="flex-1 px-2 py-1.5 text-[10px] rounded-lg bg-muted hover:bg-accent/50 font-medium"
                        >
                          Abbrechen
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); navigate(`/community/${post.id}`); setMenuOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs hover:bg-accent/50 transition-colors text-left font-medium"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                        Bearbeiten
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setConfirmDelete(true); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs hover:bg-accent/50 transition-colors text-left text-destructive font-medium"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Löschen
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-1">
          <h2 className="text-sm font-semibold leading-snug group-hover:text-primary transition-colors duration-150 line-clamp-2">
            {post.title}
          </h2>
          {preview && (
            <p className="text-xs text-muted-foreground/80 mt-0.5 line-clamp-2 leading-relaxed">
              {preview}
            </p>
          )}
        </div>

        <MediaPreview media={postMedia} />

        <PostActions
          token={token}
          post={post}
          userReaction={userReaction}
          onReacted={handleReacted}
          onCommentClick={(e) => {
            e?.stopPropagation?.();
            navigate(`/community/${post.id}`);
          }}
          compact
        />
      </div>
    </article>
  );
});
