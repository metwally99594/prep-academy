import { useState, useCallback, useRef } from "react";
import apiClient from "@/lib/api";

export function useAuditLog(_token) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState(null);
  const cursorRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    cursorRef.current = null;
    try {
      const res = await apiClient.get(
        "/community/moderation/audit?page_size=20",
        { timeout: 45000 },
      );
      setItems(res.data.items || []);
      cursorRef.current = res.data.next_cursor || null;
      setHasMore(!!res.data.next_cursor);
    } catch (e) {
      setError(e.response?.data?.detail || "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (!cursorRef.current || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await apiClient.get(
        `/community/moderation/audit?page_size=20&cursor=${encodeURIComponent(cursorRef.current)}`,
        { timeout: 12000 },
      );
      setItems(prev => [...prev, ...(res.data.items || [])]);
      cursorRef.current = res.data.next_cursor || null;
      setHasMore(!!res.data.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore]);

  return { items, loading, loadingMore, hasMore, error, load, loadMore };
}
