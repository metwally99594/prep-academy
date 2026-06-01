import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, API } from "@/App";
import axios from "axios";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle, Brain, Target, Loader2,
  ArrowRight, RefreshCw, BookOpen, ListChecks, Play,
} from "lucide-react";
import { toast } from "sonner";

export default function WeaknessPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reviewQueue, setReviewQueue] = useState(null);
  const [queueLoading, setQueueLoading] = useState(true);
  const [startingReview, setStartingReview] = useState(false);

  useEffect(() => {
    loadProfile();
    loadReviewQueue();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const { data } = await axios.get(`${API}/tracker/profile`, { headers });
      setProfile(data);
    } catch { setProfile(null) }
    setLoading(false);
  };

  const loadReviewQueue = async () => {
    setQueueLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const { data } = await axios.get(`${API}/me/review-queue?limit=5`, { headers });
      setReviewQueue(data);
    } catch { setReviewQueue(null) }
    setQueueLoading(false);
  };

  const startMemoryReview = async () => {
    setStartingReview(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const { data } = await axios.post(`${API}/review/start`, { limit: 10 }, { headers });
      if (data.questions && data.questions.length > 0) {
        sessionStorage.setItem("customQuizQuestions", JSON.stringify(data.questions));
        const specs = Array.from(new Set((data.targeted_concepts || []).map(c => c.specialty_id).filter(Boolean))).join(",");
        navigate(`/quiz/custom?specs=${encodeURIComponent(specs)}&mode=study&limit=${data.questions.length}&review_session=${data.session_id}`);
      } else {
        toast.error("Keine Fragen für die Wiederholung verfügbar");
      }
    } catch (e) {
      toast.error("Fehler beim Starten der Wiederholung");
    }
    setStartingReview(false);
  };

  const generateReview = async () => {
    setGenerating(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const { data } = await axios.post(`${API}/tracker/review`, { limit: 20 }, { headers });
      const specs = data.focus_specialties?.join(",") || "";
      sessionStorage.setItem("customQuizQuestions", JSON.stringify(data.questions));
      navigate(`/quiz/custom?specs=${encodeURIComponent(specs)}&mode=study&limit=20`);
    } catch (e) {
      toast.error("Fehler beim Generieren der Überprüfung");
    }
    setGenerating(false);
  };

  const getColor = (pct) => {
    if (pct >= 80) return "text-green-400";
    if (pct >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const getBgColor = (pct) => {
    if (pct >= 80) return "bg-green-500/10 border-green-500/20";
    if (pct >= 60) return "bg-yellow-500/10 border-yellow-500/20";
    return "bg-red-500/10 border-red-500/20";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple-400" />
            Meine Schwächen
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Verfolge deine Fehler und verbessere dich gezielt
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadProfile}>
          <RefreshCw className="w-4 h-4 mr-1" />
          Aktualisieren
        </Button>
      </div>

      {!profile?.heatmap?.length ? (
        <div className="text-center py-16 text-muted-foreground">
          <Target className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p className="text-lg">Noch keine Daten vorhanden</p>
          <p className="text-sm mt-1">Beantworte ein paar Fragen, um deine Schwächen zu sehen</p>
          <Button className="mt-4" onClick={() => navigate("/custom-quiz")}>
            <BookOpen className="w-4 h-4 mr-2" />
            Quiz starten
          </Button>
        </div>
      ) : (
        <>
          {/* Review Queue (Memory Alpha-A) */}
          {!queueLoading && reviewQueue && reviewQueue.queue && reviewQueue.queue.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <ListChecks className="w-5 h-5 text-purple-400" />
                Review Queue
                <span className="text-xs font-normal text-muted-foreground ml-1">
                  ({reviewQueue.total_queue_size} schwache Konzepte)
                </span>
              </h2>
              <div className="space-y-2 mb-3">
                {reviewQueue.queue.slice(0, 5).map((q, i) => (
                  <div
                    key={q.ckey}
                    className="flex items-center justify-between p-3 rounded-lg border bg-purple-500/5 border-purple-500/20"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-sm font-bold text-purple-400 w-6 text-right">{i + 1}</span>
                      <div className="min-w-0">
                        <div className="font-medium truncate">{q.concept}</div>
                        <div className="text-xs text-muted-foreground capitalize">
                          {q.specialty_id} · wrong {q.wrong_count}× · streak {q.wrong_streak}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <Button
                onClick={startMemoryReview}
                disabled={startingReview}
                size="lg"
                className="w-full sm:w-auto"
              >
                {startingReview ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Practice Now (10 Fragen)
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </section>
          )}

          {/* Specialty Heatmap */}
          <section>
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Target className="w-5 h-5 text-orange-400" />
              Fachbereichs-Übersicht
            </h2>
            <div className="grid gap-2">
              {profile.heatmap.map((s) => {
                const score = s.percentage || 0;
                return (
                  <div
                    key={s.specialty_id}
                    className={`flex items-center justify-between p-3 rounded-lg border ${getBgColor(score)}`}
                  >
                    <div>
                      <span className="font-medium capitalize">{s.specialty_id}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {s.correct}/{s.total} richtig
                      </span>
                    </div>
                    <span className={`text-lg font-bold ${getColor(score)}`}>
                      {score.toFixed(0)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Repeated Mistakes */}
          {profile.repeated_mistakes?.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                Wiederholte Fehler
              </h2>
              <div className="space-y-2">
                {profile.repeated_mistakes.map((m, i) => (
                  <div key={i}
                    className="flex items-center justify-between p-3 rounded-lg border bg-red-500/5 border-red-500/20"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-red-400 w-8 text-right">{m.count}×</span>
                      <div>
                        <span className="font-medium">{m.concept}</span>
                        <span className="text-xs text-muted-foreground ml-2 capitalize">({m.specialty_id})</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Recent Wrong Answers */}
          {profile.recent_wrong?.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-400" />
                Letzte Fehler
              </h2>
              <div className="space-y-1 text-sm text-muted-foreground">
                {profile.recent_wrong.slice(0, 5).map((r, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <span className="text-red-400 shrink-0">✗</span>
                    <span className="capitalize">{r.specialty_id}</span>
                    {r.concepts?.length > 0 && (
                      <span className="truncate">— {r.concepts[0]}</span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Generate Review */}
          <div className="pt-2">
            <Button onClick={generateReview} disabled={generating} size="lg" className="w-full sm:w-auto">
              {generating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Brain className="w-4 h-4 mr-2" />
              )}
              Schwachstellen-Überprüfung starten
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
