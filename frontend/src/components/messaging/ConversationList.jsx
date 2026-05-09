import { useRef, useEffect } from "react";
import { MessageSquare, Search, Plus, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConversationItem } from "./ConversationItem";

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 px-4 py-3 border-b border-border/20 animate-pulse">
      <div className="w-9 h-9 rounded-full bg-muted shrink-0 mt-0.5" />
      <div className="flex-1 space-y-2">
        <div className="flex justify-between">
          <div className="h-3.5 bg-muted rounded w-28" />
          <div className="h-3 bg-muted rounded w-10" />
        </div>
        <div className="h-3 bg-muted rounded w-40" />
      </div>
    </div>
  );
}

export function ConversationList({
  conversations,
  loading,
  activeConvId,
  userId,
  isAdmin,
  filter,
  setFilter,
  search,
  setSearch,
  onSelect,
  onNewConv,
  onContactAdmin,
  contactingAdmin,
  contactMsg,
  setContactMsg,
}) {
  const searchRef = useRef(null);

  return (
    <div className="flex flex-col h-full w-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/50 shrink-0">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-primary" />
            Nachrichten
          </h2>
          {isAdmin && (
            <button
              onClick={onNewConv}
              className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              title="Neue Unterhaltung"
              aria-label="Neue Unterhaltung starten"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
          <input
            ref={searchRef}
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Suchen…"
            className="w-full pl-8 pr-7 py-1.5 text-xs rounded-lg border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            aria-label="Unterhaltungen durchsuchen"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Suche leeren"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1">
          {[["all", "Alle"], ["unread", "Ungelesen"]].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={`flex-1 text-xs py-1 rounded-lg transition-colors font-medium ${
                filter === val
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {loading ? (
          <>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </>
        ) : conversations.length === 0 ? (
          <EmptyState
            isAdmin={isAdmin}
            filter={filter}
            onContactAdmin={onContactAdmin}
            contactingAdmin={contactingAdmin}
            contactMsg={contactMsg}
            setContactMsg={setContactMsg}
          />
        ) : (
          conversations.map(conv => (
            <ConversationItem
              key={conv.id}
              conv={conv}
              isActive={conv.id === activeConvId}
              userId={userId}
              onClick={() => onSelect(conv)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function EmptyState({ isAdmin, filter, onContactAdmin, contactingAdmin, contactMsg, setContactMsg }) {
  if (filter === "unread") {
    return (
      <div className="p-6 text-center">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-muted-foreground/20" />
        <p className="text-xs text-muted-foreground">Keine ungelesenen Nachrichten</p>
      </div>
    );
  }
  if (isAdmin) {
    return (
      <div className="p-6 text-center">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-muted-foreground/20" />
        <p className="text-sm text-muted-foreground mb-1">Noch keine Unterhaltungen</p>
        <p className="text-xs text-muted-foreground/60">Klicken Sie auf + um zu beginnen</p>
      </div>
    );
  }
  // Non-admin user: show contact form
  return (
    <div className="p-5 space-y-3">
      <div className="text-center">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-muted-foreground/20" />
        <p className="text-sm text-muted-foreground mb-3">Noch keine Nachrichten</p>
      </div>
      <p className="text-xs text-muted-foreground/70 text-center font-medium">Schreiben Sie dem Admin:</p>
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
        onClick={onContactAdmin}
        disabled={contactingAdmin || !contactMsg.trim()}
      >
        {contactingAdmin ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
        Senden
      </Button>
    </div>
  );
}
