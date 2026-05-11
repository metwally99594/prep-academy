import { memo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PostHeader } from "./PostHeader";
import { PostActions } from "./PostActions";

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
  if (first.media_type === "video") {
    return (
      <video
        src={first.data_uri}
        className="w-full max-h-48 rounded-xl object-cover border border-border/40 mt-1"
        controls
        preload="metadata"
      />
    );
  }
  return (
    <img
      src={first.data_uri}
      alt=""
      className="w-full max-h-48 rounded-xl object-cover border border-border/40 mt-1"
      loading="lazy"
    />
  );
}

export const PostCard = memo(function PostCard({ post: initialPost, token, userId }) {
  const navigate = useNavigate();
  const [post, setPost] = useState(initialPost);
  const [userReaction, setUserReaction] = useState(null);

  const handleReacted = (reaction, stats) => {
    setUserReaction(reaction);
    setPost(prev => ({ ...prev, stats: stats ?? prev.stats }));
  };

  const allTags = [...(post.specialty_tags || []), ...(post.topic_tags || [])];
  const rawPreview = stripMarkdown(post.content || "");
  const preview = rawPreview.slice(0, 200) + (rawPreview.length > 200 ? "…" : "");
  const postMedia = post.media || [];

  return (
    <article
      className="rounded-2xl border border-border/40 bg-card hover:border-border/70 transition-colors cursor-pointer group"
      onClick={() => navigate(`/community/${post.id}`)}
    >
      <div className="p-5 space-y-3">
        <PostHeader
          authorName={post.author_name}
          createdAt={post.created_at}
          type={post.type}
          tags={allTags}
        />

        <div>
          <h2 className="text-sm font-semibold leading-snug group-hover:text-primary transition-colors line-clamp-2">
            {post.title}
          </h2>
          {preview && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
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
