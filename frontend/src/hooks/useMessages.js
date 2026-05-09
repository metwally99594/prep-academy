import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/App";

export function useMessages(token, convId, userId) {
  const [messages, setMessages] = useState([]);
  const [conv, setConv] = useState(null);
  const [loading, setLoading] = useState(false);
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const otherId = useMemo(
    () => (conv?.participants || []).find(id => id !== userId) ?? null,
    [conv, userId],
  );

  const fetch = useCallback(async (quiet = false) => {
    if (!token || !convId) return;
    if (!quiet) setLoading(true);
    try {
      const res = await axios.get(
        `${API}/messaging/conversations/${convId}`,
        { headers, timeout: 10000 },
      );
      setMessages(res.data.messages || []);
      if (res.data.conversation) setConv(res.data.conversation);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, [token, convId, headers]);

  // Reset + initial fetch when conversation changes
  useEffect(() => {
    if (!convId) { setMessages([]); setConv(null); setLoading(false); return; }
    setLoading(true);
    setMessages([]);
    setConv(null);
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [convId]);

  // 4s polling while a conversation is open
  useEffect(() => {
    if (!convId) return;
    const id = setInterval(() => { if (!document.hidden) fetch(true); }, 4000);
    return () => clearInterval(id);
  }, [fetch, convId]);

  const sendMessage = useCallback(async (text, attachments = []) => {
    if (!otherId) throw new Error("Kein Empfänger gefunden");
    const now = new Date().toISOString();
    const optimistic = {
      id: `opt-${Date.now()}`,
      conversation_id: convId,
      sender_id: userId,
      content: text,
      attachments,
      created_at: now,
      read_by: [userId],
      is_system_message: false,
      _optimistic: true,
    };
    setMessages(prev => [...prev, optimistic]);
    try {
      const res = await axios.post(
        `${API}/messaging/send`,
        { recipient_id: otherId, content: text, conversation_id: convId, attachments },
        { headers, timeout: 20000 },
      );
      setMessages(prev => prev.map(m =>
        m.id === optimistic.id
          ? { ...optimistic, id: res.data.message_id, created_at: res.data.created_at, _optimistic: false }
          : m,
      ));
      return res.data;
    } catch (e) {
      setMessages(prev => prev.filter(m => m.id !== optimistic.id));
      throw e;
    }
  }, [token, convId, userId, otherId, headers]);

  return { messages, conv, loading, fetch, sendMessage, otherId };
}
