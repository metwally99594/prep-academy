import { useState, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { toast } from "sonner";
import { useConversations } from "@/hooks/useConversations";
import { useMessages } from "@/hooks/useMessages";
import { ConversationList } from "@/components/messaging/ConversationList";
import { MessageThread } from "@/components/messaging/MessageThread";
import { NewConvModal } from "@/components/messaging/NewConvModal";

export default function MessagingPage() {
  const { token, user } = useAuth();
  const userId = user?.id;
  const headers = { Authorization: `Bearer ${token}` };

  const [activeConvId, setActiveConvId] = useState(null);
  const [mobileView, setMobileView] = useState("inbox"); // "inbox" | "thread"
  const [showNewConv, setShowNewConv] = useState(false);
  const [contactMsg, setContactMsg] = useState("");
  const [contacting, setContacting] = useState(false);
  const [unreadDividerIndex, setUnreadDividerIndex] = useState(null);

  const {
    conversations, loading: loadingConvs, fetch: refreshConvs,
    markRead, filter, setFilter, search, setSearch, setConversations,
  } = useConversations(token);

  const {
    messages, conv: activeConv, loading: loadingMsgs,
    sendMessage,
  } = useMessages(token, activeConvId, userId);

  // ── Conversation selection ─────────────────────────────────────────────────

  const selectConversation = useCallback((convObj) => {
    const prevUnread = convObj.unread_count || 0;
    setUnreadDividerIndex(prevUnread > 0 ? null : null); // will resolve after messages load
    setActiveConvId(convObj.id);
    setMobileView("thread");
    markRead(convObj.id);
    // After messages load, compute divider position
    if (prevUnread > 0) {
      // We'll set it after messages are fetched (handled via effect in MessageThread)
      setUnreadDividerIndex(null); // reset; let messages render normally
    }
  }, [markRead]);

  // Update conversation preview in the list after sending
  const handleSend = useCallback(async (text, attachments) => {
    const result = await sendMessage(text, attachments);
    // Update local conv preview
    setConversations(prev => prev.map(c =>
      c.id === activeConvId
        ? {
            ...c,
            last_message_preview: text || (attachments.length ? "📎 Anhang" : ""),
            last_message_at: result?.created_at || new Date().toISOString(),
            last_message_sender_id: userId,
          }
        : c,
    ));
  }, [sendMessage, setConversations, activeConvId, userId]);

  // ── Contact admin (non-admin users) ───────────────────────────────────────

  const contactAdmin = useCallback(async () => {
    if (!contactMsg.trim()) return;
    setContacting(true);
    try {
      const res = await axios.post(
        `${API}/messaging/contact-admin`,
        { content: contactMsg.trim() },
        { headers, timeout: 15000 },
      );
      setContactMsg("");
      await refreshConvs();
      // Find the conversation and select it
      const conv = conversations.find(c => c.id === res.data.conversation_id);
      if (conv) selectConversation(conv);
      else {
        await refreshConvs();
        setActiveConvId(res.data.conversation_id);
        setMobileView("thread");
      }
      toast.success("Nachricht gesendet");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Nachricht konnte nicht gesendet werden. Bitte überprüfen Sie Ihre Verbindung.");
    } finally {
      setContacting(false);
    }
  }, [contactMsg, headers, refreshConvs, conversations, selectConversation]);

  // ── New conversation created (admin) ──────────────────────────────────────

  const onNewConvCreated = useCallback(async (convId) => {
    setShowNewConv(false);
    await refreshConvs();
    setActiveConvId(convId);
    setMobileView("thread");
  }, [refreshConvs]);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div
        className="flex rounded-2xl border border-border/50 overflow-hidden shadow-lg bg-card"
        style={{ height: "calc(100dvh - 9rem)" }}
      >
        {/* Left: conversation list */}
        <div
          className={`${mobileView === "thread" ? "hidden" : "flex"} md:flex flex-col w-full md:w-72 lg:w-80 border-r border-border/50 shrink-0 min-h-0`}
        >
          <ConversationList
            conversations={conversations}
            loading={loadingConvs}
            activeConvId={activeConvId}
            userId={userId}
            isAdmin={user?.is_admin}
            filter={filter}
            setFilter={setFilter}
            search={search}
            setSearch={setSearch}
            onSelect={selectConversation}
            onNewConv={() => setShowNewConv(true)}
            onContactAdmin={contactAdmin}
            contactingAdmin={contacting}
            contactMsg={contactMsg}
            setContactMsg={setContactMsg}
          />
        </div>

        {/* Right: message thread */}
        <div
          className={`${mobileView === "inbox" ? "hidden" : "flex"} md:flex flex-col flex-1 min-w-0 min-h-0 bg-background`}
        >
          <MessageThread
            conv={activeConv}
            messages={messages}
            loading={loadingMsgs}
            userId={userId}
            activeConvId={activeConvId}
            unreadDividerIndex={unreadDividerIndex}
            onBack={() => setMobileView("inbox")}
            onSend={handleSend}
          />
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
