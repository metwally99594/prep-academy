import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { AlertCircle, MessageSquare } from "lucide-react";
import { useFeed } from "@/hooks/useFeed";
import { useCommunityFilters } from "@/hooks/useCommunityFilters";
import { PostCard } from "@/components/community/PostCard";
import { PostCardSkeleton } from "@/components/community/PostCardSkeleton";
import { InfiniteScrollSentinel } from "@/components/community/InfiniteScrollSentinel";
import { CommunityHeader } from "@/components/community/CommunityHeader";
import { FeedFilterBar } from "@/components/community/FeedFilterBar";
import { NewPostModal } from "@/components/community/NewPostModal";
import { EmptyState } from "@/components/ui/empty-state";

export default function CommunityPage() {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const [showNewPost, setShowNewPost] = useState(false);

  const { filters, setFilter, searchInput, handleSearchInput, clearFilters, hasActiveFilters } =
    useCommunityFilters();

  const { posts, setPosts, loading, loadingMore, hasMore, error, load, loadMore } = useFeed(token, filters);

  // Reload when any filter changes
  const filterKey = [filters.sort, filters.specialty, filters.topic, filters.type, filters.search].join("|");
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  const handlePostDeleted = useCallback((postId) => {
    setPosts(prev => prev.filter(p => p.id !== postId));
  }, []);

  const handleLoadMore = useCallback(() => { loadMore(); }, [loadMore]);

  const handlePostCreated = useCallback((postId, status) => {
    setShowNewPost(false);
    load();
    if (status === "published") navigate(`/community/${postId}`);
  }, [navigate, load]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
      <CommunityHeader user={user} onNewPost={() => setShowNewPost(true)} />

      <FeedFilterBar
        filters={filters}
        setFilter={setFilter}
        searchInput={searchInput}
        onSearchInput={handleSearchInput}
        hasActiveFilters={hasActiveFilters}
        onClear={clearFilters}
      />

      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => load()}
            className="text-xs font-medium text-destructive underline hover:no-underline shrink-0"
          >
            Erneut versuchen
          </button>
        </div>
      )}

      <div className="space-y-3">
        {/* Initial load: show skeletons */}
        {loading && posts.length === 0 ? (
          Array.from({ length: 5 }).map((_, i) => <PostCardSkeleton key={i} />)
        ) : posts.length === 0 && !loading ? (
          <EmptyState
            icon={MessageSquare}
            title={hasActiveFilters ? "Keine Beiträge für diese Filter" : "Noch keine Beiträge"}
            description={hasActiveFilters ? "Versuchen Sie andere Filter oder erstellen Sie einen neuen Beitrag." : "Seien Sie der Erste, der einen Beitrag erstellt!"}
            action={hasActiveFilters ? (
              <button onClick={clearFilters} className="text-xs text-primary hover:underline font-medium">
                Filter zurücksetzen
              </button>
            ) : undefined}
          />
        ) : (
          // Keep old posts visible (faded) while filter changes load
          <div className={loading ? "opacity-60 pointer-events-none transition-opacity duration-150" : "transition-opacity duration-150"}>
            {posts.map(post => (
              <div key={post.id} className="mb-3">
                <PostCard post={post} token={token} userId={user?.id} onDelete={handlePostDeleted} />
              </div>
            ))}
          </div>
        )}
      </div>

      {!loading && hasMore && (
        <InfiniteScrollSentinel onVisible={handleLoadMore} loading={loadingMore} />
      )}

      {/* Always mounted — preserves draft across accidental close */}
      <NewPostModal
        open={showNewPost}
        onClose={() => setShowNewPost(false)}
        onCreated={handlePostCreated}
      />
    </div>
  );
}
