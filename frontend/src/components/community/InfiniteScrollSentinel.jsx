import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

export function InfiniteScrollSentinel({ onVisible, loading }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onVisible(); },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [onVisible]);

  return (
    <div ref={ref} className="flex justify-center py-6">
      {loading && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
    </div>
  );
}
