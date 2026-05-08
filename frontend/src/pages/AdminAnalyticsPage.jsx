import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import {
  ArrowLeft, Users, Activity, Star, Clock, Search,
  Check, X, ChevronDown, ChevronUp, BarChart3,
  BookOpen, Flame, Zap, Lock, Unlock, AlertCircle,
  TrendingUp, Calendar, Shield, Crown, RefreshCcw, Infinity,
} from "lucide-react";

// ── Helpers ────────────────────────────────────────────────────────
const TIER_COLORS = {
  power:  { bg: "bg-amber-500/15",   text: "text-amber-400",   label: "Power" },
  active: { bg: "bg-emerald-500/15", text: "text-emerald-400", label: "Aktiv" },
  casual: { bg: "bg-blue-500/15",    text: "text-blue-400",    label: "Casual" },
  new:    { bg: "bg-slate-500/15",   text: "text-slate-400",   label: "Neu" },
};

function TierBadge({ tier }) {
  const t = TIER_COLORS[tier] || TIER_COLORS.new;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${t.bg} ${t.text}`}>
      {t.label}
    </span>
  );
}

function ScoreBar({ score }) {
  const color = score >= 80 ? "#c9a84c" : score >= 50 ? "#22c55e" : score >= 20 ? "#3b82f6" : "#64748b";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-border overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs tabular-nums w-8 text-right text-muted-foreground">{score}</span>
    </div>
  );
}

// ── Score Gauge ────────────────────────────────────────────────────
function ScoreGauge({ score }) {
  const angle = (score / 100) * 180 - 90;
  const color = score >= 80 ? "#c9a84c" : score >= 50 ? "#22c55e" : score >= 20 ? "#3b82f6" : "#64748b";
  const r = 54, cx = 64, cy = 64;
  const toXY = (deg) => {
    const rad = (deg - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };
  const start = toXY(-90), end = toXY(angle);
  const large = score > 50 ? 1 : 0;
  return (
    <div className="flex flex-col items-center">
      <svg width="128" height="80" viewBox="0 0 128 80">
        <path d={`M ${toXY(-90).x} ${toXY(-90).y} A ${r} ${r} 0 1 1 ${toXY(90).x} ${toXY(90).y}`}
          fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" strokeLinecap="round" />
        {score > 0 && (
          <path d={`M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`}
            fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 4} textAnchor="middle" fontSize="20" fontWeight="700" fill={color}>{score}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.4)">/100</text>
      </svg>
    </div>
  );
}

// ── Activity Heatmap ───────────────────────────────────────────────
function ActivityHeatmap({ daily }) {
  if (!daily || daily.length === 0) return (
    <p className="text-xs text-muted-foreground">Keine Aktivitätsdaten</p>
  );
  const max = Math.max(...daily.map(d => d.questions || 0), 1);
  return (
    <div className="flex flex-wrap gap-0.5">
      {daily.map((d) => {
        const q = d.questions || 0;
        const intensity = q === 0 ? 0 : Math.ceil((q / max) * 4);
        const colors = ["bg-border", "bg-emerald-900/60", "bg-emerald-700/70", "bg-emerald-500/80", "bg-emerald-400"];
        return (
          <div key={d.date} title={`${d.date}: ${q} Fragen`}
            className={`w-3 h-3 rounded-sm ${colors[intensity]}`} />
        );
      })}
    </div>
  );
}

// ── User Detail Modal ──────────────────────────────────────────────
function UserDetailModal({ userId, token, onClose, onPermissionChange }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState({});
  const [trialAction, setTrialAction] = useState(null); // "extend" | "permanent" | "revoke"

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };
    axios.get(`${API}/admin/analytics/users/${userId}/detail`, { headers })
      .then(r => setDetail(r.data))
      .catch(() => toast.error("Fehler beim Laden"))
      .finally(() => setLoading(false));
  }, [userId, token]);

  const toggleFeature = async (feature, currentVal) => {
    setToggling(p => ({ ...p, [feature]: true }));
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.patch(`${API}/admin/users/${userId}/permissions`,
        { [feature]: !currentVal }, { headers });
      setDetail(prev => ({
        ...prev,
        user: { ...prev.user, [feature]: !currentVal }
      }));
      onPermissionChange?.();
      toast.success("Berechtigung aktualisiert");
    } catch {
      toast.error("Fehler beim Aktualisieren");
    } finally {
      setToggling(p => ({ ...p, [feature]: false }));
    }
  };

  const doTrialAction = async (action) => {
    setTrialAction(action);
    const headers = { Authorization: `Bearer ${token}` };
    try {
      if (action === "extend") {
        const r = await axios.post(`${API}/admin/users/${userId}/trial/extend`, { days: 30 }, { headers });
        setDetail(prev => ({ ...prev, user: { ...prev.user, trial_ends_at: r.data.trial_ends_at, is_permanent: false } }));
        toast.success("Probezeit um 30 Tage verlängert");
      } else if (action === "permanent") {
        await axios.post(`${API}/admin/users/${userId}/make-permanent`, {}, { headers });
        setDetail(prev => ({ ...prev, user: { ...prev.user, is_permanent: true } }));
        toast.success("Permanenter Zugang gesetzt");
      } else if (action === "revoke") {
        await axios.post(`${API}/admin/users/${userId}/revoke`, {}, { headers });
        setDetail(prev => ({ ...prev, user: { ...prev.user, is_permanent: false, notebook_enabled: false, analyzer_enabled: false, podcast_enabled: false } }));
        toast.success("Zugang widerrufen");
      }
      onPermissionChange?.();
    } catch {
      toast.error("Aktion fehlgeschlagen");
    } finally {
      setTrialAction(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-[#0c1229] shadow-2xl"
        onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b border-border bg-[#0c1229]">
          <h2 className="font-bold text-base">Benutzer-Detail</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/5">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : detail ? (
          <div className="p-5 space-y-5">
            {/* Header */}
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <span className="text-lg font-bold text-primary">
                  {(detail.user?.name || "?")[0].toUpperCase()}
                </span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold">{detail.user?.name}</h3>
                  <TierBadge tier={detail.tier} />
                </div>
                <p className="text-sm text-muted-foreground">{detail.user?.email}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Aktiv vor {detail.last_active ? Math.floor((Date.now() - new Date(detail.last_active)) / 86400000) : "?"} Tagen
                </p>
              </div>
              <ScoreGauge score={detail.score} />
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Fragen", val: detail.stats?.total_questions || 0, icon: BookOpen },
                { label: "Genauigkeit", val: `${detail.stats?.total_questions > 0 ? Math.round(detail.stats.correct_answers / detail.stats.total_questions * 100) : 0}%`, icon: TrendingUp },
                { label: "Streak", val: `${detail.streak?.current_streak || 0}d`, icon: Flame },
                { label: "XP", val: detail.stats?.xp || 0, icon: Zap },
              ].map(({ label, val, icon: Icon }) => (
                <div key={label} className="rounded-xl border border-border bg-white/2 p-3 text-center">
                  <Icon className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
                  <div className="font-bold text-sm">{val}</div>
                  <div className="text-[10px] text-muted-foreground">{label}</div>
                </div>
              ))}
            </div>

            {/* Activity heatmap */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" /> 90-Tage-Aktivität
              </h4>
              <ActivityHeatmap daily={detail.daily_activity} />
            </div>

            {/* Subject performance */}
            {detail.subject_performance?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <BarChart3 className="w-3.5 h-3.5" /> Fachgebiete
                </h4>
                <div className="space-y-1.5">
                  {detail.subject_performance.slice(-5).reverse().map(s => (
                    <div key={s.id} className="flex items-center gap-2 text-xs">
                      <span className="w-28 truncate text-muted-foreground">{s.id}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-border overflow-hidden">
                        <div className="h-full rounded-full bg-primary/70" style={{ width: `${s.accuracy}%` }} />
                      </div>
                      <span className="w-10 text-right">{s.accuracy}%</span>
                      <span className="text-muted-foreground">({s.total})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Feature toggles */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" /> Berechtigungen
              </h4>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { field: "notebook_enabled", label: "Notebook" },
                  { field: "analyzer_enabled", label: "Analyzer" },
                  { field: "podcast_enabled", label: "Podcast" },
                ].map(({ field, label }) => (
                  <div key={field} className="flex items-center justify-between rounded-xl border border-border p-2.5">
                    <span className="text-xs">{label}</span>
                    <Switch
                      checked={!!detail.user?.[field]}
                      disabled={!!toggling[field]}
                      onCheckedChange={() => toggleFeature(field, !!detail.user?.[field])}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Trial controls */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Probezeit
              </h4>
              <div className="rounded-xl border border-border p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Status</span>
                  {detail.user?.is_permanent
                    ? <span className="text-amber-400 flex items-center gap-1"><Crown className="w-3 h-3" />Permanent</span>
                    : detail.user?.trial_ends_at
                    ? (() => {
                        const d = Math.max(0, Math.floor((new Date(detail.user.trial_ends_at) - Date.now()) / 86400000));
                        return d > 0
                          ? <span className="text-emerald-400">{d} Tage verbleibend</span>
                          : <span className="text-red-400">Abgelaufen</span>;
                      })()
                    : <span className="text-muted-foreground">Kein Trial</span>
                  }
                </div>
                {detail.user?.trial_ends_at && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Endet am</span>
                    <span>{new Date(detail.user.trial_ends_at).toLocaleDateString("de-DE")}</span>
                  </div>
                )}
                {!!detail.user?.trial_extensions_count && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Verlängerungen</span>
                    <span>{detail.user.trial_extensions_count}×</span>
                  </div>
                )}
                <div className="flex gap-1.5 pt-1 flex-wrap">
                  <button onClick={() => doTrialAction("extend")} disabled={!!trialAction}
                    className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-50 transition-colors">
                    {trialAction === "extend" ? <div className="w-3 h-3 border border-t-transparent border-emerald-400 rounded-full animate-spin" /> : <RefreshCcw className="w-3 h-3" />}
                    +30 Tage
                  </button>
                  <button onClick={() => doTrialAction("permanent")} disabled={!!trialAction || detail.user?.is_permanent}
                    className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-amber-500/30 text-amber-400 hover:bg-amber-500/10 disabled:opacity-50 transition-colors">
                    {trialAction === "permanent" ? <div className="w-3 h-3 border border-t-transparent border-amber-400 rounded-full animate-spin" /> : <Crown className="w-3 h-3" />}
                    Permanent
                  </button>
                  <button onClick={() => doTrialAction("revoke")} disabled={!!trialAction}
                    className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 transition-colors">
                    {trialAction === "revoke" ? <div className="w-3 h-3 border border-t-transparent border-red-400 rounded-full animate-spin" /> : <Lock className="w-3 h-3" />}
                    Sperren
                  </button>
                </div>
              </div>
            </div>

            {/* Recommendation */}
            {detail.recommendation && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 flex gap-2">
                <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-200/80">{detail.recommendation}</p>
              </div>
            )}

            {/* Access requests */}
            {detail.access_requests?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Zugriffsanfragen</h4>
                <div className="space-y-1.5">
                  {detail.access_requests.map(r => (
                    <div key={r.id} className="flex items-center gap-2 text-xs rounded-lg border border-border px-3 py-2">
                      <span className="flex-1 text-muted-foreground">{r.feature_label}</span>
                      <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                        r.status === "approved" ? "bg-emerald-500/15 text-emerald-400" :
                        r.status === "rejected" ? "bg-red-500/15 text-red-400" :
                        "bg-amber-500/15 text-amber-400"}`}>
                        {r.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="p-6 text-center text-muted-foreground text-sm">Keine Daten</p>
        )}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────
