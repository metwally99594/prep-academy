import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  XCircle,
  ArrowRight,
  Loader2,
  GraduationCap,
  LogIn,
  UserPlus,
  Scissors,
  Heart,
  Baby,
  Ambulance,
  Eye,
  Fingerprint,
  Ear,
  HeartPulse,
  Brain,
  Star,
  Activity,
  Pill,
  BookOpen,
} from "lucide-react";

const iconMap = {
  Scissors,
  Heart,
  Baby,
  Ambulance,
  Eye,
  Fingerprint,
  Ear,
  HeartPulse,
  Brain,
  Star,
  Activity,
  Pill,
};

export default function GuestQuizPage() {
  const navigate = useNavigate();
  const [specialties, setSpecialties] = useState([]);
  const [selectedSpec, setSelectedSpec] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedChoice, setSelectedChoice] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("select"); // select | quiz | done

  useEffect(() => {
    axios.get(`${API}/guest/specialties`).then(r => setSpecialties(r.data)).catch(() => {});
  }, []);

  const startQuiz = async (specId) => {
    setLoading(true);
    setSelectedSpec(specId);
    try {
      const res = await axios.get(`${API}/guest/questions?specialty_id=${specId}&count=5`);
      setQuestions(res.data);
      setStage("quiz");
      setCurrentIdx(0);
      setScore({ correct: 0, total: 0 });
    } catch { /* */ }
    finally { setLoading(false); }
  };

  const submitAnswer = (choiceId) => {
    if (submitted) return;
    setSelectedChoice(choiceId);
    setSubmitted(true);
    const q = questions[currentIdx];
    const isCorrect = q.choices?.some(c => c.id === choiceId && c.is_correct);
    setScore(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }));
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

  const q = questions[currentIdx];
  const percentage = score.total > 0 ? Math.round(score.correct / score.total * 100) : 0;
  const totalGuestQuestions = specialties.reduce((sum, s) => sum + (s.question_count || 0), 0);

  // Select specialty
  if (stage === "select") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12" data-testid="guest-quiz-select">
        <div className="text-center mb-10">
          <GraduationCap className="w-12 h-12 mx-auto mb-3" style={{ color: '#3b82f6' }} />
          <h1 className="text-3xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>
            Kostenlos <span style={{ color: '#3b82f6' }}>testen</span>
          </h1>
          <p className="text-muted-foreground mt-2">5 Fragen kostenlos - ohne Anmeldung</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {specialties.map(s => {
            const Icon = iconMap[s.icon] || BookOpen;
            return (
              <button key={s.id} onClick={() => startQuiz(s.id)} disabled={loading}
                className="p-4 rounded-xl border border-border/30 hover:border-[#3b82f6]/40 transition-all text-left group"
                style={{ background: 'rgba(59, 130, 246, 0.03)' }}
                data-testid={`guest-spec-${s.id}`}>
                <Icon className="w-5 h-5 mb-3 transition-colors group-hover:text-[#3b82f6]" style={{ color: '#3b82f6' }} aria-hidden="true" />
                <div className="font-medium text-sm">{s.name_de}</div>
                <div className="text-xs text-muted-foreground">{s.question_count} Fragen</div>
              </button>
            );
          })}
        </div>
        {loading && <div className="flex justify-center mt-8"><Loader2 className="animate-spin" style={{ color: '#3b82f6' }} /></div>}
      </div>
    );
  }

  // Quiz done
  if (stage === "done") {
    return (
      <div className="max-w-lg mx-auto px-4 py-12 text-center" data-testid="guest-quiz-done">
        <div className="text-6xl font-bold mb-2" style={{ color: '#3b82f6' }}>{percentage}%</div>
        <p className="text-lg mb-1">{score.correct} von {score.total} richtig</p>
        <p className="text-muted-foreground mb-8">
          {percentage >= 80 ? "Ausgezeichnet!" : percentage >= 60 ? "Gut gemacht!" : "Weiter üben!"}
        </p>
        <div className="p-6 rounded-xl border border-[#3b82f6]/20 mb-6" style={{ background: 'rgba(59,130,246,0.05)' }}>
          <h3 className="font-semibold mb-2">Registriere dich kostenlos für:</h3>
          <ul className="text-sm text-muted-foreground space-y-1 text-left max-w-xs mx-auto">
            <li>+ {totalGuestQuestions > 0 ? totalGuestQuestions.toLocaleString('de-DE') : "alle verfügbaren"} Prüfungsfragen</li>
            <li>+ 250-Fragen Examsimulation</li>
            <li>+ KI-Tutor & PDF-Notebook</li>
            <li>+ Fortschritt & Statistiken</li>
            <li>+ Lernkarten & Audio-Podcasts</li>
          </ul>
        </div>
        <div className="flex gap-3 justify-center">
          <Button onClick={() => navigate("/register")} className="gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="guest-register-btn">
            <UserPlus className="w-4 h-4" /> Kostenlos registrieren
          </Button>
          <Button onClick={() => navigate("/login")} variant="outline" className="gap-2" data-testid="guest-login-btn">
            <LogIn className="w-4 h-4" /> Anmelden
          </Button>
        </div>
        <button onClick={() => { setStage("select"); setQuestions([]); }} className="text-sm text-muted-foreground mt-4 hover:underline">
          Nochmal versuchen
        </button>
      </div>
    );
  }

  // Quiz in progress
  if (!q) return null;
  return (
    <div className="max-w-2xl mx-auto px-4 py-8" data-testid="guest-quiz-active">
      <div className="flex items-center justify-between mb-6">
        <span className="text-sm text-muted-foreground font-mono">Frage {currentIdx + 1} / {questions.length}</span>
        <span className="text-sm font-medium" style={{ color: '#3b82f6' }}>{score.correct} richtig</span>
      </div>
      <div className="p-6 rounded-xl border border-border/30 mb-6" style={{ background: 'rgba(59, 130, 246, 0.03)' }}>
        <p className="text-base leading-relaxed">{q.question_text_de || q.question_text}</p>
      </div>
      <div className="space-y-3">
        {(q.choices || []).map(c => {
          let style = "border-border/30 hover:border-[#3b82f6]/40";
          if (submitted && c.is_correct) style = "border-emerald-500/50 bg-emerald-500/10";
          else if (submitted && c.id === selectedChoice && !c.is_correct) style = "border-red-500/50 bg-red-500/10";
          else if (!submitted && c.id === selectedChoice) style = "border-[#3b82f6]/50 bg-[#3b82f6]/5";
          return (
            <button key={c.id} onClick={() => submitAnswer(c.id)} disabled={submitted}
              className={`w-full text-left p-4 rounded-xl border transition-all ${style}`}
              data-testid={`guest-choice-${c.id}`}>
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
        <div className="mt-4 p-4 rounded-xl border border-border/20 bg-muted/20 text-sm text-muted-foreground">
          {q.explanation_de}
        </div>
      )}
      {submitted && (
        <Button onClick={nextQuestion} className="w-full mt-4 gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="guest-next-btn">
          {currentIdx + 1 >= questions.length ? "Ergebnis anzeigen" : "Nächste Frage"} <ArrowRight className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}
