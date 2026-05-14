import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Calendar as CalendarWidget } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { 
  BookOpen, 
  Trophy, 
  Flame,
  Target,
  TrendingUp,
  Clock,
  Award,
  Play,
  Zap,
  CalendarDays,
  X,
  Star,
  Crown,
  Shield,
  Users,
  Swords,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Share2,
  MessageCircle,
  RotateCcw,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

const BADGE_ICONS = {
  Zap, BookOpen, Library: BookOpen, Crown, Trophy, Flame, Target, Star, Award, Shield,
};

export default function DashboardPage() {
  const { user, token } = useAuth();
  const [stats, setStats] = useState(null);
  const [weeklyActivity, setWeeklyActivity] = useState([]);
  const [gamification, setGamification] = useState(null);
  const [examDateOpen, setExamDateOpen] = useState(false);
  const [selectedExamDate, setSelectedExamDate] = useState(null);
  const [weaknessMap, setWeaknessMap] = useState(null);
  const [percentile, setPercentile] = useState(null);
  const [challengeLoading, setChallengeLoading] = useState(false);
  const [challengeCount, setChallengeCount] = useState(10);
  const [challengeSpec, setChallengeSpec] = useState("");
  const [challengeCity, setChallengeCity] = useState("");
  const [challengeYear, setChallengeYear] = useState("");
  const [challengeAll, setChallengeAll] = useState(false);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      axios.get(`${API}/dashboard/stats`, { headers }),
      axios.get(`${API}/dashboard/weekly-activity`, { headers }),
      axios.get(`${API}/gamification/profile`, { headers }),
      axios.get(`${API}/dashboard/weakness-map`, { headers }).catch(() => ({ data: null })),
      axios.get(`${API}/dashboard/percentile`, { headers }).catch(() => ({ data: null })),
    ]).then(([statsRes, activityRes, gamRes, wmRes, pRes]) => {
      setStats(statsRes.data);
      setWeeklyActivity(activityRes.data);
      setGamification(gamRes.data);
      setWeaknessMap(wmRes.data);
      setPercentile(pRes.data);
    }).catch(error => {
      console.error("Failed to fetch dashboard data:", error);
    });
  }, [token]);

  const getDaysUntilExam = () => {
    const dateToUse = selectedExamDate || (stats?.exam_date ? new Date(stats.exam_date) : null);
    if (!dateToUse) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const examDate = new Date(dateToUse);
    examDate.setHours(0, 0, 0, 0);
    const diffDays = Math.ceil((examDate - today) / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  };

  useEffect(() => {
    if (stats?.exam_date && !selectedExamDate) {
      const d = new Date(stats.exam_date);
      if (!isNaN(d.getTime())) setSelectedExamDate(d);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats]);

  const handleExamDateSelect = async (date) => {
    if (!date) return;
    setSelectedExamDate(date);
    setExamDateOpen(false);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/dashboard/settings`, null, {
        headers, params: { exam_date: date.toISOString().split('T')[0] }
      });
    } catch (error) { console.error("Failed to save exam date:", error); }
  };

  const handleClearExamDate = async (e) => {
    e.stopPropagation();
    setSelectedExamDate(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/dashboard/settings`, null, { headers, params: { exam_date: "" } });
    } catch (error) { console.error("Failed to clear exam date:", error); }
  };

  const daysUntilExam = getDaysUntilExam();
  const weeklyTotal = weeklyActivity.reduce((sum, day) => sum + day.questions, 0);
  const level = gamification?.level;
  const xp = gamification?.xp || 0;
  const badges = gamification?.badges || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* XP & Level Hero Card */}
      <div className="glass-card rounded-2xl p-6 mb-8 bg-gradient-to-r from-primary/10 via-purple-500/5 to-amber-500/5 border-primary/20" data-testid="xp-hero-card">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-lg">
                <span className="text-2xl font-bold text-white">{level?.level || 1}</span>
              </div>
              <div className="absolute -bottom-1 -right-1 px-1.5 py-0.5 bg-amber-500 rounded-full text-[10px] font-bold text-white">
                LVL
              </div>
            </div>
            <div>
              <h2 className="text-xl font-bold" data-testid="level-name">{level?.name_de || "Praktikant"}</h2>
              <p className="text-sm text-muted-foreground">
                {xp.toLocaleString()} XP {level?.next_level_xp ? `/ ${level.next_level_xp.toLocaleString()} XP` : '(Max)'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-center" data-testid="rank-display">
              <div className="text-2xl font-bold text-amber-500">#{gamification?.rank || '—'}</div>
              <div className="text-xs text-muted-foreground">Rang</div>
            </div>
            <div className="text-center" data-testid="streak-display">
              <div className="flex items-center gap-1 justify-center">
                <Flame className="w-5 h-5 text-orange-500" />
                <span className="text-2xl font-bold">{gamification?.streak || 0}</span>
              </div>
              <div className="text-xs text-muted-foreground">Tage Serie</div>
            </div>
            <Link to="/leaderboard">
              <Button variant="outline" size="sm" className="gap-2" data-testid="leaderboard-btn">
                <Users className="w-4 h-4" />
                Rangliste
              </Button>
            </Link>
            <Link to="/spaced-review">
              <Button variant="outline" size="sm" className="gap-2 border-[#c9a84c]/30 text-[#c9a84c] hover:bg-[#c9a84c]/10" data-testid="spaced-review-btn">
                <RotateCcw className="w-4 h-4" />
                Wiederholung
              </Button>
            </Link>
          </div>
        </div>

        {/* XP Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Level {level?.level || 1}</span>
            <span>{level?.progress_percent || 0}%</span>
            {level?.next_level_xp && <span>Level {(level?.level || 0) + 1}</span>}
          </div>
          <div className="h-3 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${level?.progress_percent || 0}%` }}
              data-testid="xp-progress-bar"
            />
          </div>
        </div>
      </div>

      {/* Top Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Popover open={examDateOpen} onOpenChange={setExamDateOpen}>
          <PopoverTrigger asChild>
            <div className="glass-card rounded-2xl p-5 flex items-center gap-4 cursor-pointer hover:ring-2 hover:ring-blue-500/40 transition-all" data-testid="exam-countdown">
              <div className="p-3 rounded-xl bg-blue-500/20">
                <CalendarDays className="w-6 h-6 text-blue-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-2xl font-bold">{daysUntilExam ?? '—'}</div>
                <div className="text-sm text-muted-foreground">{daysUntilExam !== null ? 'Tage bis Prüfung' : 'Datum setzen'}</div>
                {selectedExamDate && (
                  <div className="text-xs text-blue-400 mt-0.5">
                    {selectedExamDate.toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                  </div>
                )}
              </div>
              {selectedExamDate && (
                <button onClick={handleClearExamDate} className="p-1 rounded-full hover:bg-red-500/20 transition-colors" data-testid="clear-exam-date">
                  <X className="w-4 h-4 text-red-400" />
                </button>
              )}
            </div>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <CalendarWidget mode="single" selected={selectedExamDate} onSelect={handleExamDateSelect} disabled={(date) => date < new Date()} initialFocus />
          </PopoverContent>
        </Popover>

        <div className="glass-card rounded-2xl p-5 flex items-center gap-4" data-testid="readiness-card">
          <div className="p-3 rounded-xl bg-emerald-500/20">
            <Target className="w-6 h-6 text-emerald-500" />
          </div>
          <div>
            <div className="text-2xl font-bold">{stats?.readiness || 0}%</div>
            <div className="text-sm text-muted-foreground">Prüfungsbereit</div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 flex items-center gap-4" data-testid="accuracy-card">
          <div className="p-3 rounded-xl bg-purple-500/20">
            <Zap className="w-6 h-6 text-purple-500" />
          </div>
          <div>
            <div className="text-2xl font-bold">{stats?.accuracy || 0}%</div>
            <div className="text-sm text-muted-foreground">Genauigkeit</div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 flex items-center gap-4" data-testid="total-answered-card">
          <div className="p-3 rounded-xl bg-primary/20">
            <BookOpen className="w-6 h-6 text-primary" />
          </div>
          <div>
            <div className="text-2xl font-bold">{stats?.total_answered || 0}</div>
            <div className="text-sm text-muted-foreground">Beantwortet</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Weekly Activity */}
          <div className="glass-card rounded-2xl p-6" data-testid="weekly-activity">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Wochenaktivität
            </h2>
            <div className="grid grid-cols-7 gap-2">
              {weeklyActivity.map((day, index) => (
                <div key={index} className="text-center" data-testid={`activity-day-${index}`}>
                  <div className="text-xs text-muted-foreground mb-2">{day.day}</div>
                  <div className={`aspect-square rounded-xl flex flex-col items-center justify-center p-2 ${day.questions > 0 ? 'bg-primary/20 border border-primary/30' : 'bg-muted'}`}>
                    <div className="text-lg font-bold">{day.questions}</div>
                    <div className="text-xs text-muted-foreground">Fragen</div>
                  </div>
                  {day.questions > 0 && (
                    <div className={`text-xs mt-1 font-medium ${day.accuracy >= 80 ? 'text-emerald-500' : day.accuracy >= 60 ? 'text-amber-500' : 'text-red-500'}`}>
                      {day.accuracy}%
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Gesamt: <strong>{weeklyTotal} Fragen</strong></span>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Ziel: {stats?.weekly_goal || 250}</span>
                <Progress value={(weeklyTotal / (stats?.weekly_goal || 250)) * 100} className="w-24 h-2" />
              </div>
            </div>
          </div>

          {/* Progress by Module */}
          <div className="glass-card rounded-2xl p-6" data-testid="module-progress">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              Fortschritt nach Modul
            </h2>
            <div className="space-y-4">
              {stats?.specialty_progress?.filter(s => s.total_questions > 0).slice(0, 8).map((spec) => (
                <Link key={spec.id} to={`/specialty/${spec.id}`} className="block hover:bg-muted/50 rounded-xl p-3 -mx-3 transition-colors" data-testid={`module-${spec.id}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{spec.name_de}</span>
                    <span className="text-sm text-muted-foreground">{spec.answered}/{spec.total_questions}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Progress value={spec.progress} className="flex-1 h-2" />
                    <span className="text-sm font-medium w-12 text-right">{spec.progress}%</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="glass-card rounded-2xl p-6" data-testid="quick-actions">
            <h2 className="text-lg font-semibold mb-4">Schnellzugriff</h2>
            <div className="space-y-3">
              <Link to="/exam-simulation">
                <Button className="w-full justify-start gap-2 bg-primary/10 text-primary hover:bg-primary/20">
                  <Clock className="w-4 h-4" /> Prüfungssimulation
                </Button>
              </Link>
              <Link to="/review">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Play className="w-4 h-4" /> Überprüfung
                </Button>
              </Link>
              <Link to="/leaderboard">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Trophy className="w-4 h-4" /> Rangliste
                </Button>
              </Link>
            </div>
          </div>

          {/* Badges */}
          <div className="glass-card rounded-2xl p-6" data-testid="badges-section">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-500" />
              Abzeichen ({badges.length})
            </h2>
            {badges.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground text-sm">
                <Shield className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p>Beantworte Fragen, um Abzeichen zu verdienen!</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {badges.map((badge) => {
                  const IconComp = BADGE_ICONS[badge.icon] || Award;
                  return (
                    <div key={badge.id} className={`p-3 rounded-xl bg-${badge.color}-500/10 border border-${badge.color}-500/20 text-center`} data-testid={`badge-${badge.id}`}>
                      <IconComp className={`w-6 h-6 mx-auto mb-1 text-${badge.color}-500`} />
                      <div className="text-xs font-medium truncate">{badge.name}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Stats Summary */}
          <div className="glass-card rounded-2xl p-6" data-testid="stats-summary">
            <h2 className="text-lg font-semibold mb-4">Statistik</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">XP Gesamt</span>
                <span className="font-semibold text-primary">{xp.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Beantwortet</span>
                <span className="font-semibold">{stats?.total_answered || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Richtig</span>
                <span className="font-semibold text-emerald-500">{stats?.total_correct || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Falsch</span>
                <span className="font-semibold text-red-500">{stats?.total_wrong || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Längste Serie</span>
                <span className="font-semibold">{gamification?.longest_streak || 0} Tage</span>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ WEAKNESS MAP ═══ */}
        {weaknessMap && weaknessMap.specialties?.length > 0 && (
          <div className="glass-card rounded-2xl p-6" data-testid="weakness-map">
            <h3 className="font-semibold text-base mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" style={{ color: '#c9a84c' }} /> Stärken & Schwächen
            </h3>
            <div className="space-y-3">
              {weaknessMap.specialties.map(s => (
                <div key={s.id} className="flex items-center gap-3">
                  <span className="text-sm w-28 truncate">{s.name_de}</span>
                  <div className="flex-1 h-3 rounded-full bg-muted/30 overflow-hidden">
                    <div className="h-full rounded-full transition-all"
                      style={{
                        width: `${s.accuracy}%`,
                        background: s.level === 'strong' ? '#10b981' : s.level === 'medium' ? '#f59e0b' : '#ef4444',
                      }} />
                  </div>
                  <span className="text-xs font-mono w-12 text-right" style={{
                    color: s.level === 'strong' ? '#10b981' : s.level === 'medium' ? '#f59e0b' : '#ef4444',
                  }}>{s.accuracy}%</span>
                </div>
              ))}
            </div>
            {weaknessMap.weakest && (
              <div className="mt-4 p-3 rounded-xl border border-red-500/20 bg-red-500/5 flex items-center gap-3">
                <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <p className="text-xs text-red-400">
                  Schwächstes Fach: <strong>{weaknessMap.weakest.name_de}</strong> ({weaknessMap.weakest.accuracy}%) —
                  <Link to={`/quiz/${weaknessMap.weakest.id}`} className="underline ml-1">Jetzt üben</Link>
                </p>
              </div>
            )}
          </div>
        )}

        {/* ═══ PERCENTILE & PASS PROBABILITY ═══ */}
        {percentile && percentile.total_users > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="glass-card rounded-2xl p-6 text-center" data-testid="percentile-card">
              <Users className="w-8 h-8 mx-auto mb-2" style={{ color: '#c9a84c' }} />
              <div className="text-3xl font-bold" style={{ color: '#c9a84c' }}>{percentile.percentile}%</div>
              <p className="text-xs text-muted-foreground mt-1">Besser als {percentile.percentile}% der Nutzer</p>
              <p className="text-xs text-muted-foreground">Platz {percentile.rank} von {percentile.total_users}</p>
            </div>
            <div className="glass-card rounded-2xl p-6 text-center" data-testid="pass-probability-card">
              <Target className="w-8 h-8 mx-auto mb-2" style={{ color: percentile.pass_probability >= 70 ? '#10b981' : '#f59e0b' }} />
              <div className="text-3xl font-bold" style={{ color: percentile.pass_probability >= 70 ? '#10b981' : '#f59e0b' }}>
                {percentile.pass_probability}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">Bestehenswahrscheinlichkeit</p>
              <p className="text-xs text-muted-foreground">Genauigkeit: {percentile.accuracy}%</p>
            </div>
          </div>
        )}

        {/* ═══ CHALLENGE MODE ═══ */}
        <div className="glass-card rounded-2xl p-6" data-testid="challenge-section">
          <h3 className="font-semibold text-base mb-3 flex items-center gap-2">
            <Swords className="w-5 h-5" style={{ color: '#c9a84c' }} /> Freunde herausfordern
          </h3>
          <p className="text-sm text-muted-foreground mb-4">Erstelle eine Challenge - du bestimmst alles!</p>
          
          {/* Filters Row 1: Specialty + Count */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Fachgebiet</label>
              <select value={challengeSpec} onChange={e => setChallengeSpec(e.target.value)}
                className="w-full h-9 rounded-lg bg-muted/40 border border-border/40 px-2 text-sm" data-testid="challenge-spec-select">
                <option value="">Alle Fächer</option>
                {(stats?.specialty_progress || []).filter(s => s.total_questions > 0).map(s => (
                  <option key={s.id} value={s.id}>{s.name_de} ({s.total_questions})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Anzahl</label>
              <select value={challengeAll ? "all" : challengeCount} onChange={e => {
                if (e.target.value === "all") { setChallengeAll(true); } 
                else { setChallengeAll(false); setChallengeCount(parseInt(e.target.value)); }
              }}
                className="w-full h-9 rounded-lg bg-muted/40 border border-border/40 px-2 text-sm" data-testid="challenge-count-select">
                {[5, 10, 15, 20, 30, 50].map(n => <option key={n} value={n}>{n}</option>)}
                <option value="all">Alle Fragen</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Stadt</label>
              <select value={challengeCity} onChange={e => setChallengeCity(e.target.value)}
                className="w-full h-9 rounded-lg bg-muted/40 border border-border/40 px-2 text-sm" data-testid="challenge-city-select">
                <option value="">Alle Städte</option>
                <option value="vienna">Wien</option>
                <option value="innsbruck">Innsbruck</option>
                <option value="andere">Andere</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Jahr</label>
              <select value={challengeYear} onChange={e => setChallengeYear(e.target.value)}
                className="w-full h-9 rounded-lg bg-muted/40 border border-border/40 px-2 text-sm" data-testid="challenge-year-select">
                <option value="">Alle Jahre</option>
                {[2026, 2025, 2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </div>

          {/* Create Button */}
          <Button disabled={challengeLoading} className="w-full gap-2 mt-2"
            style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}
            onClick={async () => {
              setChallengeLoading(true);
              try {
                const params = new URLSearchParams();
                if (challengeSpec) params.set("specialty_id", challengeSpec);
                if (!challengeAll) params.set("count", challengeCount);
                if (challengeAll) params.set("all_questions", "true");
                if (challengeCity) params.set("exam_location", challengeCity);
                if (challengeYear) params.set("year", challengeYear);
                const res = await axios.post(`${API}/challenge/create?${params}`, {}, { headers: { Authorization: `Bearer ${token}` } });
                const link = `${window.location.origin}/challenge/${res.data.challenge_id}`;
                await navigator.clipboard.writeText(link);
                toast.success(`Challenge erstellt! ${res.data.count} Fragen | Link kopiert!`);
              } catch (e) { toast.error(e.response?.data?.detail || "Fehler beim Erstellen"); }
              finally { setChallengeLoading(false); }
            }}
            data-testid="create-challenge-btn">
            {challengeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Swords className="w-4 h-4" />}
            Challenge erstellen & Link kopieren
          </Button>
        </div>
      </div>
    </div>
  );
}
