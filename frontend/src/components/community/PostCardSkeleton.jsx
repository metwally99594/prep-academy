export function PostCardSkeleton() {
  return (
    <div className="rounded-2xl border border-border/40 bg-card p-5 space-y-3 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-muted shrink-0" />
        <div className="h-3 bg-muted rounded w-28" />
        <div className="h-3 bg-muted rounded w-16 ml-auto" />
      </div>
      <div className="h-4 bg-muted rounded w-3/4" />
      <div className="space-y-1.5">
        <div className="h-3 bg-muted rounded w-full" />
        <div className="h-3 bg-muted rounded w-5/6" />
      </div>
      <div className="flex gap-2 pt-1">
        <div className="h-6 bg-muted rounded w-16" />
        <div className="h-6 bg-muted rounded w-16" />
        <div className="h-6 bg-muted rounded w-20" />
      </div>
    </div>
  );
}
