import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { useNavigate } from "react-router-dom";
import {
  Bell, Trophy, Flame, Zap, Check, Send, Loader2, Flag, MessageSquare,
  Lock, Unlock, XCircle,
} from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

const NOTIF_ICONS = {
  bell: Bell,
  trophy: Trophy,
  flame: Flame,
  zap: Zap,
  lock: Lock,
  unlock: Unlock,
  "x-circle": XCircle,
};

export default function NotificationBell() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const fetchNotifications = useCallback(async () => {
    if (!token) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API}/community/notifications?limit=20`, { headers });
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    axios.post(`${API}/notifications/generate-daily`, null, { headers }).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token) return;
    fetchNotifications();
  }, [fetchNotifications, token]);

  const markAllRead = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/community/notifications/mark-all-read`, null, { headers });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark notifications as read:", error);
    }
  };

  const handleOpen = (isOpen) => {
    setOpen(isOpen);
    if (isOpen && unreadCount > 0) {
      markAllRead();
    }
    if (!isOpen) {
      setReplyingTo(null);
      setReplyText("");
    }
  };

  const sendReply = async (reportId) => {
    if (!replyText.trim()) return;
    setSending(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/admin/reports/${reportId}/reply`, { message: replyText }, { headers });
      setReplyingTo(null);
      setReplyText("");
      setNotifications(prev => prev.map(n =>
        n.id === replyingTo ? { ...n, replied: true } : n
      ));
    } catch (error) {
      console.error("Failed to send reply:", error);
    } finally {
      setSending(false);
    }
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return "Gerade eben";
    if (diffMins < 60) return `Vor ${diffMins} Min.`;
    if (diffHours < 24) return `Vor ${diffHours} Std.`;
    if (diffDays < 7) return `Vor ${diffDays} Tag${diffDays > 1 ? 'en' : ''}`;
    return date.toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit' });
  };

  // Extract report_id from notification message for admin reply
  const getReportId = (notif) => {
    return notif.report_id || null;
  };

  return (
    <Popover open={open} onOpenChange={handleOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" data-testid="notification-bell">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center animate-pulse-glow" data-testid="notification-badge">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="p-3 border-b border-border flex items-center justify-between">
          <button
            className="font-semibold text-sm hover:text-primary transition-colors"
            onClick={() => { setOpen(false); navigate("/notifications"); }}
          >
            Benachrichtigungen
          </button>
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="text-xs text-primary hover:underline flex items-center gap-1">
              <Check className="w-3 h-3" /> Alle gelesen
            </button>
          )}
        </div>
        <div className="max-h-96 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground text-sm">
              <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Keine Benachrichtigungen</p>
            </div>
          ) : (
            notifications.map((notif) => {
              const isReport = notif.type === "report";
              const isReportReply = notif.type === "report_reply";
              const isAccessRequest = notif.type === "access_request";
              const isAccessGranted = notif.type === "access_granted";
              const isAccessRejected = notif.type === "access_rejected";
              const IconComp = isReport ? Flag
                : isReportReply ? MessageSquare
                : isAccessRequest ? Lock
                : isAccessGranted ? Unlock
                : isAccessRejected ? XCircle
                : (NOTIF_ICONS[notif.icon] || Bell);

              return (
                <div
                  key={notif.id}
                  className={`p-3 border-b border-border/50 transition-colors ${!notif.read ? 'bg-primary/5' : ''}`}
                  data-testid={`notification-${notif.id}`}
                >
                  <div className="flex gap-3">
                    <div className={`p-2 rounded-lg shrink-0 ${
                      isReport ? 'bg-red-500/15' :
                      isReportReply ? 'bg-emerald-500/15' :
                      isAccessRequest ? 'bg-amber-500/15' :
                      isAccessGranted ? 'bg-emerald-500/15' :
                      isAccessRejected ? 'bg-red-500/15' :
                      notif.type === 'level_up' ? 'bg-amber-500/15' :
                      notif.type === 'streak_warning' ? 'bg-orange-500/15' :
                      'bg-primary/10'
                    }`}>
                      <IconComp className={`w-4 h-4 ${
                        isReport ? 'text-red-500' :
                        isReportReply ? 'text-emerald-500' :
                        isAccessRequest ? 'text-amber-500' :
                        isAccessGranted ? 'text-emerald-500' :
                        isAccessRejected ? 'text-red-500' :
                        notif.type === 'level_up' ? 'text-amber-500' :
                        notif.type === 'streak_warning' ? 'text-orange-500' :
                        'text-primary'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{notif.title}</span>
                        {!notif.read && <span className="w-2 h-2 bg-primary rounded-full shrink-0" />}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{notif.message}</p>
                      <span className="text-xs text-muted-foreground/70 mt-1 block">{formatTime(notif.created_at)}</span>

                      {/* Admin reply button for report notifications */}
                      {isReport && user?.is_admin && notif.report_id && !notif.replied && (
                        <>
                          {replyingTo === notif.id ? (
                            <div className="mt-2 space-y-2" data-testid={`reply-form-${notif.id}`}>
                              <input
                                type="text"
                                value={replyText}
                                onChange={e => setReplyText(e.target.value)}
                                placeholder="Antwort schreiben..."
                                className="w-full px-3 py-1.5 text-xs rounded-lg border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                                data-testid={`reply-input-${notif.id}`}
                                onKeyDown={e => e.key === 'Enter' && sendReply(notif.report_id)}
                              />
                              <div className="flex gap-1.5">
                                <Button
                                  size="sm"
                                  className="h-7 text-xs gap-1 px-2"
                                  onClick={() => sendReply(notif.report_id)}
                                  disabled={sending || !replyText.trim()}
                                  data-testid={`reply-send-${notif.id}`}
                                >
                                  {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                  Senden
                                </Button>
                                <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => { setReplyingTo(null); setReplyText(""); }}>
                                  Abbrechen
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => setReplyingTo(notif.id)}
                              className="mt-1.5 flex items-center gap-1 text-xs text-primary hover:underline"
                              data-testid={`reply-btn-${notif.id}`}
                            >
                              <MessageSquare className="w-3 h-3" />
                              Antworten
                            </button>
                          )}
                        </>
                      )}

                      {/* Show "replied" badge */}
                      {isReport && notif.replied && (
                        <span className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                          <Check className="w-3 h-3" /> Beantwortet
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
