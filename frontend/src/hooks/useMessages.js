import { useState, useEffect, useCallback, useMemo } from "react";
import apiClient from "@/lib/api";

export function useMessages(token, convId, userId) {
  const [messages, setMessages] = useState([]);
  const [conv, setConv] = useState(null);
  const [loading, setLoading] = useState(false);

  const otherId = useMemo(
    () => (conv?.participants || []).find(id => id !== userId) ?? null,
    [conv, userId],
  );

  const fetch = useCallback(async (quiet = false) => {
    if (!token || !convId) return;
    if (!quiet) setLoading(true);
    try {
      const res = await apiClient.get(
        `/messaging/conversations/${convId}`,
        { timeout: 10000 },
      );
      setMessages(res.data.messages || []);
      if (res.data.conversation) setConv(res.data.conversation);
    } catch { } finally {
      setLoading(false);
    }
  }, [token, convId]);

  useEffect(() => {
    if (!convId) { setMessages([]); setConv(null); setLoading(false); return; }
    setLoading(true);
    setMessages([]);
    setConv(null);
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [convId]);


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
      const res = await apiClient.post(
        "/messaging/send",
        { recipient_id: otherId, content: text, conversation_id: convId, attachments },
        { timeout: 20000 },
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
  }, [token, convId, userId, otherId]);

  return { messages, conv, loading, fetch, sendMessage, otherId };
}
