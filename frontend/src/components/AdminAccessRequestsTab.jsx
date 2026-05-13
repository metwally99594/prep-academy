import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";

const STATUS_BADGE = {
  pending: { label: "Ausstehend", cls: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  approved: { label: "Genehmigt", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" },
  rejected: { label: "Abgelehnt", cls: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" },
};

export default function AdminAccessRequestsTab({ token }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(null);
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const res = await axios.get(`${API}/admin/access-requests`, { headers });
      setRequests(res.data);
    } catch (e) {
      toast.error("Fehler beim Laden der Zugangsanfragen");
    } finally {
      setLoading(false);
    }
  };

  const resolve = async (requestId, status) => {
    setResolving(requestId);
    try {
      await axios.patch(`${API}/admin/access-requests/${requestId}`, { status }, { headers });
      toast.success(status === "approved" ? "Zugang genehmigt" : "Zugang abgelehnt");
      setRequests(prev => prev.map(r =>
        r.id === requestId ? { ...r, status, reviewed_at: new Date().toISOString() } : r
      ));
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Bearbeiten");
    } finally {
      setResolving(null);
    }
  };

  const resolveUserNames = async () => {
    const userIds = [...new Set(requests.map(r => r.user_id))];
    try {
      const res = await axios.post(`${API}/admin/users/by-ids`, { ids: userIds }, { headers });
      const nameMap = {};
      (res.data?.users || []).forEach(u => { nameMap[u.id] = u; });
      setRequests(prev => prev.map(r => ({
        ...r,
        _user: nameMap[r.user_id] || { name: r.user_id, email: "" },
      })));
    } catch (e) {
      // Fallback: show user_id
      setRequests(prev => prev.map(r => ({
        ...r,
        _user: { name: r.user_id, email: "" },
      })));
    }
  };

  useEffect(() => {
    if (requests.length > 0 && !requests[0]._user) {
      resolveUserNames();
    }
  }, [requests.length]);

  const badge = (status) => {
    const cfg = STATUS_BADGE[status] || STATUS_BADGE.pending;
    return <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>{cfg.label}</span>;
  };

  if (loading) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Zugangsanfragen</h2>
        <Button variant="outline" size="sm" onClick={fetchRequests} className="gap-2">
          <Loader2 className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Aktualisieren
        </Button>
      </div>

      {requests.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Keine Zugangsanfragen vorhanden</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">Benutzer</th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">E-Mail</th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">Feature</th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">Status</th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">Erstellt</th>
                <th className="text-right py-3 px-2 font-medium text-muted-foreground">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-2 font-medium">{r._user?.name || r.user_id.slice(0, 8)}</td>
                  <td className="py-3 px-2 text-muted-foreground">{r._user?.email || "—"}</td>
                  <td className="py-3 px-2">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/5 text-xs font-medium">
                      {r.feature_pack === "advanced_features" ? "Erweiterte Funktionen" : r.feature_pack}
                    </span>
                  </td>
                  <td className="py-3 px-2">{badge(r.status)}</td>
                  <td className="py-3 px-2 text-muted-foreground text-xs">
                    {r.created_at ? new Date(r.created_at).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </td>
                  <td className="py-3 px-2 text-right">
                    {r.status === "pending" ? (
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resolve(r.id, "approved")}
                          disabled={resolving === r.id}
                          className="text-emerald-600 hover:text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                        >
                          {resolving === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                          <span className="hidden sm:inline ml-1">Genehmigen</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resolve(r.id, "rejected")}
                          disabled={resolving === r.id}
                          className="text-red-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                        >
                          {resolving === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-4 h-4" />}
                          <span className="hidden sm:inline ml-1">Ablehnen</span>
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
