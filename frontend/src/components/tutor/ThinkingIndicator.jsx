import { Skeleton } from "@/components/ui/skeleton";

const DOT_STYLES = [
  { animationDelay: '0ms' },
  { animationDelay: '200ms' },
  { animationDelay: '400ms' },
];

export default function ThinkingIndicator({ modelName }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-sm text-white/40">
        <span className="inline-flex gap-1">
          {DOT_STYLES.map((style, i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulse"
              style={style}
            />
          ))}
        </span>
        {modelName}
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-full bg-white/5" />
        <Skeleton className="h-3 w-3/4 bg-white/5" />
        <Skeleton className="h-3 w-1/2 bg-white/5" />
      </div>
    </div>
  );
}
