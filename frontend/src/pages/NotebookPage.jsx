import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API } from "@/App";
import { FileText, Upload, Send, Trash2, Sparkles, ArrowLeft, MessageSquare, BookOpen, Loader2, Lock, Brain, ListChecks, HelpCircle, GraduationCap, CheckCircle2,
  Layers, Headphones, GitBranch, Play, Pause, ArrowRight, RotateCcw, Volume2, ChevronRight, X,
} from "lucide-react";
import MindMapView from "@/components/MindMapView";

const LANGS = [
  { id: "de", name: "DE" }, { id: "en", name: "EN" }, { id: "ar", name: "AR" }, { id: "ru", name: "RU" }, { id: "uk", name: "UK" },
];
const VOICES = [
  { id: "nova", name: "Nova (weiblich)" }, { id: "alloy", name: "Alloy (neutral)" },
  { id: "shimmer", name: "Shimmer (weiblich)" }, { id: "echo", name: "Echo (männlich)" },
  { id: "onyx", name: "Onyx (tief)" }, { id: "fable", name: "Fable (warm)" },
];

const ANALYSIS_STAGES = [
  { id: "layer1", label: "Globale Analyse", desc: "Überblick & Struktur", icon: "🔍", color: "#c9a84c" },
  { id: "layer2", label: "Detailanalyse", desc: "Chunks & Konzepte", icon: "🧠", color: "#818cf8" },
  { id: "layer3", label: "Wissensvernetzung", desc: "Synthese & Verbindungen", icon: "🔗", color: "#34d399" },
];

