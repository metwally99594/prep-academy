import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Loader2, CheckCircle, XCircle, Clock, Mail, Phone, MessageSquare, Globe, User } from "lucide-react";

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
    // Only fetch names for registered users (skip public contact form submissions)
    const userIds = [...new Set(requests.map(r => r.user_id).filter(Boolean))];
    if (userIds.length === 0) {
      setRequests(prev => prev.map(r => ({ ...r, _user: r._user || null })));
      return;
    }
    try {
      const res = await axios.post(`${API}/admin/users/by-ids`, { ids: userIds }, { headers });
      const nameMap = {};
      (res.data?.users || []).forEach(u => { nameMap[u.id] = u; });
      setRequests(prev => prev.map(r => ({
        ...r,
        _user: r.user_id ? (nameMap[r.user_id] || { name: r.user_id.slice(0, 8), email: "" }) : null,
      })));
    } catch (e) {
      setRequests(prev => prev.map(r => ({
        ...r,
        _user: r.user_id ? { name: r.user_id.slice(0, 8), email: "" } : null,
      })));
    }
  };

  useEffect(() => {
    if (requests.length > 0 && requests[0]._user === undefined) {
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
        <div className="space-y-3">
          {requests.map(r => {
            const isPublic = !r.user_id || r.source === "public_contact_form";
            const displayName = isPublic ? (r.user_name || "Unbekannt") : (r._user?.name || r.user_id?.slice(0, 8));
            const displayEmail = isPublic ? r.user_email : (r._user?.email || "—");
            return (
              <div key={r.id} className="rounded-xl border border-border bg-card/50 p-4 hover:bg-muted/30 transition-colors">
                <div className="flex flex-wrap items-start gap-3 justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      {isPublic ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium">
                          <Globe className="w-3 h-3" /> Öffentliche Anfrage
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium">
                          <User className="w-3 h-3" /> Registriert
                        </span>
                      )}
                      {badge(r.status)}
                      <span className="text-xs text-muted-foreground">
                        {r.created_at ? new Date(r.created_at).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : ""}
                      </span>
                    </div>

                    {/* Contact info */}
                    <div className="space-y-1.5">
                      <div className="font-medium text-base">{displayName}</div>
                      {displayEmail && displayEmail !== "—" && (
                        <a href={`mailto:${displayEmail}`} className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
                          <Mail className="w-3.5 h-3.5" /> {displayEmail}
                        </a>
                      )}
                      {r.phone && (
                        <div>
                          <a href={`tel:${r.phone}`} className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
                            <Phone className="w-3.5 h-3.5" /> {r.phone}
                          </a>
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground">
                        Feature: <span className="font-medium text-foreground">
                          {r.feature_label || (r.feature_pack === "advanced_features" ? "Erweiterte Funktionen" : r.feature_pack) || "—"}
                        </span>
                      </div>
                    </div>

                    {/* Message */}
                    {r.message && (
                      <div className="mt-3 p-3 rounded-lg bg-muted/40 border-l-2 border-primary/40">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wide mb-1">
                          <MessageSquare className="w-3 h-3" /> Nachricht
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{r.message}</p>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  {r.status === "pending" && (
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => resolve(r.id, "approved")}
                        disabled={resolving === r.id}
                        className="text-emerald-600 hover:text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                        data-testid={`approve-${r.id}`}
                      >
                        {resolving === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                        <span className="hidden sm:inline ml-1">{isPublic ? "Kontaktiert" : "Genehmigen"}</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => resolve(r.id, "rejected")}
                        disabled={resolving === r.id}
                        className="text-red-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                        data-testid={`reject-${r.id}`}
                      >
                        {resolving === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-4 h-4" />}
                        <span className="hidden sm:inline ml-1">Ablehnen</span>
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
