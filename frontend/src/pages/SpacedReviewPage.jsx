import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { RotateCcw, CheckCircle2, XCircle, ArrowRight, Loader2, Brain, Trophy, Flame } from "lucide-react";

export default function SpacedReviewPage() {
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };

  const [questions, setQuestions] = useState([]);
  const [stats, setStats] = useState(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedChoice, setSelectedChoice] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("loading"); // loading | intro | review | done

  useEffect(() => {
    if (!token) return;
    Promise.all([
      axios.get(`${API}/review/due?limit=20`, { headers }),
      axios.get(`${API}/review/stats`, { headers }),
    ]).then(([dueRes, statsRes]) => {
      const qs = (dueRes.data.questions || []).map(q => ({
        ...q,
        choices: q.choices?.length > 0 ? q.choices : (q.choices_de || []),
      }));
      setQuestions(qs);
      setStats(statsRes.data);
      setStage("intro");
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]); // eslint-disable-line

  const startReview = () => {
    if (questions.length === 0) return;
    setStage("review");
    setCurrentIdx(0);
    setScore({ correct: 0, total: 0 });
  };

  const submitAnswer = async (choiceId) => {
    if (submitted) return;
    setSelectedChoice(choiceId);
    setSubmitted(true);
    const q = questions[currentIdx];
    const isCorrect = q.choices?.some(c => c.id === choiceId && c.is_correct);
    const quality = isCorrect ? 4 : 1;
    setScore(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }));

    // Submit to SM-2
    try {
      await axios.post(`${API}/review/submit?question_id=${q.id}&quality=${quality}`, {}, { headers });
    } catch { /* */ }
  };

  const nextQuestion = () => {
    if (currentIdx + 1 >= questions.length) {
      setStage("done");
      return;
    }
    setCurrentIdx(prev => prev + 1);
    setSelectedChoice(null);
    setSubmitted(false);
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin" style={{ color: '#c9a84c' }} /></div>;

  const q = questions[currentIdx];
  const percentage = score.total > 0 ? Math.round(score.correct / score.total * 100) : 0;

  // Intro
  if (stage === "intro") {
    return (
      <div className="max-w-lg mx-auto px-4 py-12 text-center" data-testid="review-intro">
        <Brain className="w-16 h-16 mx-auto mb-4" style={{ color: '#c9a84c' }} />
        <h1 className="text-2xl font-bold mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
          Spaced <span style={{ color: '#c9a84c' }}>Repetition</span>
        </h1>
        <p className="text-muted-foreground mb-6">Wiederhole Fragen nach dem SM-2 Algorithmus</p>

        {stats && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="p-4 rounded-xl border border-border/30" style={{ background: 'rgba(201,168,76,0.03)' }}>
              <div className="text-2xl font-bold" style={{ color: '#c9a84c' }}>{stats.due_today}</div>
              <div className="text-xs text-muted-foreground">Heute fällig</div>
            </div>
            <div className="p-4 rounded-xl border border-border/30" style={{ background: 'rgba(201,168,76,0.03)' }}>
              <div className="text-2xl font-bold">{stats.total_cards}</div>
              <div className="text-xs text-muted-foreground">Gesamt</div>
            </div>
            <div className="p-4 rounded-xl border border-emerald-500/20" style={{ background: 'rgba(16,185,129,0.03)' }}>
              <div className="text-2xl font-bold text-emerald-500">{stats.mastered}</div>
              <div className="text-xs text-muted-foreground">Gemeistert</div>
            </div>
          </div>
        )}

        {questions.length > 0 ? (
          <Button onClick={startReview} className="gap-2" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="start-review-btn">
            <RotateCcw className="w-4 h-4" /> {questions.length} Fragen wiederholen
          </Button>
        ) : (
          <div className="p-6 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-sm text-emerald-400">Keine Fragen fällig! Alles aufgearbeitet.</p>
            <Link to="/dashboard" className="text-xs text-muted-foreground hover:underline mt-2 block">Zurück zum Dashboard</Link>
          </div>
        )}
      </div>
    );
  }

  // Done
  if (stage === "done") {
    return (
      <div className="max-w-lg mx-auto px-4 py-12 text-center" data-testid="review-done">
        <Trophy className="w-14 h-14 mx-auto mb-4" style={{ color: '#c9a84c' }} />
        <div className="text-5xl font-bold mb-2" style={{ color: '#c9a84c' }}>{percentage}%</div>
        <p className="text-muted-foreground mb-6">{score.correct} von {score.total} richtig</p>
        <div className="flex gap-3 justify-center">
          <Link to="/dashboard"><Button variant="outline" className="gap-2">Dashboard</Button></Link>
          <Button onClick={() => window.location.reload()} className="gap-2" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
            <RotateCcw className="w-4 h-4" /> Weiter üben
          </Button>
        </div>
      </div>
    );
  }

  // Review quiz
  if (!q) return null;
  return (
    <div className="max-w-2xl mx-auto px-4 py-8" data-testid="review-quiz">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <RotateCcw size={16} style={{ color: '#c9a84c' }} />
          <span className="text-sm text-muted-foreground font-mono">Wiederholung {currentIdx + 1}/{questions.length}</span>
        </div>
        <span className="text-sm font-medium" style={{ color: '#c9a84c' }}>{score.correct} richtig</span>
      </div>
      {q.sr_interval && (
        <div className="mb-3 text-xs text-muted-foreground/60">
          Intervall: {q.sr_interval} Tage | Wiederholungen: {q.sr_repetitions}
        </div>
      )}
      <div className="p-6 rounded-xl border border-border/30 mb-6" style={{ background: 'rgba(201,168,76,0.03)' }}>
        <p className="text-base leading-relaxed">{q.question_text_de || q.question_text}</p>
      </div>
      <div className="space-y-3">
        {(q.choices || []).map(c => {
          let style = "border-border/30 hover:border-[#c9a84c]/40";
          if (submitted && c.is_correct) style = "border-emerald-500/50 bg-emerald-500/10";
          else if (submitted && c.id === selectedChoice && !c.is_correct) style = "border-red-500/50 bg-red-500/10";
          return (
            <button key={c.id} onClick={() => submitAnswer(c.id)} disabled={submitted}
              className={`w-full text-left p-4 rounded-xl border transition-all ${style}`}>
              <div className="flex items-center gap-3">
                {submitted && c.is_correct && <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />}
                {submitted && c.id === selectedChoice && !c.is_correct && <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />}
                <span className="text-sm">{c.text_de || c.text}</span>
              </div>
            </button>
          );
        })}
      </div>
      {submitted && q.explanation_de && (
        <div className="mt-4 p-4 rounded-xl border border-border/20 bg-muted/20 text-sm text-muted-foreground">{q.explanation_de}</div>
      )}
      {submitted && (
        <Button onClick={nextQuestion} className="w-full mt-4 gap-2" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
          {currentIdx + 1 >= questions.length ? "Ergebnis" : "Weiter"} <ArrowRight className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}
