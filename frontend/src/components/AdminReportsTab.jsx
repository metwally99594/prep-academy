import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Flag, Send, CheckCircle, Loader2, MessageSquare, Clock, Filter, ExternalLink, Trash2,
} from "lucide-react";

const STATUS_LABELS = {
  open: { label: "Offen", cls: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" },
  replied: { label: "Beantwortet", cls: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" },
  resolved: { label: "Gelöst", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" },
};

const CATEGORIES = ["Alle", "Falsche Antwort", "Tippfehler", "Unklare Frage", "Fehlende Erklärung", "Inhaltlicher Fehler", "Veraltete Information", "Doppelte Frage", "Technisches Problem"];

export default function AdminReportsTab({ token }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [catFilter, setCatFilter] = useState("Alle");
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchReports = async () => {
    try {
      const res = await axios.get(`${API}/admin/reports/all`, { headers });
      setReports(res.data);
    } catch (e) {
      toast.error("Fehler beim Laden der Meldungen");
    } finally {
      setLoading(false);
    }
  };

  const reply = async (reportId) => {
    if (!replyText.trim()) return;
    setSending(reportId);
    try {
      await axios.post(`${API}/admin/reports/${reportId}/reply`, { message: replyText }, { headers });
      setReports(prev => prev.map(r => r.id === reportId ? { ...r, status: "replied", admin_reply: replyText } : r));
      setReplyingTo(null);
      setReplyText("");
      toast.success("Antwort gesendet");
    } catch (e) {
      toast.error("Fehler beim Senden");
    } finally {
      setSending(null);
    }
  };

  const resolve = async (reportId) => {
    setSending(reportId);
    try {
      await axios.post(`${API}/admin/reports/${reportId}/resolve`, {}, { headers });
      setReports(prev => prev.map(r => r.id === reportId ? { ...r, status: "resolved" } : r));
      toast.success("Meldung gelöst");
    } catch (e) {
      toast.error("Fehler");
    } finally {
      setSending(null);
    }
  };

  const deleteReport = async (reportId) => {
    setSending(reportId);
    try {
      await axios.delete(`${API}/admin/reports/${reportId}`, { headers });
      setReports(prev => prev.filter(r => r.id !== reportId));
      toast.success("Meldung gelöscht");
    } catch (e) {
      toast.error("Fehler beim Löschen");
    } finally {
      setSending(null);
    }
  };

  const filtered = reports.filter(r => {
    if (filter !== "all" && r.status !== filter) return false;
    if (catFilter !== "Alle" && r.category !== catFilter) return false;
    return true;
  });

  const counts = { all: reports.length, open: reports.filter(r => r.status === "open").length, replied: reports.filter(r => r.status === "replied").length, resolved: reports.filter(r => r.status === "resolved").length };

  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString("de-AT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "";

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="glass-card rounded-2xl p-6" data-testid="admin-reports-tab">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Flag className="w-5 h-5 text-red-500" />
          Meldungen ({counts.all})
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Status filter */}
          {["all", "open", "replied", "resolved"].map(s => (
            <button key={s} onClick={() => setFilter(s)} data-testid={`report-filter-${s}`}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === s ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"}`}>
              {s === "all" ? "Alle" : STATUS_LABELS[s]?.label} ({counts[s]})
            </button>
          ))}
          {/* Category filter */}
          <select value={catFilter} onChange={e => setCatFilter(e.target.value)} className="px-2 py-1.5 rounded-lg text-xs border bg-background" data-testid="report-cat-filter">
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Flag className="w-10 h-10 mx-auto opacity-20 mb-3" />
          <p>Keine Meldungen gefunden</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(report => {
            const st = STATUS_LABELS[report.status] || STATUS_LABELS.open;
            return (
              <div key={report.id} className="border rounded-xl p-4 space-y-3" data-testid={`report-${report.id}`}>
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${st.cls}`}>{st.label}</span>
                      <span className="px-2 py-0.5 rounded-full bg-muted text-xs">{report.category}</span>
                      <span className="text-xs text-muted-foreground">{fmtDate(report.created_at)}</span>
                    </div>
                    <p className="text-sm mt-2 font-medium">{report.question_text || "—"}</p>
                    {report.details && <p className="text-sm text-muted-foreground mt-1">{report.details}</p>}
                    <p className="text-xs text-muted-foreground mt-1">Von: {report.user_email}</p>
                  </div>
                  <div className="flex gap-1.5 flex-shrink-0">
                    {report.question_id && (
                      <a href={`/admin?edit=${report.question_id}`} data-testid={`edit-question-${report.id}`}>
                        <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                          <ExternalLink className="w-3 h-3" />
                          Frage bearbeiten
                        </Button>
                      </a>
                    )}
                    {report.status !== "resolved" && (
                      <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => resolve(report.id)} disabled={!!sending} data-testid={`resolve-${report.id}`}>
                        {sending === report.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                        Lösen
                      </Button>
                    )}
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20" onClick={() => deleteReport(report.id)} disabled={!!sending} data-testid={`delete-report-${report.id}`}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>

                {/* Admin Reply */}
                {report.admin_reply && (
                  <div className="pl-4 border-l-2 border-emerald-300 dark:border-emerald-700">
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" /> Admin-Antwort:
                    </p>
                    <p className="text-sm mt-0.5">{report.admin_reply}</p>
                  </div>
                )}

                {/* Reply form */}
                {report.status === "open" && (
                  <>
                    {replyingTo === report.id ? (
                      <div className="flex gap-2" data-testid={`reply-form-${report.id}`}>
                        <input type="text" value={replyText} onChange={e => setReplyText(e.target.value)}
                          placeholder="Antwort schreiben..." className="flex-1 px-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                          data-testid={`reply-input-${report.id}`} onKeyDown={e => e.key === "Enter" && reply(report.id)} />
                        <Button size="sm" className="gap-1" onClick={() => reply(report.id)} disabled={!!sending || !replyText.trim()} data-testid={`reply-send-${report.id}`}>
                          {sending === report.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => { setReplyingTo(null); setReplyText(""); }}>Abbrechen</Button>
                      </div>
                    ) : (
                      <button onClick={() => setReplyingTo(report.id)} className="text-xs text-primary hover:underline flex items-center gap-1" data-testid={`reply-btn-${report.id}`}>
                        <MessageSquare className="w-3 h-3" /> Antworten
                      </button>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
