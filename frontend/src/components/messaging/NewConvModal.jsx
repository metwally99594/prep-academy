import { useState, useCallback } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { Search, User, X, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";

export function NewConvModal({ token, onClose, onCreated }) {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const headers = { Authorization: `Bearer ${token}` };

  const search = useCallback(async (q) => {
    setQuery(q);
    if (!q.trim()) { setUsers([]); return; }
    setSearching(true);
    try {
      const res = await axios.get(
        `${API}/messaging/admin/users?q=${encodeURIComponent(q)}`,
        { headers, timeout: 8000 },
      );
      setUsers(res.data.users || []);
    } catch { /* silent */ } finally {
      setSearching(false);
    }
  }, [token]);

  const start = async () => {
    if (!selected) return;
    setSending(true);
    try {
      const res = await axios.post(
        `${API}/messaging/send`,
        { recipient_id: selected.id, content: message.trim() || "Hallo!" },
        { headers, timeout: 15000 },
      );
      onCreated(res.data.conversation_id);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Unterhaltung konnte nicht gestartet werden. Bitte überprüfen Sie Ihre Verbindung.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl border bg-card shadow-2xl"
        style={{ maxHeight: "85dvh" }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
          <h3 className="font-semibold">Neue Unterhaltung</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground"
            aria-label="Schließen"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4" style={{ maxHeight: "calc(85dvh - 64px)", overflowY: "auto", overscrollBehavior: "contain" }}>
          {selected ? (
            <>
              {/* Selected user card */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/20">
                <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold">{selected.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{selected.email}</p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-lg hover:bg-accent"
                >
                  Ändern
                </button>
              </div>

              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1.5">
                  Erste Nachricht (optional)
                </label>
                <textarea
                  className="w-full rounded-xl border bg-background/50 p-3 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                  rows={3}
                  placeholder="Schreiben Sie etwas…"
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  maxLength={2000}
                  autoFocus
                />
              </div>

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={onClose}>
                  Abbrechen
                </Button>
                <Button className="flex-1 gap-2" onClick={start} disabled={sending}>
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Senden
                </Button>
              </div>
            </>
          ) : (
            <>
              {/* User search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="search"
                  className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nutzer suchen (Name oder E-Mail)…"
                  value={query}
                  onChange={e => search(e.target.value)}
                  autoFocus
                />
              </div>

              {searching ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-1">
                  {users.map(u => (
                    <button
                      key={u.id}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-accent transition-colors text-left"
                      onClick={() => setSelected(u)}
                    >
                      <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                        <User className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{u.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                      </div>
                      {u.is_admin && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold tracking-wide uppercase shrink-0">
                          Admin
                        </span>
                      )}
                    </button>
                  ))}
                  {!searching && query.length > 0 && users.length === 0 && (
                    <p className="text-center text-sm text-muted-foreground py-6">Keine Nutzer gefunden</p>
                  )}
                  {!query && (
                    <p className="text-center text-xs text-muted-foreground/60 py-4">
                      Geben Sie einen Namen oder eine E-Mail-Adresse ein
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
