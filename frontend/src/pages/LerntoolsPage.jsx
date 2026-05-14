import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  BookOpen, Layers, Headphones, GitBranch, MessageCircle, Upload,
  Loader2, Play, Pause, ChevronRight, RotateCcw, ArrowLeft, ArrowRight,
  Sparkles, FileText, Globe, ChevronDown, Volume2, Brain, X,
} from "lucide-react";

import MindMapView from "@/components/MindMapView";

const SPECIALTIES = [
  { id: "surgery", name: "Chirurgie" }, { id: "internal", name: "Innere Medizin" },
  { id: "ent", name: "HNO" }, { id: "ophthalmology", name: "Ophthalmologie" },
  { id: "dermatology", name: "Dermatologie" }, { id: "obgyn", name: "Gynäkologie" },
  { id: "neurology", name: "Neurologie" }, { id: "emergency", name: "Notfallmedizin" },
  { id: "pediatrics", name: "Pädiatrie" }, { id: "psychiatry", name: "Psychiatrie" },
];

const TOOLS = [
  { id: "study-guide", name: "Lernleitfaden", icon: BookOpen, desc: "KI-generierter Studienguide", color: "#3b82f6" },
  { id: "flashcards", name: "Lernkarten", icon: Layers, desc: "Flashcards aus Prüfungsfragen", color: "#3b82f6" },
  { id: "audio", name: "Audio-Podcast", icon: Headphones, desc: "Lernpodcast zum Anhören", color: "#10b981" },
  { id: "mind-map", name: "Mind Map", icon: GitBranch, desc: "Visuelle Wissensstruktur", color: "#8b5cf6" },
  { id: "source-chat", name: "Quellen-Chat", icon: MessageCircle, desc: "Chat mit deinen Quellen", color: "#f59e0b" },
  { id: "source-upload", name: "Quelle hochladen", icon: Upload, desc: "PDF/Text als Lernquelle", color: "#ef4444" },
];

const LANGS = [
  { id: "de", name: "Deutsch", flag: "DE" },
  { id: "en", name: "English", flag: "GB" },
  { id: "ar", name: "العربية", flag: "SA" },
  { id: "ru", name: "Русский", flag: "RU" },
];

const VOICES = [
  { id: "nova", name: "Nova" }, { id: "alloy", name: "Alloy" },
  { id: "shimmer", name: "Shimmer" }, { id: "echo", name: "Echo" },
  { id: "onyx", name: "Onyx" }, { id: "fable", name: "Fable" },
];

