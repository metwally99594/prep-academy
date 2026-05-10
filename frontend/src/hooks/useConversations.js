import { useState, useEffect, useCallback, useMemo } from "react";
import apiClient from "@/lib/api";

export function useConversations(token) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const fetch = useCallback(async (quiet = false) => {
    if (!token) return;
    if (!quiet) setLoading(true);
    try {
      const res = await apiClient.get("/messaging/conversations", { timeout: 10000 });
      setConversations(res.data.conversations || []);
    } catch { } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetch(); }, [fetch]);

  useEffect(() => {
    const id = setInterval(() => { if (!document.hidden) fetch(true); }, 30000);
    return () => clearInterval(id);
  }, [fetch]);

  const markRead = useCallback(async (convId) => {
    setConversations(prev => prev.map(c => c.id === convId ? { ...c, unread_count: 0 } : c));
    try {
      await apiClient.post(`/messaging/conversations/${convId}/read`, null, { timeout: 8000 });
    } catch { }
  }, []);

  const filtered = useMemo(() => {
    return conversations.filter(c => {
      if (filter === "unread" && !c.unread_count) return false;
      if (search) {
        const q = search.toLowerCase();
        const info = c.participants_info || {};
        const names = Object.values(info).map(u => `${u.name || ""} ${u.email || ""}`).join(" ").toLowerCase();
        const preview = (c.last_message_preview || "").toLowerCase();
        return names.includes(q) || preview.includes(q);
      }
      return true;
    });
  }, [conversations, filter, search]);

  const totalUnread = useMemo(
    () => conversations.reduce((s, c) => s + (c.unread_count || 0), 0),
    [conversations],
  );

  return {
    conversations: filtered,
    allConversations: conversations,
    loading,
    fetch,
    markRead,
    filter,
    setFilter,
    search,
    setSearch,
    totalUnread,
    setConversations,
  };
}
