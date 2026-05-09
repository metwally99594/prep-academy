import { useRef, useEffect, useMemo, useCallback } from "react";
import { ArrowLeft, User, Loader2, MessageSquare } from "lucide-react";
import { DateSeparator, UnreadDivider } from "./DateSeparator";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";

function SkeletonBubble({ align = "left" }) {
  return (
    <div className={`flex ${align === "right" ? "justify-end" : "justify-start"} animate-pulse`}>
      <div className={`rounded-2xl h-10 bg-muted ${align === "right" ? "w-40" : "w-52"}`} />
    </div>
  );
}

function buildRenderItems(messages, userId, unreadDividerIndex) {
  const items = [];
  let lastDateStr = null;

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    const msgDateStr = new Date(msg.created_at).toDateString();

    if (msgDateStr !== lastDateStr) {
      items.push({ type: "date", key: `sep-${msg.created_at}-${i}`, date: msg.created_at });
      lastDateStr = msgDateStr;
    }

    if (unreadDividerIndex !== null && i === unreadDividerIndex) {
      items.push({ type: "unread", key: "unread-divider" });
    }

    items.push({ type: "message", key: msg.id || `msg-${i}`, msg, index: i });
  }

  return items;
}

export function MessageThread({
  conv,
  messages,
  loading,
  userId,
  activeConvId,
  unreadDividerIndex,
  onBack,
  onSend,
}) {
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);
  const prevConvRef = useRef(null);
  const prevMsgCountRef = useRef(0);

  const other = useMemo(() => {
    if (!conv) return null;
    const info = conv.participants_info || {};
    const otherId = (conv.participants || []).find(id => id !== userId);
    return otherId ? (info[otherId] || { name: "Unbekannt" }) : null;
  }, [conv, userId]);

  // On conv switch: scroll to bottom instantly
  useEffect(() => {
    if (activeConvId !== prevConvRef.current) {
      prevConvRef.current = activeConvId;
      prevMsgCountRef.current = 0;
    }
  }, [activeConvId]);

  // On new messages: smooth-scroll if already near bottom
  useEffect(() => {
    if (!bottomRef.current || !scrollRef.current) return;
    const container = scrollRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const nearBottom = scrollHeight - scrollTop - clientHeight < 140;

    if (prevMsgCountRef.current === 0 || nearBottom) {
      bottomRef.current.scrollIntoView({ behavior: prevMsgCountRef.current === 0 ? "instant" : "smooth" });
    }
    prevMsgCountRef.current = messages.length;
  }, [messages]);

  const renderItems = useMemo(
    () => buildRenderItems(messages, userId, unreadDividerIndex),
    [messages, userId, unreadDividerIndex],
  );

  if (!activeConvId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
        <div className="w-16 h-16 rounded-2xl bg-primary/8 flex items-center justify-center mb-4">
          <MessageSquare className="w-8 h-8 text-primary/25" />
        </div>
        <h3 className="font-semibold mb-1">Nachrichten</h3>
        <p className="text-sm text-muted-foreground">Wählen Sie eine Unterhaltung aus</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-w-0">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/50 flex items-center gap-3 bg-card/60 shrink-0">
        <button
          className="md:hidden p-1.5 rounded-lg hover:bg-accent transition-colors"
          onClick={onBack}
          aria-label="Zurück"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-9 h-9 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold flex items-center gap-2 flex-wrap">
            {other?.name || "Benutzer"}
            {other?.is_admin && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold tracking-wide uppercase">
                Admin
              </span>
            )}
          </div>
          {other?.email && (
            <div className="text-xs text-muted-foreground truncate">{other.email}</div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overscroll-contain px-4 py-3 space-y-1"
      >
        {loading ? (
          <div className="space-y-4 pt-4">
            <SkeletonBubble align="left" />
            <SkeletonBubble align="right" />
            <SkeletonBubble align="left" />
            <SkeletonBubble align="right" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full min-h-32">
            <p className="text-sm text-muted-foreground">Noch keine Nachrichten — schreiben Sie die erste!</p>
          </div>
        ) : (
          renderItems.map(item => {
            if (item.type === "date") return <DateSeparator key={item.key} date={item.date} />;
            if (item.type === "unread") return <UnreadDivider key={item.key} />;
            const { msg } = item;
            const isMe = msg.sender_id === userId;
            const readByOther = (msg.read_by || []).some(id => id !== userId);
            return (
              <MessageBubble
                key={item.key}
                msg={msg}
                isMe={isMe}
                readByOther={readByOther}
              />
            );
          })
        )}
        <div ref={bottomRef} className="h-px" />
      </div>

      {/* Input */}
      <MessageInput onSend={onSend} disabled={loading && messages.length === 0} />
    </div>
  );
}
