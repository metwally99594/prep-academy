import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Bell, Check, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotificationGroup } from "@/components/notifications/NotificationGroup";

export default function NotificationsPage() {
  const { token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [markingRead, setMarkingRead] = useState(false);
  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/notifications`, { headers, timeout: 10000 });
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (e) {
      setError(e.response?.data?.detail || "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const markAllRead = useCallback(async () => {
    if (markingRead || unreadCount === 0) return;
    setMarkingRead(true);
    try {
      await axios.post(`${API}/notifications/read`, null, { headers, timeout: 8000 });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } finally {
      setMarkingRead(false);
    }
  }, [markingRead, unreadCount, headers]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bell className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">Benachrichtigungen</h1>
            {unreadCount > 0 && (
              <p className="text-xs text-muted-foreground">{unreadCount} ungelesen</p>
            )}
          </div>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={markAllRead}
            disabled={markingRead}
          >
            {markingRead
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Check className="w-3.5 h-3.5" />
            }
            Alle gelesen
          </Button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-xl px-4 py-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="rounded-xl border border-border/40 bg-card px-4 py-3 flex gap-3 animate-pulse">
              <div className="w-8 h-8 rounded-xl bg-muted shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-16">
          <Bell className="w-12 h-12 mx-auto mb-3 text-muted-foreground/20" />
          <p className="text-sm text-muted-foreground">Keine Benachrichtigungen</p>
        </div>
      ) : (
        <NotificationGroup notifications={notifications} />
      )}
    </div>
  );
}