export default function AdminAnalyticsPage() {
  const { token } = useAuth();
  const [overview, setOverview] = useState(null);
  const [trialOverview, setTrialOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [sortCol, setSortCol] = useState("score");
  const [sortAsc, setSortAsc] = useState(false);
  const [detailUserId, setDetailUserId] = useState(null);
  const [processingReq, setProcessingReq] = useState({});

  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    try {
      const [ov, us, rq, tr] = await Promise.all([
        axios.get(`${API}/admin/analytics/overview`, { headers }),
        axios.get(`${API}/admin/analytics/users`, { headers }),
        axios.get(`${API}/admin/access-requests?status=pending`, { headers }),
        axios.get(`${API}/admin/trials/overview`, { headers }),
      ]);
      setOverview(ov.data);
      setUsers(us.data);
      setRequests(rq.data);
      setTrialOverview(tr.data);
    } catch {
      toast.error("Fehler beim Laden der Analytics");
    } finally {
      setLoading(false);
    }
  }, [token]); // eslint-disable-line

  useEffect(() => { load(); }, [load]);

  const handleRequest = async (reqId, newStatus, note = "") => {
    setProcessingReq(p => ({ ...p, [reqId]: true }));
    try {
      await axios.patch(`${API}/admin/access-requests/${reqId}`,
        { status: newStatus, admin_note: note }, { headers });
      setRequests(prev => prev.filter(r => r.id !== reqId));
      setOverview(prev => prev ? { ...prev, pending_requests: Math.max(0, (prev.pending_requests || 1) - 1) } : prev);
      toast.success(newStatus === "approved" ? "Zugang freigeschaltet" : "Anfrage abgelehnt");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    } finally {
      setProcessingReq(p => ({ ...p, [reqId]: false }));
    }
  };

  const toggleSort = (col) => {
    if (sortCol === col) setSortAsc(p => !p);
    else { setSortCol(col); setSortAsc(false); }
  };

  const filtered = users
    .filter(u => {
      if (tierFilter !== "all" && u.tier !== tierFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
      }
      return true;
    })
    .sort((a, b) => {
      const av = a[sortCol] ?? 0, bv = b[sortCol] ?? 0;
      return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
    });

  const SortIcon = ({ col }) => sortCol === col
    ? (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)
    : null;

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-10 h-10 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10">
            <BarChart3 className="w-5 h-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Analytics</h1>
            <p className="text-sm text-muted-foreground">Nutzerverhalten & Zugriffsanfragen</p>
          </div>
        </div>
        <Link to="/admin">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="w-4 h-4" /> Admin
          </Button>
        </Link>
      </div>

      {/* Overview cards */}
      {overview && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: "Nutzer gesamt", val: overview.total_users, icon: Users, color: "text-blue-400" },
            { label: "Aktiv (7 Tage)", val: overview.active_7d, icon: Activity, color: "text-emerald-400" },
            { label: "Neu heute", val: overview.new_today, icon: Star, color: "text-amber-400" },
            { label: "Ausstehend", val: overview.pending_requests, icon: Clock, color: "text-orange-400" },
            { label: "Fragen in DB", val: overview.total_questions_db, icon: BookOpen, color: "text-purple-400" },
          ].map(({ label, val, icon: Icon, color }) => (
            <div key={label} className="glass-card rounded-xl p-4 text-center">
              <Icon className={`w-5 h-5 mx-auto mb-1 ${color}`} />
              <div className="text-2xl font-bold">{val ?? "–"}</div>
              <div className="text-xs text-muted-foreground">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Trial overview */}
      {trialOverview && (
        <div className="glass-card rounded-2xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Crown className="w-4 h-4 text-amber-400" /> Probezeit Übersicht
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Aktive Probezeit", val: trialOverview.active, icon: Activity, color: "text-emerald-400", bg: "bg-emerald-500/10" },
              { label: "Endet diese Woche", val: trialOverview.expiring_this_week, icon: Clock, color: "text-amber-400", bg: "bg-amber-500/10" },
              { label: "Abgelaufen", val: trialOverview.expired, icon: X, color: "text-red-400", bg: "bg-red-500/10" },
              { label: "Permanente", val: trialOverview.permanent, icon: Crown, color: "text-amber-400", bg: "bg-amber-500/10" },
            ].map(({ label, val, icon: Icon, color, bg }) => (
              <div key={label} className="rounded-xl border border-border p-4 text-center">
                <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center mx-auto mb-2`}>
                  <Icon className={`w-4 h-4 ${color}`} />
                </div>
                <div className="text-2xl font-bold">{val ?? "–"}</div>
                <div className="text-xs text-muted-foreground">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending requests */}
      {requests.length > 0 && (
        <div className="glass-card rounded-2xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-orange-400" />
            Ausstehende Anfragen
            <span className="ml-1 px-2 py-0.5 rounded-full text-xs bg-orange-500/15 text-orange-400">{requests.length}</span>
          </h2>
          <div className="space-y-2">
            {requests.map(req => (
              <div key={req.id} className="flex items-center gap-3 rounded-xl border border-border p-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">
                  {(req.user_name || "?")[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {req.user_name}
                    <span className="text-xs text-muted-foreground">→ {req.feature_label}</span>
                  </div>
                  {req.user_message && (
                    <p className="text-xs text-muted-foreground truncate">{req.user_message}</p>
                  )}
                  <p className="text-[10px] text-muted-foreground/60">
                    {new Date(req.requested_at).toLocaleString("de-DE")}
                  </p>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <Button size="sm" className="h-7 px-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs gap-1"
                    disabled={!!processingReq[req.id]}
                    onClick={() => handleRequest(req.id, "approved")}>
                    <Check className="w-3 h-3" /> Genehmigen
                  </Button>
                  <Button size="sm" variant="destructive" className="h-7 px-3 text-xs gap-1"
                    disabled={!!processingReq[req.id]}
                    onClick={() => handleRequest(req.id, "rejected")}>
                    <X className="w-3 h-3" /> Ablehnen
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top 3 users */}
      {users.length > 0 && (
        <div className="glass-card rounded-2xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Star className="w-4 h-4 text-amber-400" /> Top-Nutzer
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {users.slice(0, 3).map((u, i) => (
              <button key={u.id} onClick={() => setDetailUserId(u.id)}
                className="text-left rounded-xl border border-border p-4 hover:border-amber-500/30 hover:bg-amber-500/5 transition-all">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg font-bold text-amber-500/60">#{i + 1}</span>
                  <TierBadge tier={u.tier} />
                </div>
                <div className="font-medium text-sm truncate">{u.name}</div>
                <div className="text-xs text-muted-foreground truncate mb-2">{u.email}</div>
                <ScoreBar score={u.score} />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* User table */}
      <div className="glass-card rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-400" />
            Alle Nutzer
            <span className="text-sm text-muted-foreground font-normal">({filtered.length})</span>
          </h2>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-8 h-8 w-48 text-sm" placeholder="Suchen…"
                value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <select value={tierFilter} onChange={e => setTierFilter(e.target.value)}
              className="h-8 px-2 rounded-lg border border-border bg-background text-sm">
              <option value="all">Alle Tiers</option>
              <option value="power">Power</option>
              <option value="active">Aktiv</option>
              <option value="casual">Casual</option>
              <option value="new">Neu</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="text-left py-2 px-2">Nutzer</th>
                <th className="text-left py-2 px-2 cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort("score")}>
                  <span className="flex items-center gap-1">Score <SortIcon col="score" /></span>
                </th>
                <th className="text-left py-2 px-2">Tier</th>
                <th className="text-left py-2 px-2 cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort("total_questions")}>
                  <span className="flex items-center gap-1">Fragen <SortIcon col="total_questions" /></span>
                </th>
                <th className="text-left py-2 px-2 cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort("accuracy")}>
                  <span className="flex items-center gap-1">Genau. <SortIcon col="accuracy" /></span>
                </th>
                <th className="text-left py-2 px-2 cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort("current_streak")}>
                  <span className="flex items-center gap-1">Streak <SortIcon col="current_streak" /></span>
                </th>
                <th className="text-left py-2 px-2">Features</th>
                <th className="text-left py-2 px-2 cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort("last_active")}>
                  <span className="flex items-center gap-1">Zuletzt aktiv <SortIcon col="last_active" /></span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id}
                  className="border-b border-border/40 hover:bg-white/2 cursor-pointer transition-colors"
                  onClick={() => setDetailUserId(u.id)}>
                  <td className="py-2.5 px-2">
                    <div className="font-medium truncate max-w-[140px]">{u.name}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-[140px]">{u.email}</div>
                  </td>
                  <td className="py-2.5 px-2 w-24">
                    <ScoreBar score={u.score} />
                  </td>
                  <td className="py-2.5 px-2"><TierBadge tier={u.tier} /></td>
                  <td className="py-2.5 px-2 tabular-nums">{u.total_questions}</td>
                  <td className="py-2.5 px-2 tabular-nums">{u.accuracy}%</td>
                  <td className="py-2.5 px-2 tabular-nums">{u.current_streak}d</td>
                  <td className="py-2.5 px-2">
                    <div className="flex gap-1">
                      {u.notebook_enabled && <span title="Notebook" className="text-[10px] px-1 rounded bg-emerald-500/15 text-emerald-400">N</span>}
                      {u.analyzer_enabled && <span title="Analyzer" className="text-[10px] px-1 rounded bg-blue-500/15 text-blue-400">A</span>}
                      {u.podcast_enabled  && <span title="Podcast"  className="text-[10px] px-1 rounded bg-purple-500/15 text-purple-400">P</span>}
                    </div>
                  </td>
                  <td className="py-2.5 px-2 text-xs text-muted-foreground">
                    {u.last_active
                      ? `${Math.floor((Date.now() - new Date(u.last_active)) / 86400000)}d`
                      : "–"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="py-8 text-center text-muted-foreground text-sm">Keine Nutzer gefunden</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* User detail modal */}
      {detailUserId && (
        <UserDetailModal
          userId={detailUserId}
          token={token}
          onClose={() => setDetailUserId(null)}
          onPermissionChange={load}
        />
      )}
    </div>
  );
}
