import { memo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PostHeader } from "./PostHeader";
import { PostActions } from "./PostActions";

export const PostCard = memo(function PostCard({ post: initialPost, token, userId }) {
  const navigate = useNavigate();
  const [post, setPost] = useState(initialPost);
  const [userReaction, setUserReaction] = useState(null);

  const handleReacted = (reaction, stats) => {
    setUserReaction(reaction);
    setPost(prev => ({ ...prev, stats: stats ?? prev.stats }));
  };

  const allTags = [...(post.specialty_tags || []), ...(post.topic_tags || [])];
  const preview = post.content ? post.content.slice(0, 200) + (post.content.length > 200 ? "…" : "") : "";

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
