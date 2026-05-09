import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/App";

export function useConversations(token) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // "all" | "unread"
  const [search, setSearch] = useState("");
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const fetch = useCallback(async (quiet = false) => {
    if (!token) return;
    if (!quiet) setLoading(true);
    try {
      const res = await axios.get(`${API}/messaging/conversations`, { headers, timeout: 10000 });
      setConversations(res.data.conversations || []);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, [token, headers]);

  useEffect(() => { fetch(); }, [fetch]);

  useEffect(() => {
    const id = setInterval(() => { if (!document.hidden) fetch(true); }, 30000);
    return () => clearInterval(id);
  }, [fetch]);

  const markRead = useCallback(async (convId) => {
    setConversations(prev => prev.map(c => c.id === convId ? { ...c, unread_count: 0 } : c));
    try {
      await axios.post(`${API}/messaging/conversations/${convId}/read`, null, { headers, timeout: 8000 });
    } catch { /* silent */ }
  }, [headers]);

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
