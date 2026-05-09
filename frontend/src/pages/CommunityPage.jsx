import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Users, AlertCircle } from "lucide-react";
import { useFeed } from "@/hooks/useFeed";
import { PostCard } from "@/components/community/PostCard";
import { PostCardSkeleton } from "@/components/community/PostCardSkeleton";
import { InfiniteScrollSentinel } from "@/components/community/InfiniteScrollSentinel";

const SORT_OPTIONS = [
  { value: "recent", label: "Neueste" },
  { value: "top", label: "Top" },
  { value: "discussed", label: "Meist diskutiert" },
  { value: "trending", label: "Trending" },
];

export default function CommunityPage() {
  const { token, user } = useAuth();
  const [sort, setSort] = useState("recent");

  const { posts, loading, loadingMore, hasMore, error, load, loadMore, updatePost } = useFeed(
    token,
    { sort },
  );

  // Reload when sort changes
  useEffect(() => {
    load();
  }, [load, sort]);

  const handleLoadMore = useCallback(() => {
    loadMore();
  }, [loadMore]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
            <Users className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">Community</h1>
            <p className="text-xs text-muted-foreground">Medizinische Diskussionen</p>
          </div>
        </div>

        {/* Sort tabs */}
        <div className="flex gap-1 bg-muted/50 rounded-xl p-1">
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setSort(opt.value)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                sort === opt.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => <PostCardSkeleton key={i} />)
        ) : posts.length === 0 ? (
          <div className="text-center py-16">
            <Users className="w-12 h-12 mx-auto mb-3 text-muted-foreground/20" />
            <p className="text-sm text-muted-foreground">Noch keine Beiträge</p>
          </div>
        ) : (
          posts.map(post => (
            <PostCard
              key={post.id}
              post={post}
              token={token}
              userId={user?.id}
            />
          ))
        )}
      </div>

      {!loading && hasMore && (
        <InfiniteScrollSentinel onVisible={handleLoadMore} loading={loadingMore} />
      )}
    </div>
  );
}
