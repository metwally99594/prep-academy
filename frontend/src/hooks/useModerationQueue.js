import { useState, useCallback, useRef } from "react";
import apiClient from "@/lib/api";
import { toast } from "sonner";

export function useModerationQueue(_token) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState(null);
  const cursorRef = useRef(null);

  const buildQuery = (reviewed, severity) => {
    const p = new URLSearchParams({ page_size: 20 });
    p.set("reviewed", String(reviewed));
    if (severity) p.set("severity", severity);
    return p.toString();
  };

  const load = useCallback(async (reviewed = false, severity = "") => {
    setLoading(true);
    setError(null);
    cursorRef.current = null;
    try {
      const res = await apiClient.get(
        `/community/moderation/queue?${buildQuery(reviewed, severity)}`,
        { timeout: 12000 },
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

  const loadMore = useCallback(async (reviewed, severity) => {
    if (!cursorRef.current || loadingMore) return;
    setLoadingMore(true);
    try {
      const p = new URLSearchParams({ page_size: 20, cursor: cursorRef.current });
      p.set("reviewed", String(reviewed));
      if (severity) p.set("severity", severity);
      const res = await apiClient.get(
        `/community/moderation/queue?${p}`,
        { timeout: 12000 },
      );
      setItems(prev => [...prev, ...(res.data.items || [])]);
      cursorRef.current = res.data.next_cursor || null;
      setHasMore(!!res.data.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore]);

  const takeAction = useCallback(async (item, action, note = null) => {
    setItems(prev => prev.filter(i => i.id !== item.id));
    try {
      await apiClient.post(
        "/community/moderation/action",
        {
          target_type: item.target_type,
          target_id: item.target_id,
          action,
          ...(note ? { reason: note } : {}),
        },
        { timeout: 10000 },
      );
    } catch (e) {
      setItems(prev => [item, ...prev]);
      toast.error(e.response?.data?.detail || "Aktion fehlgeschlagen");
    }
  }, []);

  return { items, loading, loadingMore, hasMore, error, load, loadMore, takeAction };
}
