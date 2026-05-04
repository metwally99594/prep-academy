import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, ArrowRight, Loader2, Swords, Trophy, Share2, MessageCircle, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import DragDrop from "@/components/questions/DragDrop";
import Luckentext from "@/components/questions/Luckentext";
import MultiSelect from "@/components/questions/MultiSelect";

export default function ChallengePage() {
  const { challengeId } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };

  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedChoice, setSelectedChoice] = useState(null);
  const [dragDropAnswer, setDragDropAnswer] = useState({});
  const [blankAnswer, setBlankAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitResult, setSubmitResult] = useState(null); // { is_correct }
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [stage, setStage] = useState("loading"); // loading | intro | quiz | done
  const [results, setResults] = useState([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!challengeId || !token) return;
    axios.get(`${API}/challenge/${challengeId}`, { headers })
      .then(r => {
        setChallenge(r.data);
        setResults(r.data.results || []);
        setStage(r.data.already_played ? "done" : "intro");
      })
      .catch(() => { toast.error("Challenge nicht gefunden"); navigate("/"); })
      .finally(() => setLoading(false));
  }, [challengeId, token]); // eslint-disable-line

  const startChallenge = () => {
    setStage("quiz");
    setCurrentIdx(0);
    setScore({ correct: 0, total: 0 });
    resetAnswerState();
  };

  const resetAnswerState = () => {
    setSelectedChoice(null);
    setDragDropAnswer({});
    setBlankAnswer("");
    setSubmitted(false);
    setSubmitResult(null);
  };

  const q = challenge?.questions?.[currentIdx];
  const qType = q?.question_type || 'single_choice';
  const isDragDrop = qType === 'drag_drop' || qType === 'kategorisierung';
  const isLuckentext = qType === 'luckentext';
  const isMultiSelect = qType === 'multi_select';

  // Called when user clicks a single-choice option
  const handleChoiceClick = (choiceId) => {
    if (submitted) return;
    if (isMultiSelect) {
      setSelectedChoice(prev => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.includes(choiceId) ? arr.filter(id => id !== choiceId) : [...arr, choiceId];
      });
    } else {
      handleSubmit(choiceId);
    }
  };

  const handleSubmit = (choiceIdOverride) => {
    if (submitted || !q) return;

    let isCorrect = false;
    let finalChoiceId = choiceIdOverride;

    if (isDragDrop) {
      const items = q.drag_drop_items || [];
      isCorrect = items.length > 0 && items.every(item => dragDropAnswer[item.id] === item.correct_category);
    } else if (isLuckentext) {
      const blanks = q.blank_answers || [];
      isCorrect = blanks.some(b => blankAnswer.trim().toLowerCase() === b.trim().toLowerCase());
    } else if (isMultiSelect) {
      const selected = Array.isArray(selectedChoice) ? selectedChoice : [];
      const correctIds = (q.choices || []).filter(c => c.is_correct).map(c => c.id);
      isCorrect = selected.length === correctIds.length && correctIds.every(id => selected.includes(id));
      finalChoiceId = selected;
    } else {
      isCorrect = q.choices?.some(c => c.id === finalChoiceId && c.is_correct) || false;
    }

    if (!isDragDrop && !isLuckentext && !isMultiSelect) {
      setSelectedChoice(finalChoiceId);
    }
    setSubmitResult({ is_correct: isCorrect });
    setSubmitted(true);
    setScore(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }));
  };

  const canConfirm = () => {
    if (isDragDrop) return Object.keys(dragDropAnswer).length > 0;
    if (isLuckentext) return blankAnswer.trim().length > 0;
    if (isMultiSelect) return Array.isArray(selectedChoice) && selectedChoice.length > 0;
    return false; // single_choice submits on click
  };

  const nextQuestion = async () => {
    if (currentIdx + 1 >= challenge.questions.length) {
      const finalScore = score;
      try {
        const res = await axios.post(
          `${API}/challenge/${challengeId}/submit?score=${finalScore.correct}&total=${finalScore.total}`,
          {}, { headers }
        );
        setResults(res.data.results || []);
      } catch { /* */ }
      setStage("done");
      return;
    }
    setCurrentIdx(prev => prev + 1);
    resetAnswerState();
  };

  const shareLink = `${window.location.origin}/challenge/${challengeId}`;
  const shareText = `Ich fordere dich heraus! ${challenge?.specialty_name || ''} Quiz mit ${challenge?.count || 0} Fragen auf Prep Academy.\n\n${shareLink}`;

  const copyLink = async () => {
    await navigator.clipboard.writeText(shareLink);
    setCopied(true);
    toast.success("Link kopiert!");
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin" style={{ color: '#c9a84c' }} /></div>;
  if (!challenge) return null;

  const percentage = score.total > 0 ? Math.round(score.correct / score.total * 100) : 0;
  const myResult = results.find(r => r.user_id === user?.id);

  // Intro
  if (stage === "intro") {
    return (
      <div className="max-w-lg mx-auto px-4 py-12 text-center" data-testid="challenge-intro">
        <Swords className="w-16 h-16 mx-auto mb-4" style={{ color: '#c9a84c' }} />
        <h1 className="text-2xl font-bold mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Challenge</h1>
        <p className="text-muted-foreground mb-6">
          <strong>{challenge.creator_name}</strong> fordert dich heraus!
        </p>
        <div className="p-4 rounded-xl border border-[#c9a84c]/20 mb-6" style={{ background: 'rgba(201,168,76,0.05)' }}>
          <div className="text-lg font-semibold">{challenge.specialty_name}</div>
          <div className="text-sm text-muted-foreground">{challenge.count} Fragen</div>
        </div>
        {results.length > 0 && (
          <div className="mb-6 space-y-2">
            <p className="text-xs text-muted-foreground font-mono">Bisherige Ergebnisse:</p>
            {results.map((r, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-muted/30 text-sm">
                <span>{r.user_name}</span>
                <span className="font-mono font-bold" style={{ color: '#c9a84c' }}>{r.accuracy}%</span>
              </div>
            ))}
          </div>
        )}
        <Button onClick={startChallenge} className="gap-2" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="start-challenge-btn">
          <Swords className="w-4 h-4" /> Challenge starten
        </Button>
      </div>
    );
  }

  // Done
  if (stage === "done") {
    const sortedResults = [...results].sort((a, b) => b.accuracy - a.accuracy);
    return (
      <div className="max-w-lg mx-auto px-4 py-12 text-center" data-testid="challenge-done">
        <Trophy className="w-14 h-14 mx-auto mb-4" style={{ color: '#c9a84c' }} />
        {myResult && (
          <>
            <div className="text-5xl font-bold mb-2" style={{ color: '#c9a84c' }}>{myResult.accuracy}%</div>
            <p className="text-muted-foreground mb-6">{myResult.score} von {myResult.total} richtig</p>
          </>
        )}
        <div className="mb-6 space-y-2">
          <h3 className="font-semibold text-sm mb-3">Rangliste</h3>
          {sortedResults.map((r, i) => (
            <div key={i} className={`flex items-center justify-between p-3 rounded-xl border ${r.user_id === user?.id ? 'border-[#c9a84c]/30' : 'border-border/20'}`}
              style={r.user_id === user?.id ? { background: 'rgba(201,168,76,0.05)' } : {}}>
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                  style={i === 0 ? { background: '#c9a84c', color: '#06081a' } : { background: 'rgba(255,255,255,0.1)' }}>
                  {i + 1}
                </span>
                <span className="text-sm font-medium">{r.user_name}</span>
              </div>
              <span className="font-mono font-bold" style={{ color: '#c9a84c' }}>{r.accuracy}%</span>
            </div>
          ))}
        </div>
        <div className="flex gap-2 justify-center">
          <Button onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`)} variant="outline" className="gap-2 bg-[#25D366]/10 text-[#25D366]" data-testid="challenge-share-wa">
            <MessageCircle className="w-4 h-4" /> WhatsApp
          </Button>
          <Button onClick={copyLink} variant="outline" className="gap-2" data-testid="challenge-copy-link">
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copied ? "Kopiert!" : "Link kopieren"}
          </Button>
        </div>
        <button onClick={() => navigate("/")} className="text-sm text-muted-foreground mt-6 hover:underline">Zurück zur Startseite</button>
      </div>
    );
  }

  // Quiz
  if (!q) return null;

  const selectedChoiceArr = Array.isArray(selectedChoice) ? selectedChoice : (selectedChoice ? [selectedChoice] : []);

  return (
    <div className="max-w-2xl mx-auto px-4 py-8" data-testid="challenge-quiz">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Swords size={16} style={{ color: '#c9a84c' }} />
          <span className="text-sm text-muted-foreground font-mono">Frage {currentIdx + 1}/{challenge.questions.length}</span>
        </div>
        <span className="text-sm font-medium" style={{ color: '#c9a84c' }}>{score.correct} richtig</span>
      </div>

      <div className="p-6 rounded-xl border border-border/30 mb-6" style={{ background: 'rgba(201,168,76,0.03)' }}>
        <p className="text-base leading-relaxed">{q.question_text_de || q.question_text}</p>
      </div>

      {/* Answer area by question type */}
      {isDragDrop ? (
        <DragDrop
          question={q}
          submitted={submitted}
          answer={dragDropAnswer}
          onChange={setDragDropAnswer}
          result={submitResult}
        />
      ) : isLuckentext ? (
        <Luckentext
          question={q}
          submitted={submitted}
          answer={blankAnswer}
          onChange={setBlankAnswer}
          result={submitResult}
        />
      ) : isMultiSelect ? (
        <MultiSelect
          question={q}
          submitted={submitted}
          selectedChoices={selectedChoiceArr}
          onToggle={(id) => handleChoiceClick(id)}
          result={submitResult ? { correct_choice_ids: (q.choices || []).filter(c => c.is_correct).map(c => c.id) } : null}
        />
      ) : (
        <div className="space-y-3">
          {(q.choices || []).map(c => {
            let style = "border-border/30 hover:border-[#c9a84c]/40";
            if (submitted && c.is_correct) style = "border-emerald-500/50 bg-emerald-500/10";
            else if (submitted && c.id === selectedChoice && !c.is_correct) style = "border-red-500/50 bg-red-500/10";
            return (
              <button key={c.id} onClick={() => handleChoiceClick(c.id)} disabled={submitted}
                className={`w-full text-left p-4 rounded-xl border transition-all ${style}`}>
                <span className="text-sm">{c.text_de || c.text}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Confirm button for non-single-choice types */}
      {!submitted && (isDragDrop || isLuckentext || isMultiSelect) && (
        <Button
          onClick={() => handleSubmit()}
          disabled={!canConfirm()}
          className="w-full mt-4 gap-2"
          style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}
        >
          <Check className="w-4 h-4" /> Antwort bestätigen
        </Button>
      )}

      {/* Correct/Wrong feedback */}
      {submitted && submitResult && (
        <div className={`mt-4 p-3 rounded-xl flex items-center gap-2 text-sm font-medium ${
          submitResult.is_correct ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
        }`}>
          {submitResult.is_correct
            ? <><CheckCircle2 className="w-4 h-4" /> Richtig!</>
            : <><XCircle className="w-4 h-4" /> Falsch</>}
        </div>
      )}

      {submitted && q.explanation_de && (
        <div className="mt-3 p-4 rounded-xl border border-border/20 bg-muted/20 text-sm text-muted-foreground">{q.explanation_de}</div>
      )}

      {submitted && (
        <Button onClick={nextQuestion} className="w-full mt-4 gap-2" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
          {currentIdx + 1 >= challenge.questions.length ? "Ergebnis" : "Weiter"} <ArrowRight className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}
