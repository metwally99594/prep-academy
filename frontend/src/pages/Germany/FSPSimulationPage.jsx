import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Send, Loader2, Bot, User, Award, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import VoiceInputButton from "@/components/Germany/VoiceInputButton";
import { startFSP, chatFSP, switchToExaminer, evaluateFSP } from "@/lib/api";

const SPECIALTIES = [
  { id: "Kardiologie", label: "Kardiologie", emoji: "❤️" },
  { id: "Gastroenterologie", label: "Gastroenterologie", emoji: "🫃" },
  { id: "Pneumologie", label: "Pneumologie", emoji: "🫁" },
  { id: "Neurologie", label: "Neurologie", emoji: "🧠" },
  { id: "Orthopädie", label: "Orthopädie", emoji: "🦴" },
  { id: "Innere Medizin", label: "Innere Medizin", emoji: "🩺" },
];

const DIFFICULTIES = [
  { id: "leicht", label: "Leicht", desc: "Typische Symptome" },
  { id: "mittel", label: "Mittel", desc: "Mehrere Differentialdiagnosen" },
  { id: "schwer", label: "Schwer", desc: "Komplexe, unspezifische Symptome" },
];

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

export default function FSPSimulationPage() {
  const [phase, setPhase] = useState("idle");
  const [specialty, setSpecialty] = useState("Kardiologie");
  const [difficulty, setDifficulty] = useState("mittel");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentPhase, setCurrentPhase] = useState("patient");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [canSwitch, setCanSwitch] = useState(false);
  const [canEnd, setCanEnd] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleStart = useCallback(async () => {
    setLoading(true);
    try {
      const data = await startFSP(specialty, difficulty);
      setSessionId(data.session_id);
      setPhase("chat");
      setCurrentPhase("patient");
      setMessages([{ role: "patient", message: data.opening_message, phase: "patient" }]);
    } catch (err) {
      const detail = err.response?.data?.detail || "Fehler beim Starten";
      if (typeof detail === "string") {
        // Already a string, fine
      } else if (Array.isArray(detail)) {
        err.response.data.detail = detail.map(d => d.msg || String(d)).join("; ");
      }
    } finally {
      setLoading(false);
    }
  }, [specialty, difficulty]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", message: msg, phase: currentPhase }]);
    setSending(true);
    try {
      const data = await chatFSP(sessionId, msg);
      setMessages(prev => [...prev, { role: data.phase, message: data.reply, phase: data.phase }]);
      setCanSwitch(data.can_switch);
      setCanEnd(data.can_end);
    } catch (err) {
      setMessages(prev => [...prev, { role: "system", message: "Fehler bei der Antwort. Bitte versuche es erneut.", phase: currentPhase }]);
    } finally {
      setSending(false);
    }
  }, [input, sending, sessionId, currentPhase]);

  const handleSwitch = useCallback(async () => {
    setSending(true);
    try {
      const data = await switchToExaminer(sessionId);
      setCurrentPhase("examiner");
      setCanSwitch(false);
      setMessages(prev => [...prev, { role: "examiner", message: data.examiner_opening, phase: "examiner" }]);
    } catch (err) {
      // silent
    } finally {
      setSending(false);
    }
  }, [sessionId]);

  const handleEvaluate = useCallback(async () => {
    setLoading(true);
    try {
      const data = await evaluateFSP(sessionId);
      setEvaluation(data);
      setPhase("results");
    } catch (err) {
      const detail = err.response?.data?.detail || "Fehler bei der Bewertung";
      if (typeof detail === "string") {
        // ok
      } else if (Array.isArray(detail)) {
        err.response.data.detail = detail.map(d => d.msg || String(d)).join("; ");
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleNew = () => {
    setPhase("idle");
    setSessionId(null);
    setMessages([]);
    setCurrentPhase("patient");
    setCanSwitch(false);
    setCanEnd(false);
    setEvaluation(null);
  };

  // ── Screen 1: Idle (Specialty + Difficulty selection) ──
  if (phase === "idle") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10">
        <Link to="/de">
          <Button variant="ghost" size="sm" className="gap-1 mb-6">
            <ArrowLeft className="w-4 h-4" /> Zurück
          </Button>
        </Link>
        <h1 className="text-3xl font-bold mb-2">FSP Simulation</h1>
        <p className="text-muted-foreground mb-8">
          Wähle ein Fachgebiet und einen Schwierigkeitsgrad für die Simulation
        </p>

        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Fachgebiet</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
          {SPECIALTIES.map(s => (
            <button key={s.id} onClick={() => setSpecialty(s.id)}
              className={classNames(
                "rounded-xl border p-4 text-left transition-all hover:border-primary/40",
                specialty === s.id ? "border-primary bg-primary/10" : "border-border/60 bg-card"
              )}>
              <div className="text-2xl mb-1">{s.emoji}</div>
              <div className="font-medium text-sm">{s.label}</div>
            </button>
          ))}
        </div>

        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Schwierigkeitsgrad</h2>
        <div className="grid grid-cols-3 gap-3 mb-10">
          {DIFFICULTIES.map(d => (
            <button key={d.id} onClick={() => setDifficulty(d.id)}
              className={classNames(
                "rounded-xl border p-4 text-left transition-all hover:border-primary/40",
                difficulty === d.id ? "border-primary bg-primary/10" : "border-border/60 bg-card"
              )}>
              <div className="font-medium text-sm mb-0.5">{d.label}</div>
              <div className="text-xs text-muted-foreground">{d.desc}</div>
            </button>
          ))}
        </div>

        <Button size="lg" className="w-full gap-2" onClick={handleStart} disabled={loading}>
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bot className="w-5 h-5" />}
          Simulation starten
        </Button>
      </div>
    );
  }

  // ── Screen 3: Results ──
  if (phase === "results" && evaluation) {
    const bars = [
      { key: "language", label: "Sprachkompetenz" },
      { key: "communication", label: "Kommunikation" },
      { key: "medical_knowledge", label: "Fachwissen" },
      { key: "structure", label: "Struktur & Systematik" },
      { key: "terminology", label: "Fachsprache" },
    ];
    const overall = evaluation.overall || 0;
    const barColor = (v) => v >= 80 ? "bg-emerald-500" : v >= 60 ? "bg-amber-500" : "bg-red-500";

    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Award className="w-10 h-10 text-primary" />
          </div>
          <h1 className="text-4xl font-bold mb-1">{Math.round(overall)}%</h1>
          <p className="text-muted-foreground">Gesamtbewertung</p>
        </div>

        <div className="space-y-4 mb-8">
          {bars.map(b => {
            const val = evaluation[b.key] || 0;
            return (
              <div key={b.key}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{b.label}</span>
                  <span className="font-semibold">{Math.round(val)}%</span>
                </div>
                <div className="h-2.5 bg-muted rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${barColor(val)}`} style={{ width: `${val}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        {evaluation.feedback && (
          <div className="rounded-xl border border-border/60 bg-card p-5 mb-6">
            <p className="text-sm leading-relaxed">{evaluation.feedback}</p>
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-4 mb-8">
          {evaluation.strengths?.length > 0 && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <h3 className="text-sm font-semibold text-emerald-500 mb-2">Stärken</h3>
              <ul className="space-y-1.5">
                {evaluation.strengths.map((s, i) => (
                  <li key={i} className="text-sm flex gap-2">
                    <span className="text-emerald-500 mt-0.5">+</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {evaluation.improvements?.length > 0 && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <h3 className="text-sm font-semibold text-amber-500 mb-2">Verbesserungen</h3>
              <ul className="space-y-1.5">
                {evaluation.improvements.map((s, i) => (
                  <li key={i} className="text-sm flex gap-2">
                    <span className="text-amber-500 mt-0.5">→</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <Button size="lg" className="w-full gap-2" onClick={handleNew}>
          <Bot className="w-5 h-5" /> Neue Simulation
        </Button>
      </div>
    );
  }

  // ── Screen 2: Chat ──
  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Link to="/de">
          <Button variant="ghost" size="sm" className="gap-1">
            <ArrowLeft className="w-4 h-4" /> Zurück
          </Button>
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{specialty}</span>
          <span className={classNames(
            "px-2.5 py-0.5 rounded-full text-xs font-medium",
            currentPhase === "patient"
              ? "bg-blue-500/15 text-blue-400"
              : "bg-amber-500/15 text-amber-400"
          )}>
            {currentPhase === "patient" ? "👤 Patientengespräch" : "🎤 Prüfungsgespräch"}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="rounded-xl border border-border/60 bg-card/50 h-[60vh] overflow-y-auto p-4 space-y-3 mb-4">
        {messages.map((m, i) => {
          const isUser = m.role === "user";
          const isSystem = m.role === "system";
          if (isSystem) {
            return (
              <div key={i} className="text-center text-xs text-muted-foreground py-2">
                {m.message}
              </div>
            );
          }
          return (
            <div key={i} className={classNames("flex gap-2", isUser ? "justify-end" : "justify-start")}>
              {!isUser && (
                <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div className={classNames(
                "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                isUser
                  ? "bg-primary text-primary-foreground rounded-br-md"
                  : "bg-muted rounded-bl-md"
              )}>
                {m.message}
              </div>
              {isUser && (
                <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-3.5 h-3.5 text-primary" />
                </div>
              )}
            </div>
          );
        })}
        {sending && (
          <div className="flex justify-start gap-2">
            <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-2.5">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 mb-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="Schreibe deine Antwort..."
          className="flex-1 rounded-xl border border-border/60 bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
          disabled={sending}
        />
        <VoiceInputButton onTranscribed={(text) => setInput(text)} />
        <Button size="icon" onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        {currentPhase === "patient" && canSwitch && (
          <Button variant="outline" className="flex-1 gap-2" onClick={handleSwitch} disabled={sending}>
            <ChevronRight className="w-4 h-4" /> Weiter zum Prüfungsgespräch
          </Button>
        )}
        {currentPhase === "examiner" && canEnd && (
          <Button className="flex-1 gap-2" onClick={handleEvaluate} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Award className="w-4 h-4" />}
            Simulation beenden & bewerten
          </Button>
        )}
      </div>
    </div>
  );
}
