import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

export function InfiniteScrollSentinel({ onVisible, loading }) {
  const ref = useRef(null);
  // Keep latest callback in a ref so the observer never needs to reconnect
  const onVisibleRef = useRef(onVisible);
  onVisibleRef.current = onVisible;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onVisibleRef.current(); },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []); // observer mounted once; callback stays current via ref

  return (
    <div ref={ref} className="flex justify-center py-6">
      {loading && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
    </div>
  );
}
