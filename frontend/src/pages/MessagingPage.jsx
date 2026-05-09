import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import {
  MessageSquare, Send, Plus, Search, Loader2, ArrowLeft,
  User, CheckCheck, AlertCircle, X,
} from "lucide-react";
import { toast } from "sonner";

// ─── Time helpers ────────────────────────────────────────────────────────────

function fmtConvTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays < 7) return d.toLocaleDateString("de-AT", { weekday: "short" });
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" });
}

function fmtMsgTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

// ─── New Conversation modal (admin only) ─────────────────────────────────────

function NewConvModal({ token, onClose, onCreated }) {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const search = useCallback(async (q) => {
    setQuery(q);
    if (!q) { setUsers([]); return; }
    setSearching(true);
    try {
      const res = await axios.get(
        `${API}/messaging/admin/users?q=${encodeURIComponent(q)}`,
        { headers: { Authorization: `Bearer ${token}` }, timeout: 8000 },
      );
      setUsers(res.data.users || []);
    } catch { /* silent */ } finally {
      setSearching(false);
    }
  }, [token]);

  const startConv = async () => {
    if (!selected) return;
    setSending(true);
    try {
      const res = await axios.post(
        `${API}/messaging/send`,
        { recipient_id: selected.id, content: message.trim() || "Hallo!" },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 12000 },
      );
      onCreated(res.data.conversation_id);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Starten der Unterhaltung");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-md rounded-2xl border bg-card p-6 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Neue Unterhaltung</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent">
            <X className="w-4 h-4" />
          </button>
        </div>

        {selected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/20">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                <User className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{selected.name}</div>
                <div className="text-xs text-muted-foreground truncate">{selected.email}</div>
              </div>
              <button onClick={() => setSelected(null)} className="text-xs text-muted-foreground hover:text-foreground">
                Ändern
              </button>
            </div>
            <textarea
              className="w-full rounded-xl border bg-background/50 p-3 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
              rows={3}
              placeholder="Erste Nachricht (optional)…"
              value={message}
              onChange={e => setMessage(e.target.value)}
              maxLength={2000}
              autoFocus
            />
            <div className="flex gap-2">
              <Button variant="ghost" className="flex-1" onClick={onClose}>Abbrechen</Button>
              <Button className="flex-1 gap-2" onClick={startConv} disabled={sending}>
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Senden
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Nutzer suchen (Name oder E-Mail)…"
                value={query}
                onChange={e => search(e.target.value)}
                autoFocus
              />
            </div>
            {searching && (
              <div className="flex justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            )}
            <div className="max-h-52 overflow-y-auto space-y-1">
              {users.map(u => (
                <button
                  key={u.id}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-accent text-left"
                  onClick={() => setSelected(u)}
                >
                  <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                    <User className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{u.name}</div>
                    <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                  </div>
                  {u.is_admin && <span className="text-xs text-amber-500 font-medium shrink-0">Admin</span>}
                </button>
              ))}
              {!searching && query.length > 0 && users.length === 0 && (
                <p className="text-center text-sm text-muted-foreground py-4">Keine Nutzer gefunden</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function MessagingPage() {
  const { token, user } = useAuth();
  const hdrs = { Authorization: `Bearer ${token}` };

  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [showNewConv, setShowNewConv] = useState(false);
  const [mobileView, setMobileView] = useState("inbox");
  const [contactMsg, setContactMsg] = useState("");
  const [contacting, setContacting] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      const res = await axios.get(`${API}/messaging/conversations`, { headers: hdrs, timeout: 10000 });
      setConversations(res.data.conversations || []);
    } catch { /* silent */ } finally {
      setLoadingConvs(false);
    }
  }, [token]);

  const fetchMessages = useCallback(async (convId) => {
    if (!token || !convId) return;
    try {
      const res = await axios.get(
        `${API}/messaging/conversations/${convId}`,
        { headers: hdrs, timeout: 10000 },
      );
      setMessages(res.data.messages || []);
      if (res.data.conversation) setActiveConv(res.data.conversation);
    } catch { /* silent */ }
  }, [token]);

  // ── Polling ────────────────────────────────────────────────────────────────

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  useEffect(() => {
    const id = setInterval(() => { if (!document.hidden) fetchConversations(); }, 30000);
    return () => clearInterval(id);
  }, [fetchConversations]);

  useEffect(() => {
    if (!activeConvId) return;
    const id = setInterval(() => {
      if (!document.hidden) fetchMessages(activeConvId);
    }, 4000);
    return () => clearInterval(id);
  }, [activeConvId, fetchMessages]);

  // ── Scroll to bottom on new messages ──────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Actions ────────────────────────────────────────────────────────────────

  const markRead = useCallback(async (convId) => {
    try {
      await axios.post(`${API}/messaging/conversations/${convId}/read`, null, { headers: hdrs, timeout: 8000 });
    } catch { /* silent */ }
  }, [token]);

  const selectConversation = useCallback(async (convId) => {
    setActiveConvId(convId);
    setMessages([]);
    setLoadingMsgs(true);
    setMobileView("thread");
    setConversations(prev => prev.map(c => c.id === convId ? { ...c, unread_count: 0 } : c));
    markRead(convId);
    await fetchMessages(convId);
    setLoadingMsgs(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [fetchMessages, markRead]);

  const sendMessage = async () => {
    if (!inputText.trim() || !activeConvId || sending) return;
    const text = inputText.trim();
    setInputText("");
    setSending(true);

    // Determine recipient_id from activeConv participants
    const participantsInfo = activeConv?.participants_info || {};
    const participantIds = activeConv?.participants || [];
    const otherId = participantIds.find(id => id !== user?.id);
    if (!otherId) {
      toast.error("Empfänger nicht gefunden");
      setInputText(text);
      setSending(false);
      return;
    }

    const optimistic = {
      id: `opt-${Date.now()}`,
      conversation_id: activeConvId,
      sender_id: user?.id,
      content: text,
      created_at: new Date().toISOString(),
      read_by: [user?.id],
      sender_role: user?.is_admin ? "admin" : "user",
    };
    setMessages(prev => [...prev, optimistic]);

    try {
      const res = await axios.post(
        `${API}/messaging/send`,
        { recipient_id: otherId, content: text, conversation_id: activeConvId },
        { headers: hdrs, timeout: 12000 },
      );
      setMessages(prev => prev.map(m =>
        m.id === optimistic.id ? { ...optimistic, id: res.data.message_id, created_at: res.data.created_at } : m
      ));
      setConversations(prev => prev.map(c =>
        c.id === activeConvId
          ? { ...c, last_message_preview: text, last_message_at: res.data.created_at, last_message_sender_id: user?.id }
          : c
      ));
    } catch (e) {
      setMessages(prev => prev.filter(m => m.id !== optimistic.id));
      setInputText(text);
      toast.error(e.response?.data?.detail || "Nachricht konnte nicht gesendet werden");
    } finally {
      setSending(false);
    }
  };

  const contactAdmin = async () => {
    if (!contactMsg.trim()) return;
    setContacting(true);
    try {
      const res = await axios.post(
        `${API}/messaging/contact-admin`,
        { content: contactMsg.trim() },
        { headers: hdrs, timeout: 15000 },
      );
      setContactMsg("");
      await fetchConversations();
      selectConversation(res.data.conversation_id);
      toast.success("Nachricht gesendet");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Senden");
    } finally {
      setContacting(false);
    }
  };

  const onNewConvCreated = async (convId) => {
    setShowNewConv(false);
    await fetchConversations();
    selectConversation(convId);
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

  const getOtherUser = (conv) => {
    if (!conv) return null;
    const info = conv.participants_info || {};
    const otherId = (conv.participants || []).find(id => id !== user?.id);
    return otherId ? (info[otherId] || { name: "Unbekannt", id: otherId }) : null;
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  const currentOtherUser = getOtherUser(activeConv);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div
        className="flex rounded-2xl border border-border/50 overflow-hidden shadow-lg bg-card"
        style={{ height: "calc(100vh - 9rem)" }}
      >

        {/* ── Conversation list (left) ── */}
        <div className={`
          ${mobileView === "thread" ? "hidden" : "flex"} md:flex
          flex-col w-full md:w-72 lg:w-80 border-r border-border/50 shrink-0
        `}>
          <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between">
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-primary" />
              Nachrichten
            </h2>
            {user?.is_admin && (
              <button
                onClick={() => setShowNewConv(true)}
                className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                title="Neue Unterhaltung"
              >
                <Plus className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingConvs ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-5 text-center">
                <MessageSquare className="w-10 h-10 mx-auto mb-3 text-muted-foreground/25" />
                <p className="text-sm text-muted-foreground mb-4">
                  {user?.is_admin ? "Noch keine Unterhaltungen" : "Noch keine Nachrichten"}
                </p>
                {!user?.is_admin && (
                  <div className="space-y-2 text-left">
                    <p className="text-xs text-muted-foreground text-center mb-2">Schreiben Sie dem Admin:</p>
                    <textarea
                      className="w-full rounded-xl border bg-background/50 p-3 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                      rows={3}
                      placeholder="Ihre Nachricht…"
                      value={contactMsg}
                      onChange={e => setContactMsg(e.target.value)}
                      maxLength={2000}
                    />
                    <Button
                      size="sm"
                      className="w-full gap-2"
                      onClick={contactAdmin}
                      disabled={contacting || !contactMsg.trim()}
                    >
                      {contacting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      Senden
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              conversations.map(conv => {
                const other = getOtherUser(conv);
                const isActive = conv.id === activeConvId;
                const hasUnread = (conv.unread_count || 0) > 0;
                return (
                  <button
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`w-full text-left px-4 py-3 flex gap-3 items-start border-b border-border/20 transition-colors hover:bg-accent/40 ${
                      isActive ? "bg-primary/5 border-l-2 border-l-primary" : ""
                    }`}
                  >
                    <div className="w-9 h-9 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                      <User className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5 gap-2">
                        <span className={`text-sm truncate ${hasUnread ? "font-semibold" : "font-medium"}`}>
                          {other?.name || "Unbekannt"}
                          {other?.is_admin && (
                            <span className="ml-1.5 text-[10px] px-1 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-medium">
                              Admin
                            </span>
                          )}
                        </span>
                        <span className="text-[11px] text-muted-foreground/60 shrink-0">
                          {fmtConvTime(conv.last_message_at)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <p className={`text-xs truncate flex-1 ${hasUnread ? "text-foreground" : "text-muted-foreground"}`}>
                          {conv.last_message_sender_id === user?.id && (
                            <span className="text-muted-foreground/50">Du: </span>
                          )}
                          {conv.last_message_preview || "Unterhaltung starten…"}
                        </p>
                        {hasUnread > 0 && (
                          <span className="w-5 h-5 bg-primary rounded-full text-[10px] font-bold text-primary-foreground flex items-center justify-center shrink-0">
                            {conv.unread_count > 9 ? "9+" : conv.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Contact admin shortcut for users with existing convs but no admin conv */}
          {!user?.is_admin && conversations.length > 0 && !conversations.some(c => {
            const info = c.participants_info || {};
            return Object.values(info).some(u => u.is_admin && u.id !== user?.id);
          }) && (
            <div className="p-3 border-t border-border/50">
              <Button
                variant="outline" size="sm" className="w-full gap-2"
                onClick={() => setShowNewConv(false) || toast("Nutzen Sie das Formular oben")}
              >
                <MessageSquare className="w-4 h-4" />
                Admin kontaktieren
              </Button>
            </div>
          )}
        </div>

        {/* ── Message thread (right) ── */}
        <div className={`
          ${mobileView === "inbox" ? "hidden" : "flex"} md:flex
          flex-col flex-1 min-w-0 bg-background
        `}>
          {!activeConvId ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-2xl bg-primary/8 flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-primary/30" />
              </div>
              <h3 className="font-semibold mb-1">Nachrichten</h3>
              <p className="text-sm text-muted-foreground">Wählen Sie eine Unterhaltung aus der Liste</p>
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="px-4 py-3 border-b border-border/50 flex items-center gap-3 bg-card/60 shrink-0">
                <button
                  className="md:hidden p-1.5 rounded-lg hover:bg-accent"
                  onClick={() => setMobileView("inbox")}
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <div className="w-9 h-9 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold flex items-center gap-2">
                    {currentOtherUser?.name || "Benutzer"}
                    {currentOtherUser?.is_admin && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-medium">
                        Admin
                      </span>
                    )}
                  </div>
                  {currentOtherUser?.email && (
                    <div className="text-xs text-muted-foreground truncate">{currentOtherUser.email}</div>
                  )}
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {loadingMsgs ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center py-16 text-sm text-muted-foreground">
                    Noch keine Nachrichten — schreiben Sie die erste!
                  </div>
                ) : (
                  messages.map(msg => {
                    const isMe = msg.sender_id === user?.id;
                    const isSystem = msg.is_system_message;
                    if (isSystem) {
                      return (
                        <div key={msg.id} className="flex justify-center">
                          <span className="text-xs text-muted-foreground/60 bg-muted/50 px-3 py-1 rounded-full">
                            {msg.content}
                          </span>
                        </div>
                      );
                    }
                    return (
                      <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 ${
                          isMe
                            ? "bg-primary text-primary-foreground rounded-br-sm"
                            : "bg-muted text-foreground rounded-bl-sm"
                        }`}>
                          <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
                          <div className={`flex items-center gap-1 mt-1 ${isMe ? "justify-end" : "justify-start"}`}>
                            <span className={`text-[10px] ${isMe ? "text-primary-foreground/55" : "text-muted-foreground/70"}`}>
                              {fmtMsgTime(msg.created_at)}
                            </span>
                            {isMe && (
                              <CheckCheck className={`w-3 h-3 ${
                                (msg.read_by?.length || 0) > 1
                                  ? "text-primary-foreground"
                                  : "text-primary-foreground/40"
                              }`} />
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-3 border-t border-border/50 bg-card/30 shrink-0">
                <div className="flex gap-2 items-end">
                  <textarea
                    ref={inputRef}
                    className="flex-1 rounded-xl border bg-background px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                    style={{ maxHeight: "8rem" }}
                    rows={1}
                    placeholder="Nachricht schreiben… (Enter zum Senden, Shift+Enter für Zeilenumbruch)"
                    value={inputText}
                    onChange={e => setInputText(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    maxLength={5000}
                  />
                  <Button
                    size="icon"
                    className="h-10 w-10 rounded-xl shrink-0"
                    onClick={sendMessage}
                    disabled={!inputText.trim() || sending}
                  >
                    {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {showNewConv && (
        <NewConvModal
          token={token}
          onClose={() => setShowNewConv(false)}
          onCreated={onNewConvCreated}
        />
      )}
    </div>
  );
}