function AnalysisProgressBanner({ progress, preview, onDismiss }) {
  if (!progress) return null;
  const isDone = progress.stage === "done";
  const currentIdx = isDone ? 3 : ANALYSIS_STAGES.findIndex(s => s.id === progress.stage);

  return (
    <div className="mb-3 rounded-xl border overflow-hidden" style={{ borderColor: isDone ? 'rgba(52,211,153,0.3)' : 'rgba(201,168,76,0.2)' }}>
      {/* Stage indicator row */}
      <div className="flex items-center px-4 py-2.5 gap-3" style={{ background: isDone ? 'rgba(52,211,153,0.05)' : 'rgba(201,168,76,0.05)' }}>
        {isDone
          ? <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />
          : <Loader2 size={16} className="animate-spin flex-shrink-0" style={{ color: ANALYSIS_STAGES[currentIdx]?.color }} />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            {ANALYSIS_STAGES.map((s, i) => {
              const done = isDone || i < currentIdx;
              const active = !isDone && i === currentIdx;
              return (
                <div key={s.id} className="flex items-center gap-1.5">
                  <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-all ${
                    done ? 'bg-emerald-500/15 text-emerald-400' : active ? 'text-white' : 'bg-muted/50 text-muted-foreground'
                  }`} style={active ? { background: `${s.color}20`, color: s.color } : {}}>
                    <span>{done ? '✓' : s.icon}</span>
                    <span>{s.label}</span>
                  </div>
                  {i < 2 && <ChevronRight size={12} className="text-muted-foreground/40" />}
                </div>
              );
            })}
          </div>
          <div className="h-1.5 rounded-full bg-muted/30 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: isDone ? '100%' : `${(currentIdx / 3) * 100 + 15}%`, background: isDone ? '#34d399' : ANALYSIS_STAGES[currentIdx]?.color }} />
          </div>
        </div>
        {isDone && (
          <button onClick={onDismiss} className="text-muted-foreground/50 hover:text-muted-foreground transition-colors flex-shrink-0">
            <X size={14} />
          </button>
        )}
        {!isDone && (
          <span className="text-xs text-muted-foreground font-mono flex-shrink-0">{progress.elapsed}s</span>
        )}
      </div>

      {/* Preview after done */}
      {isDone && preview?.master_summary && (
        <div className="px-4 pb-3">
          <p className="text-xs text-muted-foreground/80 leading-relaxed line-clamp-2">{preview.master_summary}</p>
          {preview.top_exam_points?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {preview.top_exam_points.slice(0, 3).map((pt, i) => (
                <span key={i} className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399' }}>
                  {typeof pt === "string" ? pt.slice(0, 50) : pt}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function NotebookPage() {
  const [token] = useState(localStorage.getItem("token"));
  const [notebooks, setNotebooks] = useState([]);
  const [activeNotebook, setActiveNotebook] = useState(null);
  const [notebookMeta, setNotebookMeta] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [quizGenResult, setQuizGenResult] = useState(null);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const headers = { Authorization: `Bearer ${token}` };

  // Lerntools state
  const [activeTab, setActiveTab] = useState("chat");
  const [language, setLanguage] = useState("de");
  const [toolLoading, setToolLoading] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState(-1);

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
  const [audioSavedDate, setAudioSavedDate] = useState(null);

  // Mind Map
  const [mindMap, setMindMap] = useState(null);

  // Quiz count
  const [quizCount, setQuizCount] = useState(10);

  // Hierarchical Analysis state
  const [analysisProgress, setAnalysisProgress] = useState(null); // {stage, elapsed, stageStart}
  const [analysisPreview, setAnalysisPreview] = useState(null);

  useEffect(() => {
    if (token) fetchNotebooks();
  }, [token]); // eslint-disable-line

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Tick elapsed time while analysis is running
  useEffect(() => {
    if (!analysisProgress || analysisProgress.stage === "done") return;
    const iv = setInterval(() => {
      setAnalysisProgress(prev =>
        prev && prev.stage !== "done"
          ? { ...prev, elapsed: Math.round((Date.now() - prev.stageStart) / 1000) }
          : prev
      );
    }, 1000);
    return () => clearInterval(iv);
  }, [analysisProgress?.stage]); // eslint-disable-line

  // Reload saved audio when language changes
  useEffect(() => {
    if (activeTab === "audio" && activeNotebook) {
      loadSavedAudio();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, activeNotebook?.id]);

  const fetchNotebooks = async () => {
    try {
      const res = await axios.get(`${API}/notebook/list`, { headers });
      setNotebooks(res.data); setAccessDenied(false);
    } catch (e) { if (e.response?.status === 403) setAccessDenied(true); }
  };

  // Run 3-layer hierarchical analysis after upload (fire-and-forget)
  const runAnalysisChain = async (nb) => {
    const nbId = nb.id;

    // Layer 1: Global scan (~15s)
    setAnalysisProgress({ stage: "layer1", elapsed: 0, stageStart: Date.now() });
    try {
      await axios.post(`${API}/notebook/analyze/global/${nbId}`, {}, { headers, timeout: 60000 });
    } catch { /* non-fatal — backend will retry on task call */ }

    // Layer 2: Chunk analysis (~30s, background job)
    setAnalysisProgress({ stage: "layer2", elapsed: 0, stageStart: Date.now() });
    try {
      const jobRes = await axios.post(`${API}/notebook/analyze/chunks/${nbId}`, {}, { headers, timeout: 15000 });
      const jobId = jobRes.data.job_id;
      if (jobId) {
        for (let i = 0; i < 40; i++) {
          await new Promise(r => setTimeout(r, 3000));
          try {
            const poll = await axios.get(`${API}/notebook/analyze/jobs/${jobId}`, { headers });
            if (poll.data.status === "done" || poll.data.status === "error") break;
          } catch { break; }
        }
      }
    } catch { /* non-fatal */ }

    // Layer 3: Synthesis (~5s)
    setAnalysisProgress({ stage: "layer3", elapsed: 0, stageStart: Date.now() });
    try {
      const synthRes = await axios.post(`${API}/notebook/synthesize/${nbId}`, {}, { headers, timeout: 30000 });
      setAnalysisPreview(synthRes.data);
    } catch { /* non-fatal */ }

    setAnalysisProgress({ stage: "done", elapsed: 0, stageStart: 0 });
  };

  const uploadPDF = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setAnalysisProgress(null);
    setAnalysisPreview(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post(`${API}/notebook/upload`, formData, { headers: { ...headers, "Content-Type": "multipart/form-data" } });
      await fetchNotebooks();
      openNotebook(res.data);
      runAnalysisChain(res.data); // fire-and-forget: shows progress banner
    } catch (e) {
      if (e.response?.status === 403) setAccessDenied(true);
      else alert(e.response?.data?.detail || "Fehler beim Hochladen");
    } finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = ""; }
  };

  const openNotebook = async (nb) => {
    setActiveNotebook(nb); setNotebookMeta(null); setActiveTab("chat");
    setAnalysisProgress(null); setAnalysisPreview(null);
    try {
      const [histRes, metaRes] = await Promise.all([
        axios.get(`${API}/notebook/${nb.id}/history`, { headers }),
        axios.get(`${API}/notebook/${nb.id}`, { headers })
      ]);
      setMessages(histRes.data); setNotebookMeta(metaRes.data);
    } catch { setMessages([]); }
  };

  const deleteNotebook = async (id) => {
    if (!window.confirm("Dieses Notebook wirklich löschen?")) return;
    try {
      await axios.delete(`${API}/notebook/${id}`, { headers });
      if (activeNotebook?.id === id) { setActiveNotebook(null); setMessages([]); }
      fetchNotebooks();
    } catch {}
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeNotebook || sending) return;
    const msg = input.trim(); setInput("");
    setMessages(prev => [...prev, { role: "user", content: msg, id: Date.now() }]);
    setSending(true);
    try {
      const res = await axios.post(`${API}/notebook/chat`, { notebook_id: activeNotebook.id, message: msg, chunk_index: selectedChunk >= 0 ? selectedChunk : null }, { headers });
      setMessages(prev => [...prev, { role: "assistant", content: res.data.response, id: Date.now() + 1 }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Fehler: Bitte versuchen Sie es erneut.", id: Date.now() + 1 }]);
    } finally { setSending(false); }
  };

  const doAction = async (action) => {
    if (!activeNotebook || actionLoading) return;
    setActionLoading(action);
    const labels = { summarize: "Fasse dieses Dokument zusammen", mcq: "Generiere MCQ-Prüfungsfragen" };
    setMessages(prev => [...prev, { role: "user", content: labels[action] || action, id: Date.now() }]);
    try {
      const chunkParam = selectedChunk >= 0 ? `&chunk_index=${selectedChunk}` : '';
      const langParam = `&language=${language}`;
      const url = action === "mcq"
        ? `${API}/notebook/${activeNotebook.id}/generate-mcq?${langParam}${chunkParam}`
        : `${API}/notebook/${activeNotebook.id}/summarize?${langParam}${chunkParam}`;
      const res = await axios.post(url, {}, { headers, timeout: 90000 });
      setMessages(prev => [...prev, { role: "assistant", content: res.data.summary || res.data.mcq || "Keine Antwort.", id: Date.now() + 1 }]);
    } catch { setMessages(prev => [...prev, { role: "assistant", content: "Fehler aufgetreten.", id: Date.now() + 1 }]); }
    finally { setActionLoading(null); }
  };

  const generateQuiz = async () => {
    if (!activeNotebook || generatingQuiz) return;
    setGeneratingQuiz(true); setQuizGenResult(null);
    try {
      const chunkParam = selectedChunk >= 0 ? `&chunk_index=${selectedChunk}` : '';
      const res = await axios.post(`${API}/notebook/${activeNotebook.id}/generate-quiz?count=${quizCount}&language=${language}${chunkParam}`, {}, { headers });
      const jobId = res.data.job_id;
      if (!jobId) { setQuizGenResult(res.data); return; }
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
          const poll = await axios.get(`${API}/quiz-job/${jobId}`, { headers });
          if (poll.data.status === "done") { setQuizGenResult({ success: true, message: poll.data.message, count: poll.data.count }); return; }
          if (poll.data.status === "error") { setQuizGenResult({ success: false, message: poll.data.message || "Fehler" }); return; }
        } catch { /* continue polling */ }
      }
      setQuizGenResult({ success: false, message: "Zeitüberschreitung. Bitte erneut versuchen." });
    } catch (e) { setQuizGenResult({ success: false, message: e.response?.data?.detail || "Fehler" }); }
    finally { setGeneratingQuiz(false); }
  };

  // ═══ LERNTOOLS — New hierarchical endpoints ═══

  const generateStudyGuide = async () => {
    if (!activeNotebook) return;
    setToolLoading(true); setGuideContent("");
    try {
      const res = await axios.post(
        `${API}/notebook/lernleitfaden/${activeNotebook.id}?language=${language}`,
        {}, { headers, timeout: 15000 }
      );
      // Cached result returned immediately
      if (res.data.status === "done" && res.data.content) {
        setGuideContent(res.data.content);
        return;
      }
      const jobId = res.data.job_id;
      if (!jobId) throw new Error("Kein Job erhalten");
      // Poll until done (up to ~5 min at 3s intervals)
      for (let i = 0; i < 100; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
          const poll = await axios.get(
            `${API}/notebook/lernleitfaden/job/${jobId}`,
            { headers, timeout: 10000 }
          );
          if (poll.data.status === "done") {
            setGuideContent(poll.data.content || "Kein Inhalt.");
            return;
          }
          if (poll.data.status === "error") {
            throw new Error(poll.data.message || "Generierung fehlgeschlagen");
          }
        } catch (pollErr) {
          if (pollErr.message?.includes("Generierung fehlgeschlagen")) throw pollErr;
          // transient network error — retry next tick
        }
      }
      throw new Error("Zeitüberschreitung — bitte erneut versuchen");
    } catch (e) {
      setGuideContent(e.response?.data?.detail || e.message || "Fehler beim Generieren des Lernleitfadens.");
    } finally {
      setToolLoading(false);
    }
  };

  const generateFlashcards = async () => {
    if (!activeNotebook) return;
    setToolLoading(true); setCards([]); setCardIdx(0); setFlipped(false);
    try {
      const res = await axios.post(
        `${API}/notebook/lernkarten/${activeNotebook.id}?language=${language}&count=15`,
        {}, { headers, timeout: 180000 }
      );
      setCards(res.data.cards || []);
    } catch { setCards([{ front: "Fehler", back: "Konnte keine Lernkarten generieren", difficulty: "medium", category: "Allgemein" }]); }
    finally { setToolLoading(false); }
  };

  const loadSavedAudio = async () => {
    if (!activeNotebook) return;
    try {
      const res = await axios.get(`${API}/notebook/audio-saved/${activeNotebook.id}?language=${language}`, { headers });
      if (res.data.found) {
        setAudioData({ script: res.data.script, audio_base64: res.data.audio_base64, voice: res.data.voice });
        setAudioSavedDate(res.data.created_at);
        return true;
      }
      setAudioData(null); setAudioSavedDate(null);
    } catch { setAudioData(null); setAudioSavedDate(null); }
    return false;
  };

  const generateAudio = async () => {
    if (!activeNotebook) return;
    setToolLoading(true); setAudioData(null); setAudioSavedDate(null);
    try {
      const res = await axios.post(
        `${API}/notebook/audio/${activeNotebook.id}?language=${language}&voice=${voice}`,
        {}, { headers, timeout: 180000 }
      );
      setAudioData({ script: res.data.script, audio_base64: res.data.audio_base64, voice: res.data.voice });
      setAudioSavedDate(new Date().toISOString());
    } catch (e) { setAudioData({ script: e.response?.data?.detail || e.message || "Fehler beim Generieren.", audio_base64: null }); }
    finally { setToolLoading(false); }
  };

  const generateMindMap = async () => {
    if (!activeNotebook) return;
    setToolLoading(true); setMindMap(null);
    try {
      const res = await axios.post(
        `${API}/notebook/mindmap/${activeNotebook.id}?language=${language}`,
        {}, { headers, timeout: 180000 }
      );
      setMindMap(res.data.mind_map);
    } catch { setMindMap({ title: "Fehler", children: [] }); }
    finally { setToolLoading(false); }
  };

  const toggleAudio = () => {
    if (!audioRef.current) return;
    if (isPlaying) audioRef.current.pause(); else audioRef.current.play();
    setIsPlaying(!isPlaying);
  };

  // Access denied
  if (accessDenied) {
    return (
      <div data-testid="notebook-locked" className="max-w-lg mx-auto px-4 py-20 text-center">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'rgba(201,168,76,0.1)' }}>
          <Lock size={32} style={{ color: '#c9a84c' }} />
        </div>
        <h2 className="text-xl font-bold mb-2">Notebook gesperrt</h2>
        <p className="text-muted-foreground text-sm">Diese Funktion ist nur für freigeschaltete Benutzer verfügbar.</p>
      </div>
    );
  }

  // ═══ ACTIVE NOTEBOOK VIEW ═══
  if (activeNotebook) {
    const TABS = [
      { id: "chat", name: "Chat", icon: MessageSquare },
      { id: "study-guide", name: "Lernleitfaden", icon: BookOpen, action: generateStudyGuide },
      { id: "flashcards", name: "Lernkarten", icon: Layers, action: generateFlashcards },
      { id: "audio", name: "Audio", icon: Headphones, action: async () => { const loaded = await loadSavedAudio(); if (!loaded) generateAudio(); } },
      { id: "mind-map", name: "Mind Map", icon: GitBranch, action: generateMindMap },
    ];

    return (
      <div data-testid="notebook-chat" className="max-w-4xl mx-auto px-4 py-4 flex flex-col" style={{ height: "calc(100vh - 80px)" }}>
        {/* Header */}
        <div className="flex items-center gap-3 mb-3 pb-3" style={{ borderBottom: '1px solid rgba(201,168,76,0.1)' }}>
          <button data-testid="notebook-back-btn" onClick={() => { setActiveNotebook(null); setNotebookMeta(null); setMessages([]); setActiveTab("chat"); setAnalysisProgress(null); setAnalysisPreview(null); }}
            className="p-2 rounded-lg hover:bg-muted transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(201,168,76,0.1)' }}>
            <FileText size={20} style={{ color: '#c9a84c' }} />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold truncate text-sm">{activeNotebook.filename}</h2>
            <p className="text-xs text-muted-foreground">{activeNotebook.page_count} Seiten</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={language} onChange={e => setLanguage(e.target.value)} className="h-7 rounded-md bg-muted/50 border border-border px-1.5 text-xs" data-testid="nb-lang-select">
              {LANGS.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            {notebookMeta?.chunks?.length > 1 && (
              <select value={selectedChunk} onChange={e => setSelectedChunk(parseInt(e.target.value))}
                className="h-7 rounded-md bg-muted/50 border border-border px-1.5 text-xs max-w-[160px]" data-testid="chunk-select">
                <option value={-1}>Gesamtes Dokument</option>
                {notebookMeta.chunks.map(c => (
                  <option key={c.index} value={c.index}>{c.title} ({c.word_count}w)</option>
                ))}
              </select>
            )}
            <div className="flex gap-1">
              <button data-testid="notebook-summarize-btn" onClick={() => doAction("summarize")} disabled={!!actionLoading}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50 hover:bg-muted" style={{ color: '#c9a84c' }}>
                {actionLoading === "summarize" ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} Zusammenfassen
              </button>
              <button data-testid="notebook-mcq-btn" onClick={() => doAction("mcq")} disabled={!!actionLoading}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50 hover:bg-muted text-blue-400">
                {actionLoading === "mcq" ? <Loader2 size={12} className="animate-spin" /> : <ListChecks size={12} />} MCQ
              </button>
              <select value={quizCount} onChange={e => setQuizCount(parseInt(e.target.value))}
                className="h-7 rounded-md bg-muted/50 border border-border px-1 text-xs w-14" data-testid="quiz-count-select">
                {[10, 20, 30, 40, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <button data-testid="notebook-quiz-btn" onClick={generateQuiz} disabled={generatingQuiz || !!actionLoading}
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50 hover:bg-muted text-emerald-400">
                {generatingQuiz ? <Loader2 size={12} className="animate-spin" /> : <GraduationCap size={12} />} Quiz
              </button>
            </div>
          </div>
        </div>

        {/* Analysis Progress Banner */}
        <AnalysisProgressBanner
          progress={analysisProgress}
          preview={analysisPreview}
          onDismiss={() => setAnalysisProgress(null)}
        />

        {/* Quiz Result Banner */}
        {quizGenResult && (
          <div className={`mb-3 p-3 rounded-xl border ${quizGenResult.success ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`} data-testid="quiz-gen-result">
            <div className="flex items-center gap-3">
              {quizGenResult.success ? <CheckCircle2 size={18} className="text-emerald-400" /> : <HelpCircle size={18} className="text-red-400" />}
              <p className="text-sm flex-1">{quizGenResult.message}</p>
              {quizGenResult.success && (
                <a href="/specialty/special" className="px-3 py-1 text-xs font-medium rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30" data-testid="quiz-gen-start-link">Jetzt üben</a>
              )}
              <button onClick={() => setQuizGenResult(null)} className="text-muted-foreground hover:text-foreground"><X size={16} /></button>
            </div>
          </div>
        )}
        {generatingQuiz && (
          <div className="mb-3 p-3 rounded-xl border border-blue-500/30 bg-blue-500/5 flex items-center gap-3" data-testid="quiz-gen-loading">
            <Loader2 size={16} className="text-blue-400 animate-spin" />
            <p className="text-sm text-blue-400">Quiz wird generiert...</p>
          </div>
        )}

        {/* ═══ TAB BAR ═══ */}
        <div className="flex gap-1 mb-3 overflow-x-auto pb-1" data-testid="notebook-tabs">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => { setActiveTab(tab.id); if (tab.action && tab.id !== "chat") tab.action(); }}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  isActive ? 'text-[#c9a84c]' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
                style={isActive ? { background: 'rgba(201,168,76,0.1)' } : {}}
                data-testid={`tab-${tab.id}`}>
                <Icon size={14} />
                {tab.name}
              </button>
            );
          })}
        </div>

        {/* ═══ TAB CONTENT ═══ */}
        <div className="flex-1 overflow-y-auto">
          {/* CHAT TAB */}
          {activeTab === "chat" && (
            <div className="flex flex-col h-full">
              <div className="flex-1 overflow-y-auto space-y-3 pb-3">
                {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
                    <Brain size={48} strokeWidth={1} style={{ color: '#c9a84c' }} />
                    <p className="text-center text-sm">Stellen Sie eine Frage zu<br /><strong>{activeNotebook.filename}</strong></p>
                    {notebookMeta?.topics?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 justify-center max-w-md">
                        {notebookMeta.topics.map((t, i) => <span key={i} className="px-2.5 py-1 rounded-full text-xs" style={{ background: 'rgba(201,168,76,0.1)', color: '#c9a84c' }}>{t}</span>)}
                      </div>
                    )}
                    {/* Show analysis preview if available */}
                    {analysisPreview?.master_summary && (
                      <div className="max-w-md w-full px-4 py-3 rounded-xl border" style={{ borderColor: 'rgba(52,211,153,0.2)', background: 'rgba(52,211,153,0.03)' }}>
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle2 size={14} className="text-emerald-400" />
                          <span className="text-xs font-medium text-emerald-400">Tiefenanalyse abgeschlossen</span>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{analysisPreview.master_summary}</p>
                        {analysisPreview.top_exam_points?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {analysisPreview.top_exam_points.slice(0, 4).map((pt, i) => (
                              <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-muted/50">{typeof pt === "string" ? pt.slice(0, 40) : pt}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    {notebookMeta?.auto_summary && !analysisPreview && (
                      <p className="text-xs text-muted-foreground max-w-md text-center bg-muted/30 px-4 py-3 rounded-xl">{notebookMeta.auto_summary}</p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-1 justify-center max-w-lg">
                      {(notebookMeta?.suggested_questions?.length > 0 ? notebookMeta.suggested_questions : ["Fasse zusammen", "Was sind die Hauptthemen?", "Erkläre die wichtigsten Konzepte"]).map(q => (
                        <button key={q} onClick={() => setInput(q)} className="px-3 py-1.5 border border-border rounded-full text-xs hover:bg-muted/50 transition-all">
                          <HelpCircle size={10} className="inline mr-1 -mt-0.5" />{q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map(msg => (
                  <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div data-testid={`chat-msg-${msg.role}`}
                      className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                        msg.role === "user" ? "rounded-br-md" : "rounded-bl-md bg-muted/30 border border-border/30"
                      }`}
                      style={msg.role === "user" ? { background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.15)' } : {}}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {(sending || actionLoading) && (
                  <div className="flex justify-start">
                    <div className="bg-muted/30 border border-border/30 px-4 py-3 rounded-2xl rounded-bl-md flex items-center gap-2">
                      <Loader2 size={14} className="animate-spin" style={{ color: '#c9a84c' }} />
                      <span className="text-xs text-muted-foreground">{actionLoading === "mcq" ? "MCQ wird generiert..." : actionLoading === "summarize" ? "Zusammenfassung..." : "Denkt nach..."}</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              <div className="flex gap-2 pt-3" style={{ borderTop: '1px solid rgba(201,168,76,0.08)' }}>
                <input data-testid="notebook-chat-input" value={input} onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  placeholder="Frage stellen... (Deutsch / English / العربية / Русский / Українська)"
                  className="flex-1 px-4 py-2.5 bg-muted/30 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-[#c9a84c]/30 text-sm" />
                <button data-testid="notebook-send-btn" onClick={sendMessage} disabled={!input.trim() || sending}
                  className="px-4 py-2.5 rounded-xl disabled:opacity-40 transition-colors text-sm font-medium"
                  style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                  <Send size={18} />
                </button>
              </div>
            </div>
          )}

          {/* STUDY GUIDE TAB */}
          {activeTab === "study-guide" && (
            <div className="space-y-4">
              {toolLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#c9a84c' }} />
                  <span className="text-sm text-muted-foreground">Lernleitfaden wird erstellt...</span>
                  <span className="text-xs text-muted-foreground/60">KI analysiert Ihre medizinischen Inhalte</span>
                </div>
              )}
              {guideContent && <div className="p-6 rounded-xl border border-border/30 bg-muted/10 text-sm leading-relaxed whitespace-pre-wrap" data-testid="guide-output">{guideContent}</div>}
              {!toolLoading && !guideContent && (
                <button onClick={generateStudyGuide} className="w-full py-8 rounded-xl border border-dashed border-border/50 text-muted-foreground hover:border-[#c9a84c]/30 hover:text-foreground transition-all">
                  <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Lernleitfaden generieren</p>
                  <p className="text-xs mt-1 opacity-60">Tiefenanalyse → strukturierter Lernplan</p>
                </button>
              )}
            </div>
          )}

          {/* FLASHCARDS TAB */}
          {activeTab === "flashcards" && (
            <div className="space-y-4">
              {toolLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#c9a84c' }} />
                  <span className="text-sm text-muted-foreground">Lernkarten werden erstellt...</span>
                  <span className="text-xs text-muted-foreground/60">KI erstellt klinische Beispiele für jede Karte</span>
                </div>
              )}
              {cards.length > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <div className="text-center text-sm text-muted-foreground font-mono">Karte {cardIdx + 1} / {cards.length}</div>
                    {cards[cardIdx]?.category && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground">{cards[cardIdx].category}</span>
                    )}
                  </div>
                  <div onClick={() => setFlipped(!flipped)}
                    className="p-8 min-h-[180px] flex items-center justify-center cursor-pointer transition-all duration-300 rounded-xl border"
                    style={{ borderColor: flipped ? 'rgba(16,185,129,0.3)' : 'rgba(201,168,76,0.15)', background: flipped ? 'rgba(16,185,129,0.03)' : 'rgba(201,168,76,0.03)' }}
                    data-testid="flashcard">
                    <div className="text-center">
                      <div className="text-xs font-mono mb-3" style={{ color: flipped ? '#10b981' : '#c9a84c' }}>{flipped ? "ANTWORT" : "FRAGE"}</div>
                      <p className="text-lg font-medium">{flipped ? cards[cardIdx]?.back : cards[cardIdx]?.front}</p>
                    </div>
                  </div>
                  <div className="flex justify-center gap-3">
                    <button onClick={() => { setCardIdx(Math.max(0, cardIdx - 1)); setFlipped(false); }} disabled={cardIdx === 0} className="p-2 rounded-lg hover:bg-muted disabled:opacity-30"><ArrowLeft size={18} /></button>
                    <button onClick={() => setFlipped(!flipped)} className="p-2 rounded-lg hover:bg-muted" data-testid="flip-card-btn"><RotateCcw size={18} /></button>
                    <button onClick={() => { setCardIdx(Math.min(cards.length - 1, cardIdx + 1)); setFlipped(false); }} disabled={cardIdx >= cards.length - 1} className="p-2 rounded-lg hover:bg-muted disabled:opacity-30"><ArrowRight size={18} /></button>
                  </div>
                </>
              )}
              {!toolLoading && cards.length === 0 && (
                <button onClick={generateFlashcards} className="w-full py-8 rounded-xl border border-dashed border-border/50 text-muted-foreground hover:border-[#c9a84c]/30 hover:text-foreground transition-all">
                  <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Lernkarten generieren</p>
                  <p className="text-xs mt-1 opacity-60">15 Karten mit klinischen Beispielen</p>
                </button>
              )}
            </div>
          )}

          {/* AUDIO TAB */}
          {activeTab === "audio" && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/20">
                <Volume2 size={16} className="text-muted-foreground" />
                <select value={voice} onChange={e => setVoice(e.target.value)} className="h-8 rounded-md bg-muted/50 border border-border px-2 text-sm" data-testid="voice-select">
                  {VOICES.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
                <div className="ml-auto flex items-center gap-2">
                  {audioData?.audio_base64 && !toolLoading && (
                    <button onClick={generateAudio} className="px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-muted/50 text-muted-foreground transition-colors" data-testid="regenerate-audio-btn">
                      <RotateCcw size={12} className="inline mr-1" />Neu generieren
                    </button>
                  )}
                  {!audioData && !toolLoading && <button onClick={generateAudio} className="px-4 py-1.5 rounded-lg text-xs font-medium" style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c' }} data-testid="generate-audio-btn">Podcast generieren</button>}
                </div>
              </div>
              {toolLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#c9a84c' }} />
                  <span className="text-sm text-muted-foreground">Audio wird generiert...</span>
                  <span className="text-xs text-muted-foreground/60">Skript + Sprachsynthese</span>
                </div>
              )}
              {audioData && (
                <>
                  {audioData.audio_base64 && (
                    <div className="flex items-center gap-4 p-5 rounded-xl border" style={{ borderColor: 'rgba(201,168,76,0.15)', background: 'rgba(201,168,76,0.03)' }}>
                      <button onClick={toggleAudio} className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)' }} data-testid="play-audio-btn">
                        {isPlaying ? <Pause className="w-6 h-6 text-[#06081a]" /> : <Play className="w-6 h-6 text-[#06081a] ml-1" />}
                      </button>
                      <div>
                        <h3 className="font-semibold text-sm">Audio-Podcast</h3>
                        <p className="text-xs text-muted-foreground">Stimme: {audioData.voice || voice}</p>
                        {audioSavedDate && <p className="text-xs text-muted-foreground/60 mt-0.5">Gespeichert: {new Date(audioSavedDate).toLocaleDateString("de-DE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>}
                      </div>
                      <audio ref={audioRef} src={`data:audio/mp3;base64,${audioData.audio_base64}`} onEnded={() => setIsPlaying(false)} />
                    </div>
                  )}
                  {audioData.error && (
                    <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-sm text-red-400">{audioData.error}</div>
                  )}
                  {!audioData.audio_base64 && !audioData.error && (
                    <div className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 text-sm text-yellow-400">Audio konnte nicht generiert werden. Skript ist verfügbar.</div>
                  )}
                  {audioData.script && (
                    <details className="rounded-xl border border-border/30 p-4">
                      <summary className="cursor-pointer font-semibold text-sm">Skript anzeigen</summary>
                      <div className="mt-3 text-sm text-muted-foreground whitespace-pre-wrap">{audioData.script}</div>
                    </details>
                  )}
                </>
              )}
            </div>
          )}

          {/* MIND MAP TAB */}
          {activeTab === "mind-map" && (
            <div>
              {toolLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#c9a84c' }} />
                  <span className="text-sm text-muted-foreground">Mind Map wird erstellt...</span>
                  <span className="text-xs text-muted-foreground/60">Wissensstruktur aus Tiefenanalyse</span>
                </div>
              )}
              {mindMap && <div className="p-6 rounded-xl border border-border/30 bg-muted/10" data-testid="mindmap-output"><MindMapView data={mindMap} /></div>}
              {!toolLoading && !mindMap && (
                <button onClick={generateMindMap} className="w-full py-8 rounded-xl border border-dashed border-border/50 text-muted-foreground hover:border-[#c9a84c]/30 hover:text-foreground transition-all">
                  <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Mind Map generieren</p>
                  <p className="text-xs mt-1 opacity-60">Verknüpfte Konzepte visualisieren</p>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ═══ LIST VIEW ═══
  return (
    <div data-testid="notebook-page" className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ fontFamily: "'Playfair Display', serif" }}>
            <Brain size={24} style={{ color: '#c9a84c' }} /> PDF <span style={{ color: '#c9a84c' }}>Notebook</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Laden Sie medizinische PDFs hoch und lernen Sie mit KI</p>
        </div>
        <label data-testid="notebook-upload-btn"
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl cursor-pointer transition-colors text-sm font-medium ${uploading ? "opacity-50 pointer-events-none" : ""}`}
          style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
          {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
          {uploading ? "Wird hochgeladen..." : "PDF hochladen"}
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={uploadPDF} className="hidden" />
        </label>
      </div>

      {notebooks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-4">
          <BookOpen size={64} strokeWidth={1} />
          <p className="text-lg font-medium">Noch keine PDFs hochgeladen</p>
          <p className="text-sm">Laden Sie eine medizinische PDF-Datei hoch</p>
          <div className="flex flex-wrap gap-3 mt-4 text-xs text-muted-foreground/60">
            {["Vorlesungsskripte", "Prüfungsfragen", "Lehrbücher", "Fallstudien"].map(t => (
              <span key={t} className="px-3 py-1.5 bg-muted/30 rounded-full">{t}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-3">
          {notebooks.map(nb => (
            <div key={nb.id} data-testid={`notebook-item-${nb.id}`}
              className="flex items-center gap-4 p-4 border rounded-xl cursor-pointer group transition-all hover:-translate-y-0.5"
              style={{ borderColor: 'rgba(201,168,76,0.08)', background: 'rgba(201,168,76,0.02)' }}
              onClick={() => openNotebook(nb)}>
              <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(201,168,76,0.08)' }}>
                <FileText size={22} style={{ color: '#c9a84c' }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium truncate">{nb.filename}</h3>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="text-xs text-muted-foreground">{nb.page_count} Seiten</span>
                  {nb.chunk_count > 1 && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(201,168,76,0.1)', color: '#c9a84c' }}>{nb.chunk_count} Abschnitte</span>}
                  {nb.word_count > 0 && <span className="text-xs text-muted-foreground">{Math.round(nb.word_count/1000)}k Wörter</span>}
                  <span className="text-xs text-muted-foreground">{new Date(nb.created_at).toLocaleDateString("de-DE")}</span>
                  {nb.topics?.length > 0 && <span className="text-xs" style={{ color: '#c9a84c' }}>{nb.topics.slice(0, 2).join(", ")}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-muted-foreground/30 group-hover:text-[#c9a84c] transition-colors" />
                <button data-testid={`notebook-delete-${nb.id}`}
                  onClick={e => { e.stopPropagation(); deleteNotebook(nb.id); }}
                  className="p-1.5 text-muted-foreground/30 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
