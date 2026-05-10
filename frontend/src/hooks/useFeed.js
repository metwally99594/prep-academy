import { useState, useCallback, useRef } from "react";
import apiClient from "@/lib/api";

const PAGE_SIZE = 20;

export function useFeed(token, filters = {}) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);
  const cursorRef = useRef(null);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const buildParams = useCallback((cursor = null) => {
    const f = filtersRef.current;
    const p = new URLSearchParams();
    p.set("page_size", PAGE_SIZE);
    p.set("sort", f.sort || "recent");
    if (f.specialty) p.set("specialty", f.specialty);
    if (f.topic) p.set("topic", f.topic);
    if (f.type) p.set("type", f.type);
    if (f.search) p.set("search", f.search);
    if (cursor) p.set("cursor", cursor);
    else p.set("page", 1);
    return p.toString();
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cursorRef.current = null;
    try {
      const res = await apiClient.get(
        `/community/feed?${buildParams()}`,
        { timeout: 12000 },
      );
      const data = res.data;
      setPosts(data.posts || []);
      cursorRef.current = data.next_cursor || null;
      setHasMore(!!data.next_cursor);
    } catch (e) {
      setError(e.response?.data?.detail || "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, [token, buildParams]);

  const loadMore = useCallback(async () => {
    if (!token || loadingMore || !hasMore || !cursorRef.current) return;
    setLoadingMore(true);
    try {
      const res = await apiClient.get(
        `/community/feed?${buildParams(cursorRef.current)}`,
        { timeout: 12000 },
      );
      const data = res.data;
      setPosts(prev => [...prev, ...(data.posts || [])]);
      cursorRef.current = data.next_cursor || null;
      setHasMore(!!data.next_cursor);
    } catch {
    } finally {
      setLoadingMore(false);
    }
  }, [token, loadingMore, hasMore, buildParams]);

  const updatePost = useCallback((postId, updater) => {
    setPosts(prev => prev.map(p => p.id === postId ? updater(p) : p));
  }, []);

  return { posts, loading, loadingMore, hasMore, error, load, loadMore, updatePost };
}