export default function LerntoolsPage() {
  const { token } = useAuth();
  const [activeTool, setActiveTool] = useState(null);
  const [specialty, setSpecialty] = useState("");
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("de");
  const [loading, setLoading] = useState(false);

  // Study Guide
  const [guideContent, setGuideContent] = useState("");

  // Flashcards
  const [cards, setCards] = useState([]);
  const [cardIdx, setCardIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);

  // Audio
  const [audioData, setAudioData] = useState(null);
  const [voice, setVoice] = useState("nova");
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  // Mind Map
  const [mindMap, setMindMap] = useState(null);

  // Source Chat
  const [notebooks, setNotebooks] = useState([]);
  const [selNotebook, setSelNotebook] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Fetch notebooks
  useEffect(() => {
    if (token) {
      axios.get(`${API}/learn/notebooks`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => setNotebooks(r.data)).catch(() => {});
    }
  }, [token, activeTool]);

  const headers = { Authorization: `Bearer ${token}` };

  const pollJob = async (jobId, maxRetries = 60) => {
    for (let i = 0; i < maxRetries; i++) {
      await new Promise(r => setTimeout(r, 2000));
      const res = await axios.get(`${API}/learn/job/${jobId}`, { headers });
      if (res.data.status === "done") return res.data.result;
      if (res.data.status === "error") throw new Error(res.data.error || "AI-Fehler");
    }
    throw new Error("Timeout: Analyse dauert zu lange");
  };

  const generateStudyGuide = async () => {
    setLoading(true); setGuideContent("");
    try {
      const res = await axios.post(`${API}/learn/study-guide`, { specialty_id: specialty || null, topic: topic || null, language, model: "gpt-4o" }, { headers, timeout: 15000 });
      const result = await pollJob(res.data.job_id);
      setGuideContent(result.content);
      toast.success("Lernleitfaden erstellt");
    } catch (e) { toast.error(e.response?.data?.detail || e.message || "Fehler"); }
    finally { setLoading(false); }
  };

  const generateFlashcards = async () => {
    setLoading(true); setCards([]); setCardIdx(0); setFlipped(false);
    try {
      const res = await axios.post(`${API}/learn/flashcards`, { specialty_id: specialty || null, topic: topic || null, count: 10, language, model: "gpt-4o" }, { headers, timeout: 15000 });
      const result = await pollJob(res.data.job_id);
      setCards(result.cards || []);
      toast.success(`${result.count || result.cards?.length || 0} Lernkarten erstellt`);
    } catch (e) { toast.error(e.response?.data?.detail || e.message || "Fehler"); }
    finally { setLoading(false); }
  };

  const generateAudio = async () => {
    setLoading(true); setAudioData(null);
    try {
      const scriptRes = await axios.post(`${API}/learn/audio-script`, { specialty_id: specialty || null, topic: topic || null, language, voice }, { headers, timeout: 15000 });
      const scriptResult = await pollJob(scriptRes.data.job_id);
      const ttsRes = await axios.post(`${API}/learn/audio-tts`, {
        audio_id: scriptResult.id, script: scriptResult.script, voice, language, podcast_mode: true,
      }, { headers, timeout: 90000 });
      setAudioData({ script: scriptResult.script, audio_base64: ttsRes.data.audio_base64, question_count: 0 });
      if (ttsRes.data.audio_base64) toast.success("Audio-Podcast erstellt!");
      else toast.warning("Skript erstellt, aber Audio fehlgeschlagen");
    } catch (e) { toast.error(e.response?.data?.detail || e.message || "Fehler"); }
    finally { setLoading(false); }
  };

  const generateMindMap = async () => {
    setLoading(true); setMindMap(null);
    try {
      const res = await axios.post(`${API}/learn/mind-map`, { specialty_id: specialty || null, topic: topic || null, language, model: "gpt-4o" }, { headers, timeout: 15000 });
      const result = await pollJob(res.data.job_id);
      setMindMap(result.mind_map);
      toast.success("Mind Map erstellt!");
    } catch (e) { toast.error(e.response?.data?.detail || e.message || "Fehler"); }
    finally { setLoading(false); }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || !selNotebook) return;
    const msg = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", content: msg }]);
    setChatLoading(true);
    try {
      const res = await axios.post(`${API}/learn/chat-with-citations`, { notebook_id: selNotebook, message: msg, language, model: "gpt-4o" }, { headers, timeout: 60000 });
      setChatMessages(prev => [...prev, { role: "assistant", content: res.data.response, citations: res.data.citations }]);
    } catch (e) { setChatMessages(prev => [...prev, { role: "assistant", content: "Fehler aufgetreten." }]); }
    finally { setChatLoading(false); }
  };

  const uploadSource = async (file) => {
    if (!file) return;
    setLoading(true);
    try {
      const nbId = selNotebook || `nb-${Date.now()}`;
      const formData = new FormData();
      formData.append("file", file);
      formData.append("notebook_id", nbId);
      const res = await axios.post(`${API}/learn/source-upload`, formData, { headers, timeout: 120000 });
      toast.success(`"${res.data.name}" hochgeladen!`);
      setSelNotebook(nbId);
      // Refresh notebooks
      const nbs = await axios.get(`${API}/learn/notebooks`, { headers });
      setNotebooks(nbs.data);
    } catch (e) { toast.error(e.response?.data?.detail || "Upload fehlgeschlagen"); }
    finally { setLoading(false); }
  };

  const toggleAudio = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); }
    else { audioRef.current.play(); }
    setIsPlaying(!isPlaying);
  };

  // ═══ MAIN RENDER ═══
  if (!activeTool) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 page-enter" data-testid="lerntools-page">
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3" style={{ fontFamily: "'Playfair Display', serif", color: '#d4d4d8' }}>
            Lern<span style={{ color: '#3b82f6' }}>tools</span>
          </h1>
          <p style={{ color: '#8899aa' }}>KI-gestützte Werkzeuge für dein Medizinstudium</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {TOOLS.map(tool => {
            const Icon = tool.icon;
            return (
              <button key={tool.id} onClick={() => setActiveTool(tool.id)}
                className="p-6 rounded-2xl border text-left transition-all duration-300 hover:-translate-y-1 group cursor-pointer"
                style={{ background: '#0f1a3a', borderColor: 'rgba(59, 130, 246, 0.12)' }}
                data-testid={`tool-${tool.id}`}>
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4" style={{ background: `${tool.color}15` }}>
                  <Icon className="w-6 h-6" style={{ color: tool.color }} />
                </div>
                <h3 className="font-semibold text-base mb-1" style={{ color: '#d4d4d8' }}>{tool.name}</h3>
                <p className="text-sm" style={{ color: '#8899aa' }}>{tool.desc}</p>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  const currentTool = TOOLS.find(t => t.id === activeTool);
  const ToolIcon = currentTool?.icon || BookOpen;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 page-enter" data-testid="lerntools-active">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={() => { setActiveTool(null); setGuideContent(""); setCards([]); setAudioData(null); setMindMap(null); setChatMessages([]); }}
          className="p-2 rounded-lg hover:bg-muted transition-colors" data-testid="back-btn">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${currentTool?.color}15` }}>
          <ToolIcon className="w-5 h-5" style={{ color: currentTool?.color }} />
        </div>
        <div>
          <h2 className="text-xl font-bold">{currentTool?.name}</h2>
          <p className="text-sm text-muted-foreground">{currentTool?.desc}</p>
        </div>
      </div>

      {/* Controls (except source-chat and source-upload) */}
      {!["source-chat", "source-upload"].includes(activeTool) && (
        <div className="glass-card rounded-2xl p-6 mb-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Fachgebiet</label>
              <select value={specialty} onChange={e => setSpecialty(e.target.value)}
                className="w-full h-10 rounded-lg bg-muted/50 border border-border px-3 text-sm"
                data-testid="specialty-select">
                <option value="">Alle Fachgebiete</option>
                {SPECIALTIES.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Thema (optional)</label>
              <Input value={topic} onChange={e => setTopic(e.target.value)} placeholder="z.B. EKG, Anämie, Frakturen..." data-testid="topic-input" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-muted-foreground" />
              <select value={language} onChange={e => setLanguage(e.target.value)} className="h-8 rounded-md bg-muted/50 border border-border px-2 text-sm" data-testid="lang-select">
                {LANGS.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            {activeTool === "audio" && (
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-muted-foreground" />
                <select value={voice} onChange={e => setVoice(e.target.value)} className="h-8 rounded-md bg-muted/50 border border-border px-2 text-sm" data-testid="voice-select">
                  {VOICES.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              </div>
            )}
          </div>
          <Button onClick={() => {
            if (activeTool === "study-guide") generateStudyGuide();
            else if (activeTool === "flashcards") generateFlashcards();
            else if (activeTool === "audio") generateAudio();
            else if (activeTool === "mind-map") generateMindMap();
          }} disabled={loading} className="gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="generate-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? "Wird generiert..." : "Generieren"}
          </Button>
        </div>
      )}

      {/* ═══ STUDY GUIDE OUTPUT ═══ */}
      {activeTool === "study-guide" && guideContent && (
        <div className="glass-card rounded-2xl p-6 prose prose-invert max-w-none" data-testid="guide-output">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{guideContent}</div>
        </div>
      )}

      {/* ═══ FLASHCARDS OUTPUT ═══ */}
      {activeTool === "flashcards" && cards.length > 0 && (
        <div className="space-y-4" data-testid="flashcards-output">
          <div className="text-center text-sm text-muted-foreground font-mono">
            Karte {cardIdx + 1} / {cards.length}
          </div>
          <div onClick={() => setFlipped(!flipped)}
            className="glass-card rounded-2xl p-8 min-h-[200px] flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-[1.01]"
            style={{ borderColor: flipped ? 'rgba(16,185,129,0.3)' : 'rgba(59,130,246,0.15)' }}
            data-testid="flashcard">
            <div className="text-center">
              <div className="text-xs font-mono mb-3" style={{ color: flipped ? '#10b981' : '#3b82f6' }}>
                {flipped ? "ANTWORT" : "FRAGE"}
              </div>
              <p className="text-lg font-medium">
                {flipped ? cards[cardIdx]?.back : cards[cardIdx]?.front}
              </p>
              {cards[cardIdx]?.source_ref && (
                <span className="text-xs text-muted-foreground mt-3 inline-block">{cards[cardIdx].source_ref}</span>
              )}
            </div>
          </div>
          <div className="flex justify-center gap-3">
            <Button variant="outline" size="sm" onClick={() => { setCardIdx(Math.max(0, cardIdx - 1)); setFlipped(false); }} disabled={cardIdx === 0}>
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => setFlipped(!flipped)} data-testid="flip-card-btn">
              <RotateCcw className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => { setCardIdx(Math.min(cards.length - 1, cardIdx + 1)); setFlipped(false); }} disabled={cardIdx >= cards.length - 1}>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ═══ AUDIO OUTPUT ═══ */}
      {activeTool === "audio" && audioData && (
        <div className="space-y-4" data-testid="audio-output">
          {audioData.audio_base64 && (
            <div className="glass-card rounded-2xl p-6 flex items-center gap-4">
              <button onClick={toggleAudio}
                className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)' }}
                data-testid="play-audio-btn">
                {isPlaying ? <Pause className="w-6 h-6 text-[#06081a]" /> : <Play className="w-6 h-6 text-[#06081a] ml-1" />}
              </button>
              <div className="flex-1">
                <h3 className="font-semibold">Audio-Podcast</h3>
                <p className="text-sm text-muted-foreground">Stimme: {voice} · {audioData.question_count} Fragen</p>
              </div>
              <audio ref={audioRef} src={`data:audio/mp3;base64,${audioData.audio_base64}`} onEnded={() => setIsPlaying(false)} />
            </div>
          )}
          {audioData.script && (
            <details className="glass-card rounded-2xl p-6">
              <summary className="cursor-pointer font-semibold text-sm">Skript anzeigen</summary>
              <div className="mt-4 text-sm text-muted-foreground whitespace-pre-wrap">{audioData.script}</div>
            </details>
          )}
        </div>
      )}

      {/* ═══ MIND MAP OUTPUT ═══ */}
      {activeTool === "mind-map" && mindMap && (
        <div className="glass-card rounded-2xl p-6" data-testid="mindmap-output">
          <MindMapView data={mindMap} />
        </div>
      )}

      {/* ═══ SOURCE CHAT ═══ */}
      {activeTool === "source-chat" && (
        <div className="space-y-4">
          <div className="glass-card rounded-2xl p-4 flex items-center gap-4">
            <select value={selNotebook} onChange={e => setSelNotebook(e.target.value)}
              className="flex-1 h-10 rounded-lg bg-muted/50 border border-border px-3 text-sm"
              data-testid="notebook-select">
              <option value="">Notebook auswählen...</option>
              {notebooks.map(nb => (
                <option key={nb.id} value={nb.id}>{nb.name} ({(nb.sources || []).length} Quellen)</option>
              ))}
            </select>
            <select value={language} onChange={e => setLanguage(e.target.value)} className="h-10 rounded-lg bg-muted/50 border border-border px-2 text-sm">
              {LANGS.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>

          <div className="glass-card rounded-2xl overflow-hidden" style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                {chatMessages.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground text-sm">
                    Wähle ein Notebook und stelle eine Frage zu deinen Quellen
                  </div>
                )}
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`max-w-[80%] p-3 rounded-xl text-sm ${msg.role === "user" ? "bg-[#3b82f6]/10 border border-[#3b82f6]/20" : "bg-muted/30 border border-border/30"}`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {msg.citations.map((c, ci) => <span key={ci} className="text-[10px] px-1.5 py-0.5 rounded bg-[#3b82f6]/10 text-[#3b82f6]">{c}</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {chatLoading && <div className="flex gap-2 items-center text-muted-foreground text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Denkt nach...</div>}
              </div>
            </ScrollArea>
            <div className="p-3 border-t border-border/30 flex gap-2">
              <Input value={chatInput} onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") sendChatMessage(); }}
                placeholder="Frage zu deinen Quellen..." disabled={!selNotebook || chatLoading} className="flex-1" data-testid="source-chat-input" />
              <Button onClick={sendChatMessage} disabled={!selNotebook || chatLoading || !chatInput.trim()}
                style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="source-chat-send">
                {chatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ SOURCE UPLOAD ═══ */}
      {activeTool === "source-upload" && (
        <div className="space-y-4">
          <div className="glass-card rounded-2xl p-6">
            <div className="text-center">
              <label className="cursor-pointer inline-flex flex-col items-center gap-3 p-8 border-2 border-dashed rounded-2xl transition-colors hover:border-[#3b82f6]/30"
                style={{ borderColor: 'rgba(59,130,246,0.1)' }}>
                <Upload className="w-10 h-10 text-muted-foreground" />
                <span className="text-sm font-medium">PDF oder Text hochladen</span>
                <span className="text-xs text-muted-foreground">Wird als Lernquelle gespeichert</span>
                <input type="file" accept=".pdf,.txt,.md,.docx" className="hidden" onChange={e => uploadSource(e.target.files[0])} data-testid="source-file-input" />
              </label>
              {loading && <div className="flex items-center justify-center gap-2 mt-4"><Loader2 className="w-4 h-4 animate-spin" /> Wird verarbeitet...</div>}
            </div>
          </div>

          {notebooks.length > 0 && (
            <div className="glass-card rounded-2xl p-6">
              <h3 className="font-semibold mb-4">Deine Notebooks</h3>
              <div className="space-y-2">
                {notebooks.map(nb => (
                  <div key={nb.id} className="flex items-center justify-between p-3 rounded-xl bg-muted/20 border border-border/20">
                    <div>
                      <span className="font-medium text-sm">{nb.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">{(nb.sources || []).length} Quellen</span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => { setActiveTool("source-chat"); setSelNotebook(nb.id); }}>
                      <MessageCircle className="w-4 h-4 mr-1" /> Chat
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loading overlay */}
      {loading && !["source-upload", "source-chat"].includes(activeTool) && (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: '#3b82f6' }} />
          <p className="text-sm text-muted-foreground">KI generiert Inhalte...</p>
        </div>
      )}
    </div>
  );
}
