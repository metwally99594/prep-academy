import { useState, useEffect, useCallback, useRef } from "react";
import DOMPurify from "dompurify";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  ArrowRight, 
  ArrowLeft,
  Heart,
  HeartOff,
  Sparkles,
  Check,
  X,
  Loader2,
  Trophy,
  RotateCcw,
  MessageCircle,
  Clock,
  Download,
  AlertTriangle,
  Share2,
  FileText,
  Flag,
  Save,
  Grid3X3,
  ChevronLeft,
  ChevronRight,
  ListChecks,
  Eye,
  Highlighter,
  Volume2,
  VolumeX,
} from "lucide-react";
import AIChat from "@/components/AIChat";
import ShareResults from "@/components/ShareResults";
import DragDrop from "@/components/questions/DragDrop";
import Luckentext from "@/components/questions/Luckentext";
import MultiSelect from "@/components/questions/MultiSelect";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function QuizPage() {
  const { specialtyId } = useParams();
  const [searchParams] = useSearchParams();
  const year = searchParams.get("year");
  const examLocation = searchParams.get("exam_location");
  const quizMode = searchParams.get("mode") || "study";
  const navigate = useNavigate();
  const { token } = useAuth();

  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedChoices, setSelectedChoices] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [aiExplanation, setAiExplanation] = useState("");
  const [ragExplanation, setRagExplanation] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [aiChatOpen, setAiChatOpen] = useState(false);
  const [quizCompleted, setQuizCompleted] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  
  // Exam mode
  const [timeLeft, setTimeLeft] = useState(60);
  const [totalTimeUsed, setTotalTimeUsed] = useState(0);
  const [shareOpen, setShareOpen] = useState(false);
  const [latestXp, setLatestXp] = useState(0);
  const [latestLevel, setLatestLevel] = useState(null);
  const timerRef = useRef(null);

  // Notes & Reports
  const [noteText, setNoteText] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteSaving, setNoteSaving] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportCategory, setReportCategory] = useState("");
  const [reportDetails, setReportDetails] = useState("");
  const [reportSending, setReportSending] = useState(false);

  // NEW: Question navigation & answer tracking
  const [answers, setAnswers] = useState({}); // { questionIndex: { selectedIds: [], result: {}, submitted: bool } }
  const [dragDropAnswer, setDragDropAnswer] = useState({});
  const [blankAnswer, setBlankAnswer] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [showReview, setShowReview] = useState(false);
  const [highlights, setHighlights] = useState({}); // { questionIndex: [{text, color}] }

  // In-session caches to avoid redundant per-question API calls
  const favoritesCache = useRef({}); // questionId → boolean
  const notesCache = useRef({});     // questionId → string

  // TTS — Read aloud the current question
  const [ttsPlaying, setTtsPlaying] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);
  const ttsAudioRef = useRef(null);

  const speakCurrentQuestion = async () => {
    if (!currentQuestion) return;
    // If already playing → stop
    if (ttsPlaying && ttsAudioRef.current) {
      ttsAudioRef.current.pause();
      ttsAudioRef.current.currentTime = 0;
      setTtsPlaying(false);
      return;
    }
    setTtsLoading(true);
    try {
      const qText = currentQuestion.question_text_de || currentQuestion.question_text || "";
      const choicesText = (currentQuestion.choices || [])
        .map((c, i) => `${String.fromCharCode(65 + i)}. ${c.text_de || c.text || ""}`)
        .join(". ");
      const fullText = `Frage. ${qText}. Antwortmöglichkeiten. ${choicesText}`;
      const res = await axios.post(`${API}/learn/tts/speak`,
        { text: fullText, language: "de" },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 60000 }
      );
      if (!res.data.audio_base64) throw new Error("Kein Audio");
      const audio = new Audio(`data:audio/mp3;base64,${res.data.audio_base64}`);
      ttsAudioRef.current = audio;
      audio.onended = () => setTtsPlaying(false);
      audio.onerror = () => setTtsPlaying(false);
      await audio.play();
      setTtsPlaying(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || "TTS fehlgeschlagen");
    } finally {
      setTtsLoading(false);
    }
  };

  // Stop TTS when navigating to a different question
  useEffect(() => {
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
      ttsAudioRef.current = null;
      setTtsPlaying(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex]);
  const [highlightMode, setHighlightMode] = useState(false);
  const [specNameDe, setSpecNameDe] = useState("");

  const currentQuestion = questions[currentIndex];
  const isExamMode = quizMode === "exam";
  const currentAnswer = answers[currentIndex];

  // Subject-to-RAG-category map (used to filter RAG search to the question's topic)
  const SUBJECT_TO_CATEGORY = {
    kardiologie: "Kardiologie", pneumologie: "Pneumologie", neurologie: "Neurologie",
    gastroenterologie: "Gastroenterologie", chirurgie: "Chirurgie", urologie: "Urologie",
    endokrinologie: "Endokrinologie", notfallmedizin: "Notfallmedizin",
    intensivmedizin: "Intensivmedizin", psychiatrie: "Psychiatrie",
    pharmakologie: "Pharmakologie", orthopaedie: "Orthopädie",
  };

  const explainWithRag = async () => {
    if (!currentQuestion) return;
    setRagLoading(true);
    setRagExplanation(null);
    try {
      const qText = currentQuestion.question_text_de || currentQuestion.question_text || "";
      const choicesBlock = (currentQuestion.choices || [])
        .map((c, i) => `${String.fromCharCode(65 + i)}) ${c.text_de || c.text || ""}${c.is_correct ? " ✓" : ""}`)
        .join("\n");
      const query = `Prüfungsfrage: ${qText}\n\nAntwortmöglichkeiten:\n${choicesBlock}\n\nErkläre die korrekte Antwort klinisch und verweise auf Leitlinien.`;

      const category = SUBJECT_TO_CATEGORY[specialtyId] || null;
      const payload = { query, language: "de", top_k: 4 };
      if (category) payload.filter_category = category;

      const r = await axios.post(`${API}/rag/query`, payload, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 90000,
      });
      setRagExplanation(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "RAG-Erklärung fehlgeschlagen");
    } finally {
      setRagLoading(false);
    }
  };

  // Fetch questions
  useEffect(() => {
    // Fetch specialty German name
    if (specialtyId && specialtyId !== 'custom') {
      axios.get(`${API}/specialties/${specialtyId}`).then(r => setSpecNameDe(r.data.name_de || specialtyId)).catch(() => {});
    }
    const fetchQuestions = async () => {
      try {
        if (specialtyId === "custom") {
          const stored = sessionStorage.getItem("customQuizQuestions");
          if (stored) {
            const rawData = JSON.parse(stored);
            const normalized = rawData.map(q => ({
              ...q,
              choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
              question_text: q.question_text || q.question_text_de || "",
            })).filter(q => {
              const t = q.question_type || 'single_choice';
              if (t === 'drag_drop' || t === 'kategorisierung') return (q.drag_drop_items?.length ?? 0) > 0;
              if (t === 'luckentext') return !!q.blank_text;
              return (q.choices?.length ?? 0) > 0;
            });
            setQuestions(normalized);
            sessionStorage.removeItem("customQuizQuestions");
            setLoading(false);
            return;
          }

          const headers = { Authorization: `Bearer ${token}` };
          const specs = searchParams.get("specs");
          const textQ = searchParams.get("q");
          const yf = searchParams.get("yf");
          const yt = searchParams.get("yt");
          const loc = searchParams.get("loc");
          const fav = searchParams.get("fav");
          const tagsParam = searchParams.get("tags");
          const limit = searchParams.get("limit") || 50;

          const payload = {
            specialties: specs ? specs.split(",") : [],
            text_search: textQ || null,
            year_from: yf ? parseInt(yf) : null,
            year_to: yt ? parseInt(yt) : null,
            exam_location: loc || null,
            favorites_only: fav === "1",
            tags: tagsParam ? tagsParam.split(",") : null,
            limit: parseInt(limit),
            mode: quizMode,
          };

          const res = await axios.post(`${API}/questions/custom-quiz`, payload, { headers });
          const rawData = Array.isArray(res.data) ? res.data : [];
          const normalized = rawData.map(q => ({
            ...q,
            choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
            question_text: q.question_text || q.question_text_de || "",
          })).filter(q => {
            const t = q.question_type || 'single_choice';
            if (t === 'drag_drop' || t === 'kategorisierung') return (q.drag_drop_items?.length ?? 0) > 0;
            if (t === 'luckentext') return !!q.blank_text;
            return (q.choices?.length ?? 0) > 0;
          });
          setQuestions(normalized);
          setLoading(false);
          return;
        }

        const headers = { Authorization: `Bearer ${token}` };
        let params = `specialty_id=${specialtyId}`;
        if (year) params += `&year=${year}`;
        if (examLocation) params += `&exam_location=${examLocation}`;
        const modeParam = isExamMode ? 'exam' : 'study';
        const quizLimit = isExamMode ? 50 : 5000;
        const response = await axios.get(`${API}/questions/quiz?${params}&limit=${quizLimit}&mode=${modeParam}`, { headers });
        const rawData = Array.isArray(response.data) ? response.data : [];
        const normalized = rawData.map(q => ({
          ...q,
          choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
          question_text: q.question_text || q.question_text_de || "",
        })).filter(q => {
          const t = q.question_type || 'single_choice';
          if (t === 'drag_drop' || t === 'kategorisierung') return (q.drag_drop_items?.length ?? 0) > 0;
          if (t === 'luckentext') return !!q.blank_text;
          return (q.choices?.length ?? 0) > 0;
        });
        setQuestions(normalized);
      } catch (error) {
        console.error("Failed to fetch questions:", error);
        toast.error("Fehler beim Laden der Fragen");
      } finally {
        setLoading(false);
      }
    };
    fetchQuestions();
  }, [specialtyId, year, examLocation, token, isExamMode]); // eslint-disable-line

  // Timer for exam mode
  useEffect(() => {
    if (!isExamMode || loading || quizCompleted || (currentAnswer && currentAnswer.submitted)) return;
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          handleTimeUp();
          return 60;
        }
        return prev - 1;
      });
      setTotalTimeUsed(prev => prev + 1);
    }, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isExamMode, currentIndex, loading, quizCompleted]); // eslint-disable-line

  const handleTimeUp = () => {
    // Mark as skipped
    setAnswers(prev => ({
      ...prev,
      [currentIndex]: { selectedIds: [], result: null, submitted: true, correct: false, skipped: true }
    }));
    setScore(prev => ({ ...prev, total: prev.total + 1 }));
    toast.error("Zeit abgelaufen!");
  };

  // Favorites — cached per question to avoid a round-trip on every navigation
  useEffect(() => {
    if (!currentQuestion || !token) return;
    const qId = currentQuestion.id;
    if (qId in favoritesCache.current) {
      setIsFavorite(favoritesCache.current[qId]);
      return;
    }
    axios.get(`${API}/favorites/check/${qId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        favoritesCache.current[qId] = res.data.is_favorite;
        setIsFavorite(res.data.is_favorite);
      })
      .catch(() => {});
  }, [currentQuestion, token]);

  // Notes — cached per question to avoid a round-trip on every navigation
  useEffect(() => {
    setNoteOpen(false);
    if (!currentQuestion || !token) return;
    const qId = currentQuestion.id;
    if (qId in notesCache.current) {
      setNoteText(notesCache.current[qId]);
      return;
    }
    axios.get(`${API}/notes/${qId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        const text = res.data.text || "";
        notesCache.current[qId] = text;
        setNoteText(text);
      })
      .catch(() => { setNoteText(""); });
  }, [currentQuestion, token]);

  // When navigating to a question, restore its state
  useEffect(() => {
    const saved = answers[currentIndex];
    if (saved && saved.submitted) {
      setSelectedChoices(saved.selectedIds || []);
      setDragDropAnswer(saved.dragDropAnswer || {});
      setBlankAnswer(saved.blankAnswer || "");
      setShowResult(true);
      setResult(saved.result);
    } else if (saved) {
      setSelectedChoices(saved.selectedIds || []);
      setDragDropAnswer(saved.dragDropAnswer || {});
      setBlankAnswer(saved.blankAnswer || "");
      setShowResult(false);
      setResult(null);
    } else {
      setSelectedChoices([]);
      setDragDropAnswer({});
      setBlankAnswer("");
      setShowResult(false);
      setResult(null);
    }
    setAiExplanation("");
    setRagExplanation(null);
    setNoteOpen(false);
    setReportOpen(false);
    if (isExamMode && !(saved && saved.submitted)) setTimeLeft(60);
  }, [currentIndex]); // eslint-disable-line

  const goToQuestion = (idx) => {
    if (idx >= 0 && idx < questions.length) {
      if (!answers[currentIndex]?.submitted) {
        const hasProgress = selectedChoices.length > 0 || Object.keys(dragDropAnswer).length > 0 || blankAnswer.length > 0;
        if (hasProgress) {
          setAnswers(prev => ({
            ...prev,
            [currentIndex]: { ...prev[currentIndex], selectedIds: selectedChoices, dragDropAnswer, blankAnswer, submitted: false }
          }));
        }
      }
      if (timerRef.current) clearInterval(timerRef.current);
      setCurrentIndex(idx);
    }
  };

  const saveNote = async () => {
    if (!currentQuestion) return;
    setNoteSaving(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/notes`, { question_id: currentQuestion.id, text: noteText }, { headers });
      notesCache.current[currentQuestion.id] = noteText;
      toast.success("Notiz gespeichert");
      setNoteOpen(false);
    } catch { toast.error("Fehler beim Speichern"); }
    finally { setNoteSaving(false); }
  };

  const submitReport = async () => {
    if (!currentQuestion || !reportCategory) return;
    setReportSending(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/reports`, {
        question_id: currentQuestion.id, category: reportCategory, details: reportDetails,
        question_text: currentQuestion.question_text_de || currentQuestion.question_text || "",
      }, { headers });
      toast.success("Problem gemeldet. Danke!");
      setReportOpen(false); setReportCategory(""); setReportDetails("");
    } catch { toast.error("Fehler beim Senden"); }
    finally { setReportSending(false); }
  };

  const toggleChoice = (choiceId) => {
    if (showResult) return;
    const qType = currentQuestion?.question_type || 'single_choice';
    const isMulti = qType === 'multi_select' || (currentQuestion?.choices?.filter(c => c.is_correct === true)?.length || 1) > 1;
    if (isMulti) {
      setSelectedChoices(prev => prev.includes(choiceId) ? prev.filter(id => id !== choiceId) : [...prev, choiceId]);
    } else {
      setSelectedChoices([choiceId]);
    }
  };

  const submitAnswer = async () => {
    const qType = currentQuestion?.question_type || 'single_choice';
    const isDragDrop = qType === 'drag_drop' || qType === 'kategorisierung';
    const isLuckentext = qType === 'luckentext';

    if (isDragDrop && Object.keys(dragDropAnswer).length === 0) {
      toast.error("Bitte ordne mindestens einen Begriff zu"); return;
    }
    if (isLuckentext && !blankAnswer.trim()) {
      toast.error("Bitte fülle die Lücke aus"); return;
    }
    if (!isDragDrop && !isLuckentext && selectedChoices.length === 0) {
      toast.error("Bitte wählen Sie mindestens eine Antwort"); return;
    }

    if (timerRef.current) clearInterval(timerRef.current);
    setSubmitting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const payload = { question_id: currentQuestion.id };
      if (isDragDrop) {
        payload.drag_drop_answer = dragDropAnswer;
      } else if (isLuckentext) {
        try {
          const parsed = JSON.parse(blankAnswer);
          const sorted = Object.keys(parsed).sort((a, b) => parseInt(a) - parseInt(b)).map(k => parsed[k] || "");
          payload.blank_answers = sorted;
          payload.blank_answer = sorted[0] || "";
        } catch {
          payload.blank_answer = blankAnswer;
        }
      } else payload.selected_choice_ids = selectedChoices;

      const response = await axios.post(`${API}/questions/${currentQuestion.id}/answer`, payload, { headers });
      setResult(response.data);
      setShowResult(true);
      if (response.data.total_xp !== undefined) setLatestXp(response.data.total_xp);
      if (response.data.level) setLatestLevel(response.data.level);
      const isCorrect = response.data.is_correct;
      setScore(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }));

      setAnswers(prev => ({
        ...prev,
        [currentIndex]: {
          selectedIds: selectedChoices,
          dragDropAnswer,
          blankAnswer,
          result: response.data,
          submitted: true,
          correct: isCorrect,
          skipped: false,
        }
      }));

      if (isCorrect) {
        const xpMsg = response.data.xp_earned ? ` +${response.data.xp_earned} XP` : '';
        toast.success(`Richtig!${xpMsg}`);
      } else {
        const xpMsg = response.data.xp_earned ? ` +${response.data.xp_earned} XP` : '';
        toast.error(`Falsch${xpMsg}`);
      }
      if (response.data.leveled_up && response.data.level) {
        setTimeout(() => toast.success(`Level Up! Du bist jetzt ${response.data.level.name_de}!`, { duration: 4000 }), 500);
      }
    } catch (error) {
      console.error("Failed to submit answer:", error);
      toast.error("Fehler beim Senden der Antwort");
    } finally { setSubmitting(false); }
  };

  const finishQuiz = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setQuizCompleted(true);
    setShowReview(true);
  };

  const restartQuiz = () => {
    setCurrentIndex(0); setSelectedChoices([]); setDragDropAnswer({}); setBlankAnswer("");
    setShowResult(false); setResult(null);
    setAiExplanation("");
    setRagExplanation(null); setQuizCompleted(false); setScore({ correct: 0, total: 0 });
    setTimeLeft(60); setTotalTimeUsed(0); setAnswers({}); setShowReview(false);
  };

  const toggleFavorite = async () => {
    if (!currentQuestion) return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const newVal = !isFavorite;
      if (isFavorite) { await axios.delete(`${API}/favorites/${currentQuestion.id}`, { headers }); toast.success("Aus Favoriten entfernt"); }
      else { await axios.post(`${API}/favorites`, { question_id: currentQuestion.id }, { headers }); toast.success("Zu Favoriten hinzugefügt"); }
      favoritesCache.current[currentQuestion.id] = newVal;
      setIsFavorite(newVal);
    } catch { toast.error("Fehler beim Aktualisieren der Favoriten"); }
  };

  const getAIExplanation = async () => {
    if (!currentQuestion) return;
    setLoadingAI(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.post(`${API}/ai/explain`, { question_id: currentQuestion.id }, { headers });
      setAiExplanation(response.data.explanation);
    } catch { toast.error("Fehler beim Abrufen der KI-Erklärung"); }
    finally { setLoadingAI(false); }
  };

  const getChoiceClass = useCallback((choice) => {
    if (!showResult) return selectedChoices.includes(choice.id) ? "selected" : "";
    if (result?.correct_choice_ids?.includes(choice.id)) return "correct";
    if (selectedChoices.includes(choice.id) && !result?.correct_choice_ids?.includes(choice.id)) return "incorrect";
    return "";
  }, [showResult, selectedChoices, result]);

  // Text highlighting handler
  const handleTextSelect = useCallback(() => {
    if (!highlightMode) return;
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 1) {
      setHighlights(prev => ({
        ...prev,
        [currentIndex]: [...(prev[currentIndex] || []), { text, color: '#3b82f6' }]
      }));
      selection.removeAllRanges();
      toast.success("Markiert!");
    }
  }, [highlightMode, currentIndex]);

  const clearHighlights = () => {
    setHighlights(prev => ({ ...prev, [currentIndex]: [] }));
    toast.success("Markierungen gelöscht");
  };

  // Render text with highlights — output is sanitized before injection
  const renderHighlightedText = (rawText) => {
    if (!rawText) return "";
    const safe = DOMPurify.sanitize(rawText, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
    const qHighlights = highlights[currentIndex] || [];
    if (qHighlights.length === 0) return safe;
    let result = safe;
    qHighlights.forEach(h => {
      const escaped = DOMPurify.sanitize(h.text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
        .replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      result = result.replace(new RegExp(`(${escaped})`, 'gi'), `<mark style="background:rgba(59,130,246,0.3);padding:1px 2px;border-radius:3px;">$1</mark>`);
    });
    return DOMPurify.sanitize(result, { ALLOWED_TAGS: ['mark'], ALLOWED_ATTR: ['style'] });
  };

  const canSubmit = () => {
    const qType = currentQuestion?.question_type || 'single_choice';
    if (qType === 'drag_drop' || qType === 'kategorisierung') return Object.keys(dragDropAnswer).length > 0;
    if (qType === 'luckentext') return blankAnswer.trim().length > 0;
    return selectedChoices.length > 0;
  };

  // Counts
  const answeredCount = Object.values(answers).filter(a => a.submitted).length;
  const correctCount = currentQuestion?.choices?.filter(c => c.is_correct === true)?.length || 1;
  const wrongAnswers = Object.entries(answers).filter(([, a]) => a.submitted && !a.correct && !a.skipped);

  if (loading) return <div className="flex items-center justify-center min-h-[60vh]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;

  if (questions.length === 0) return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="empty-state glass-card rounded-2xl">
        <X className="w-16 h-16 text-muted-foreground" />
        <h2 className="text-xl font-semibold mt-4">Keine Fragen</h2>
        <p className="text-muted-foreground">Für dieses Fachgebiet wurden noch keine Fragen hinzugefügt</p>
        <Link to={`/specialty/${specialtyId}`}><Button className="mt-6">Zurück</Button></Link>
      </div>
    </div>
  );

  // ═══ REVIEW SCREEN ═══
  if (quizCompleted && showReview) {
    const percentage = score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0;
    return (
      <div className="max-w-5xl mx-auto px-4 py-8" data-testid="review-screen">
        {/* Score Summary */}
        <div className="glass-card rounded-2xl p-8 text-center mb-8">
          <Trophy className="w-12 h-12 mx-auto mb-4" style={{ color: '#3b82f6' }} />
          <h2 className="text-3xl font-bold mb-2" data-testid="quiz-complete-title">
            {isExamMode ? "Prüfung beendet!" : "Quiz beendet!"}
          </h2>
          <div className="text-5xl font-bold mb-2" style={{ color: '#3b82f6' }} data-testid="quiz-score">{percentage}%</div>
          <p className="text-lg text-muted-foreground">{score.correct} von {score.total} richtig</p>

          {isExamMode && (
            <div className="grid grid-cols-3 gap-4 my-6 max-w-md mx-auto">
              <div className="p-3 bg-muted rounded-xl">
                <div className="text-xl font-bold">{Math.floor(totalTimeUsed / 60)}:{(totalTimeUsed % 60).toString().padStart(2, '0')}</div>
                <div className="text-xs text-muted-foreground">Gesamtzeit</div>
              </div>
              <div className="p-3 bg-muted rounded-xl">
                <div className="text-xl font-bold">{Math.round(totalTimeUsed / Math.max(score.total, 1))}s</div>
                <div className="text-xs text-muted-foreground">Ø pro Frage</div>
              </div>
              <div className="p-3 bg-muted rounded-xl">
                <div className="text-xl font-bold text-amber-500">{Object.values(answers).filter(a => a.skipped).length}</div>
                <div className="text-xs text-muted-foreground">Übersprungen</div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <Button onClick={restartQuiz} variant="outline" className="gap-2" data-testid="restart-quiz-btn">
              <RotateCcw className="w-4 h-4" /> Wiederholen
            </Button>
            <Button onClick={() => setShareOpen(true)} className="gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="share-results-btn">
              <Share2 className="w-4 h-4" /> Teilen
            </Button>
            <Link to={specialtyId === 'custom' ? '/custom-quiz' : `/specialty/${specialtyId}`}>
              <Button variant="outline" className="gap-2"><ArrowLeft className="w-4 h-4" /> Zurück</Button>
            </Link>
          </div>
          <ShareResults score={score.correct} total={score.total} specialty={specialtyId} level={latestLevel} xp={latestXp} isOpen={shareOpen} onClose={() => setShareOpen(false)} />
        </div>

        {/* Question Grid Overview */}
        <div className="glass-card rounded-2xl p-6 mb-8">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Grid3X3 className="w-5 h-5" /> Alle Fragen</h3>
          <div className="flex flex-wrap gap-2">
            {questions.map((_, idx) => {
              const a = answers[idx];
              let bg = 'bg-muted text-muted-foreground';
              if (a?.submitted && a.correct) bg = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
              if (a?.submitted && !a.correct && !a.skipped) bg = 'bg-red-500/20 text-red-400 border-red-500/30';
              if (a?.skipped) bg = 'bg-amber-500/20 text-amber-400 border-amber-500/30';
              return (
                <button key={idx} onClick={() => { setQuizCompleted(false); setShowReview(false); goToQuestion(idx); }}
                  className={`w-10 h-10 rounded-lg text-sm font-mono font-semibold border transition-all hover:scale-105 ${bg}`}>
                  {idx + 1}
                </button>
              );
            })}
          </div>
        </div>

        {/* Wrong Answers Review */}
        {wrongAnswers.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <X className="w-5 h-5 text-red-400" />
              Falsche Antworten ({wrongAnswers.length})
            </h3>
            {wrongAnswers.map(([idx, a]) => {
              const q = questions[parseInt(idx)];
              if (!q) return null;
              const qType = q.question_type || 'single_choice';
              const choices = q.choices || [];
              return (
                <div key={idx} className="glass-card rounded-xl p-5 border-l-4 border-red-500/40" data-testid={`review-wrong-${idx}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }}>Frage {parseInt(idx) + 1}</span>
                    {q.year && <span className="text-xs text-muted-foreground">{q.year}</span>}
                    {(qType !== 'single_choice') && (
                      <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">{qType}</span>
                    )}
                  </div>
                  <p className="font-medium mb-3 text-sm">{q.question_text_de || q.question_text}</p>

                  {/* drag_drop / kategorisierung review */}
                  {(qType === 'drag_drop' || qType === 'kategorisierung') && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Richtige Zuordnung:</p>
                      {(q.drag_drop_items || []).map(item => {
                        const correctCat = (q.drag_drop_categories || []).find(c => c.id === item.correct_category);
                        const userCatId = a.dragDropAnswer?.[item.id];
                        const userCat = (q.drag_drop_categories || []).find(c => c.id === userCatId);
                        const itemCorrect = userCatId === item.correct_category;
                        return (
                          <div key={item.id} className={`flex items-center gap-2 p-2 rounded-lg text-xs border ${itemCorrect ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                            {itemCorrect ? <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" /> : <X className="w-3 h-3 text-red-400 flex-shrink-0" />}
                            <span className="font-medium">{item.text}</span>
                            <span className="text-muted-foreground">→</span>
                            <span className="text-emerald-400 font-medium">{correctCat?.text || '?'}</span>
                            {!itemCorrect && userCat && (
                              <span className="text-red-400 ml-auto">(du: {userCat.text})</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* luckentext review */}
                  {qType === 'luckentext' && (
                    <div className="space-y-2">
                      <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-sm">
                        <span className="text-muted-foreground">Deine Antwort: </span>
                        <span className="text-red-400 font-semibold line-through">{a.blankAnswer || '—'}</span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-sm">
                        <span className="text-muted-foreground">Richtige Antwort: </span>
                        <span className="text-emerald-400 font-semibold">{(q.blank_answers || []).join(' / ')}</span>
                      </div>
                    </div>
                  )}

                  {/* single_choice / multi_select review */}
                  {(qType === 'single_choice' || qType === 'multi_select') && (
                    <div className="space-y-2">
                      {choices.map((c, ci) => {
                        const isCorrectChoice = a.result?.correct_choice_ids?.includes(c.id) || c.is_correct;
                        const wasSelected = (a.selectedIds || []).includes(c.id);
                        let cls = 'bg-muted/30 border-transparent';
                        if (isCorrectChoice) cls = 'bg-emerald-500/10 border-emerald-500/30';
                        if (wasSelected && !isCorrectChoice) cls = 'bg-red-500/10 border-red-500/30';
                        return (
                          <div key={c.id} className={`flex items-center gap-3 p-2.5 rounded-lg border text-sm ${cls}`}>
                            <span className={`w-6 h-6 rounded flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                              isCorrectChoice ? 'bg-emerald-500 text-white' : wasSelected ? 'bg-red-500 text-white' : 'bg-muted text-muted-foreground'
                            }`}>
                              {isCorrectChoice ? <Check className="w-3 h-3" /> : wasSelected ? <X className="w-3 h-3" /> : String.fromCharCode(65 + ci)}
                            </span>
                            <span className={isCorrectChoice ? 'font-medium' : ''}>{c.text_de || c.text}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {a.result?.explanation && (
                    <div className="mt-3 p-3 rounded-lg bg-muted/30 text-xs text-muted-foreground">
                      <strong>Erklärung:</strong> {a.result.explanation}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ═══ MAIN QUIZ VIEW ═══
  return (
    <div className="flex min-h-[calc(100vh-4rem)]" data-testid="quiz-page">
      {/* ═══ SIDEBAR - Question Grid ═══ */}
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0 md:w-0 md:overflow-hidden'} fixed md:relative top-0 left-0 h-full md:h-auto w-64 md:w-56 lg:w-60 flex-shrink-0 transition-[transform,width] duration-300 z-40 md:z-auto bg-background md:bg-transparent border-r md:border-0 border-border/30 overflow-y-auto`}>
        <div className="sticky top-20 p-3 space-y-3">
          {/* Progress header */}
          <div className="text-xs text-muted-foreground font-mono">
            FORTSCHRITT: {answeredCount}/{questions.length}
          </div>
          <Progress value={(answeredCount / questions.length) * 100} className="h-1.5" style={{ background: 'hsl(var(--muted))' }} />

          {/* Specialty name */}
          <div className="text-sm font-semibold" style={{ color: '#3b82f6' }}>
            {specialtyId === 'custom' ? 'Eigene Auswahl' : (specNameDe || specialtyId)}
            <div className="text-xs text-muted-foreground font-normal">{answeredCount}/{questions.length}</div>
          </div>

          {/* Question grid */}
          <div className="flex flex-wrap gap-1.5" data-testid="question-grid">
            {questions.map((_, idx) => {
              const a = answers[idx];
              const isCurrent = idx === currentIndex;
              let bg = 'bg-muted/50 text-muted-foreground hover:bg-muted';
              if (a?.submitted && a.correct) bg = 'bg-emerald-500/20 text-emerald-400';
              if (a?.submitted && !a.correct && !a.skipped) bg = 'bg-red-500/20 text-red-400';
              if (a?.skipped) bg = 'bg-amber-500/20 text-amber-400';
              if (isCurrent) bg += ' ring-2 ring-[#3b82f6]';
              return (
                <button key={idx} onClick={() => goToQuestion(idx)}
                  className={`w-8 h-8 rounded-md text-xs font-mono font-semibold transition-all ${bg}`}
                  data-testid={`grid-btn-${idx}`}>
                  {idx + 1}
                </button>
              );
            })}
          </div>

          {/* Finish button */}
          {answeredCount > 0 && (
            <Button onClick={finishQuiz} size="sm" className="w-full gap-2 mt-2" variant="outline" data-testid="finish-quiz-btn">
              <ListChecks className="w-4 h-4" /> Auswertung
            </Button>
          )}
        </div>
      </div>

      {/* Toggle sidebar button */}
      <button onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed left-0 top-1/2 -translate-y-1/2 z-30 w-6 h-16 bg-muted/80 backdrop-blur rounded-r-lg flex items-center justify-center hover:bg-muted transition-colors"
        data-testid="toggle-sidebar-btn">
        {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Grid3X3 className="w-4 h-4" />}
      </button>

      {/* ═══ MAIN CONTENT ═══ */}
      <div className="flex-1 max-w-4xl mx-auto px-4 py-6">
        {/* Timer warning */}
        {isExamMode && timeLeft <= 10 && !showResult && !(currentAnswer?.submitted) && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-2 text-red-600 animate-pulse">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Nur noch {timeLeft} Sekunden!</span>
          </div>
        )}

        {/* Top bar: navigation + timer */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => goToQuestion(currentIndex - 1)} disabled={currentIndex === 0} data-testid="prev-btn">
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm font-mono text-muted-foreground">
              F{currentIndex + 1} / {questions.length}
            </span>
            <Button variant="ghost" size="sm" onClick={() => goToQuestion(currentIndex + 1)} disabled={currentIndex >= questions.length - 1} data-testid="next-btn">
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-3">
            {isExamMode && !(currentAnswer?.submitted) && (
              <div className={`timer-pill ${timeLeft <= 10 ? '!bg-red-500/20 !text-red-600 !border-red-500/30' : ''}`}>
                <Clock className="w-3.5 h-3.5" /><span>{timeLeft}s</span>
              </div>
            )}
            <Button variant="ghost" size="icon" onClick={toggleFavorite} className={isFavorite ? "text-red-500" : ""} data-testid="favorite-btn">
              {isFavorite ? <Heart className="w-5 h-5 fill-current" /> : <HeartOff className="w-5 h-5" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setReportOpen(true)} data-testid="report-toggle-btn">
              <Flag className="w-4 h-4" />
            </Button>
          </div>
        </div>

          {/* Question Card */}
        <div className="quiz-card mb-4">
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            {currentQuestion?.year && <span className="quiz-year-badge">{currentQuestion.year}</span>}
            {currentQuestion?.tags?.map(t => <span key={t} className="px-2 py-0.5 bg-muted text-xs rounded-md text-muted-foreground">{t}</span>)}
            {correctCount > 1 && <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-xs rounded-lg font-medium">{correctCount} richtige</span>}
            <button
              onClick={speakCurrentQuestion}
              disabled={ttsLoading}
              className={`ml-auto inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${ttsPlaying ? 'bg-amber-500 text-amber-950' : 'bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground'}`}
              title={ttsPlaying ? "Stop" : "Frage vorlesen"}
              data-testid="tts-speak-btn"
            >
              {ttsLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : ttsPlaying ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{ttsPlaying ? "Stop" : "Vorlesen"}</span>
            </button>
          </div>

          {currentQuestion?.question_type !== 'luckentext' && (
            <h2 className="question-text select-text" data-testid="question-text"
              onMouseUp={handleTextSelect}
              dangerouslySetInnerHTML={{ __html: renderHighlightedText(currentQuestion?.question_text_de || currentQuestion?.question_text || "") }}
            />
          )}

          {currentQuestion?.image_base64 && (
            <div className="mb-6"><img src={currentQuestion.image_base64} alt="Question" className="question-image mx-auto" /></div>
          )}

          {/* Answer area – rendered by question type */}
          {(currentQuestion?.question_type === 'drag_drop' || currentQuestion?.question_type === 'kategorisierung') ? (
            <DragDrop
              question={currentQuestion}
              submitted={showResult}
              answer={dragDropAnswer}
              onChange={setDragDropAnswer}
              result={result}
            />
          ) : currentQuestion?.question_type === 'luckentext' ? (
            <Luckentext
              question={currentQuestion}
              submitted={showResult}
              answer={blankAnswer}
              onChange={setBlankAnswer}
              result={result}
            />
          ) : currentQuestion?.question_type === 'multi_select' ? (
            <MultiSelect
              question={currentQuestion}
              submitted={showResult}
              selectedChoices={selectedChoices}
              onToggle={toggleChoice}
              result={result}
            />
          ) : (
            <div className="answers-container">
              {(currentQuestion?.choices || []).map((choice, index) => (
                <button key={choice.id} onClick={() => toggleChoice(choice.id)} disabled={showResult}
                  className={`answer-option ${getChoiceClass(choice)}`}
                  data-testid={`choice-${index}`}>
                  <div className="answer-circle">
                    {getChoiceClass(choice) === "correct" ? <Check className="w-4 h-4" />
                    : getChoiceClass(choice) === "incorrect" ? <X className="w-4 h-4" />
                    : String.fromCharCode(65 + index)}
                  </div>
                  <p className="answer-text select-text" onMouseUp={handleTextSelect}
                    dangerouslySetInnerHTML={{ __html: renderHighlightedText(choice.text_de || choice.text || "") }} />
                </button>
              ))}
            </div>
          )}

          {/* Inline result feedback */}
          {showResult && result && (
            <div className={`quiz-feedback ${result.is_correct ? 'correct' : 'incorrect'}`}>
              {result.is_correct
                ? <Check className="quiz-feedback-icon" />
                : <X className="quiz-feedback-icon" />
              }
              <div className="quiz-feedback-text">
                {result.is_correct
                  ? <strong>✓ Richtig!</strong>
                  : (
                    <>✗ Falsch. Richtige Antwort: <strong>
                      {(() => {
                        if (currentQuestion?.blank_answers?.length) {
                          return currentQuestion.blank_answers.join(', ');
                        }
                        if (!result?.correct_choice_ids?.length) return '';
                        const correctChoices = (currentQuestion?.choices || []).filter(c => result.correct_choice_ids.includes(c.id));
                        return correctChoices.map(c => {
                          const idx = (currentQuestion?.choices || []).indexOf(c);
                          return `${String.fromCharCode(65 + idx)}) ${c.text_de || c.text || ''}`;
                        }).join(', ');
                      })()}
                    </strong></>
                  )
                }
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          {!(currentAnswer?.submitted) ? (
            <Button onClick={submitAnswer} size="lg" className="w-full sm:w-auto gap-2" disabled={submitting || !canSubmit()} data-testid="submit-answer-btn">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Antwort bestätigen
            </Button>
          ) : (
            <Button onClick={() => { if (currentIndex < questions.length - 1) goToQuestion(currentIndex + 1); else finishQuiz(); }}
              size="lg" className="w-full sm:w-auto gap-2" data-testid="next-question-btn">
              {currentIndex < questions.length - 1 ? "Nächste Frage" : "Auswertung"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}

          <div className="flex gap-2 w-full sm:w-auto">
            <Button variant="outline" onClick={() => setAiChatOpen(true)} className="flex-1 sm:flex-none gap-2" data-testid="ai-chat-btn">
              <MessageCircle className="w-4 h-4" /> KI fragen
            </Button>
            {showResult && (
              <Button variant="outline" onClick={getAIExplanation} disabled={loadingAI} className="flex-1 sm:flex-none gap-2" data-testid="ai-explain-btn">
                {loadingAI ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Erklärung
              </Button>
            )}
          </div>
        </div>

        {/* Note & Highlight bar */}
        <div className="flex gap-2 mt-3 flex-wrap">
          <button onClick={() => setNoteOpen(!noteOpen)} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/40 hover:bg-muted transition-colors text-sm" data-testid="note-toggle-btn">
            <FileText className="w-4 h-4" /> {noteText ? "Notiz bearbeiten" : "Notiz"}
          </button>
          <button onClick={() => setHighlightMode(!highlightMode)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm ${highlightMode ? 'bg-[#3b82f6]/20 text-[#3b82f6]' : 'bg-muted/40 hover:bg-muted'}`}
            data-testid="highlight-toggle-btn">
            <Highlighter className="w-4 h-4" /> {highlightMode ? "Markieren: AN" : "Markieren"}
          </button>
          {(highlights[currentIndex]?.length > 0) && (
            <button onClick={clearHighlights} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors text-sm" data-testid="clear-highlights-btn">
              <X className="w-3 h-3" /> Löschen
            </button>
          )}
        </div>

        {noteOpen && (
          <div className="mt-3 glass-card rounded-xl p-4 animate-fadeIn" data-testid="note-editor">
            <Textarea value={noteText} onChange={e => setNoteText(e.target.value)} placeholder="Persönliche Notiz..." className="min-h-[80px] text-sm mb-3" data-testid="note-textarea" />
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setNoteOpen(false)}>Abbrechen</Button>
              <Button size="sm" onClick={saveNote} disabled={noteSaving} className="gap-1" data-testid="save-note-btn">
                {noteSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Speichern
              </Button>
            </div>
          </div>
        )}

        {/* Explanation */}
        {showResult && (result?.explanation || aiExplanation || ragExplanation) && (
          <div className="mt-4 space-y-3">
            {result?.explanation && (
              <div className="glass-card rounded-xl p-5">
                <h3 className="font-semibold mb-2 flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500" /> Erklärung</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{result.explanation}</p>
              </div>
            )}
            {aiExplanation && (
              <div className="glass-card rounded-xl p-5 border-l-4 border-[#3b82f6]/30">
                <h3 className="font-semibold mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4" style={{ color: '#3b82f6' }} /> KI-Erklärung</h3>
                <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-line">{aiExplanation}</p>
              </div>
            )}
            {ragExplanation && (
              <div className="glass-card rounded-xl p-5 border-l-4 border-amber-500/50" data-testid="quiz-rag-explanation">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-500" /> RAG-Erklärung (mit Leitlinien-Zitaten)
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-line">
                  {(ragExplanation.answer || "").split(/(\[\d+\])/g).map((p, i) =>
                    /^\[\d+\]$/.test(p) ? <sup key={i} className="font-bold text-amber-500 ml-0.5">{p}</sup> : <span key={i}>{p}</span>
                  )}
                </p>
                {ragExplanation.sources?.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-border/50 space-y-1.5">
                    {ragExplanation.sources.map((s) => (
                      <div key={s.index} className="text-xs bg-muted/40 rounded p-2" data-testid={`quiz-rag-source-${s.index}`}>
                        <span className="font-bold text-amber-500">[{s.index}]</span>{" "}
                        <span className="font-semibold">{s.source}</span>
                        {s.code && <span className="text-muted-foreground ml-1">{s.code}</span>}
                        <p className="text-muted-foreground mt-1">{s.excerpt}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* RAG Explain Button — only after the user answered (and only if advanced features enabled) */}
        {showResult && !ragExplanation && process.env.REACT_APP_ADVANCED === "true" && (
          <div className="mt-4">
            <Button
              onClick={explainWithRag}
              disabled={ragLoading}
              variant="outline"
              className="gap-2 border-amber-500/40 hover:bg-amber-500/5"
              data-testid="quiz-explain-rag-btn"
            >
              {ragLoading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> RAG sucht Leitlinien...</>
              ) : (
                <><Sparkles className="w-4 h-4 text-amber-500" /> Mit RAG erklären (mit Zitaten)</>
              )}
            </Button>
          </div>
        )}

        {/* Report Dialog */}
        <Dialog open={reportOpen} onOpenChange={setReportOpen}>
          <DialogContent className="sm:max-w-md" data-testid="report-dialog">
            <DialogHeader><DialogTitle className="flex items-center gap-2"><Flag className="w-5 h-5 text-red-500" /> Problem melden</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2" data-testid="report-categories">
                {["Falsche Antwort", "Fehlerhaft", "Duplikat", "Tippfehler", "Unklar", "Erklärung fehlt", "Falsches Thema", "Sonstiges"].map(cat => (
                  <button key={cat} onClick={() => setReportCategory(cat)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${reportCategory === cat ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}
                    data-testid={`report-cat-${cat}`}>{cat}</button>
                ))}
              </div>
              <Textarea value={reportDetails} onChange={e => setReportDetails(e.target.value)} placeholder="Weitere Details (optional)..." className="min-h-[80px] text-sm" data-testid="report-details" />
              <div className="flex gap-2 justify-end">
                <Button variant="ghost" onClick={() => setReportOpen(false)}>Abbrechen</Button>
                <Button onClick={submitReport} disabled={!reportCategory || reportSending} className="gap-1" data-testid="report-submit-btn">
                  {reportSending ? <Loader2 className="w-3 h-3 animate-spin" /> : null} Senden
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <AIChat question={currentQuestion} isOpen={aiChatOpen} onClose={() => setAiChatOpen(false)} />
      </div>
    </div>
  );
}
