import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";

const MODELS = [
  { id: "deepseek-chat", name: "DeepSeek Chat", provider: "DeepSeek", color: "#4f46e5" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI", color: "#10a37f" },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", color: "#10a37f" },
  { id: "claude-sonnet", name: "Claude Sonnet", provider: "Anthropic", color: "#cc785c" },
  { id: "gemini-flash", name: "Gemini Flash", provider: "Google", color: "#4285f4" },
  { id: "metsu", name: "Metsu", provider: "DeepSeek • Qwen • InternLM", color: "#f59e0b" },
];

const LANGUAGES = [
  { id: "de", name: "Deutsch", flag: "DE" },
  { id: "en", name: "English", flag: "GB" },
  { id: "ar", name: "العربية", flag: "SA" },
  { id: "ru", name: "Русский", flag: "RU" },
  { id: "uk", name: "Українська", flag: "UA" },
];

const FLAG_EMOJI = { DE: "\uD83C\uDDE9\uD83C\uDDEA", GB: "\uD83C\uDDEC\uD83C\uDDE7", SA: "\uD83C\uDDF8\uD83C\uDDE6", RU: "\uD83C\uDDF7\uD83C\uDDFA" };

const PLACEHOLDERS = {
  de: "Schreiben Sie Ihre Frage hier...",
  en: "Type your question here...",
  ar: "...اكتب سؤالك هنا",
  ru: "Напишите свой вопрос здесь...",
};

const GREETINGS = {
  de: "Hallo! Ich bin Ihr medizinischer KI-Tutor mit Zugriff auf tausende Prüfungsfragen.\n\nStellen Sie mir jede beliebige medizinische Frage — ich merke mir den Verlauf und helfe Ihnen Schritt für Schritt.",
  en: "Hello! I'm your medical AI tutor with access to thousands of exam questions.\n\nAsk me any medical question — I remember our conversation and help you step by step.",
  ar: "مرحباً! أنا معلمك الطبي الذكي مع إمكانية الوصول إلى آلاف أسئلة الامتحان.\n\nاسألني أي سؤال طبي — أتذكر محادثتنا وأساعدك خطوة بخطوة.",
  ru: "Здравствуйте! Я ваш медицинский ИИ-репетитор с доступом к тысячам экзаменационных вопросов.\n\nЗадайте любой медицинский вопрос — я помню историю и помогаю шаг за шагом.",
};

export { MODELS, LANGUAGES, FLAG_EMOJI, PLACEHOLDERS, GREETINGS };

export default function useAIChat({ question, isOpen, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("deepseek-chat");
  const [selectedLang, setSelectedLang] = useState("de");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState("");
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const [specialties, setSpecialties] = useState([]);
  const [showSpecialtyPicker, setShowSpecialtyPicker] = useState(false);
  const [documentsCount, setDocumentsCount] = useState(0);
  const [chapters, setChapters] = useState([]);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [showChapterPicker, setShowChapterPicker] = useState(false);
  const [pageViewerDocId, setPageViewerDocId] = useState(null);
  const [pageViewerPage, setPageViewerPage] = useState(null);
  const [pageViewerImages, setPageViewerImages] = useState([]);
  const [showPageViewer, setShowPageViewer] = useState(false);
  const [pageViewerLoading, setPageViewerLoading] = useState(false);
  const [lightboxImage, setLightboxImage] = useState(null);
  const [loadingPhase, setLoadingPhase] = useState("idle");
  const { token } = useAuth();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const isTutor = !question;

  const headers = { Authorization: `Bearer ${token}` };
  const currentModel = MODELS.find(m => m.id === selectedModel) || MODELS[0];
  const currentLang = LANGUAGES.find(l => l.id === selectedLang) || LANGUAGES[0];

  // Fetch conversations on mount (tutor only)
  useEffect(() => {
    if (!isOpen || !isTutor || !token) return;
    setConversationsLoading(true);
    axios.get(`${API}/ai/tutor/conversations`, { headers })
      .then(r => setConversations(r.data.conversations))
      .catch(() => {})
      .finally(() => setConversationsLoading(false));
  }, [isOpen, isTutor, token]);

  // Fetch specialties for document bank filter
  useEffect(() => {
    if (!isOpen || !isTutor || !token) return;
    axios.get(`${API}/specialties`, { headers })
      .then(r => setSpecialties(r.data || []))
      .catch(() => {});
    axios.get(`${API}/tutor/documents`, { headers })
      .then(r => setDocumentsCount(r.data.documents?.length || 0))
      .catch(() => {});
  }, [isOpen, isTutor, token]);

  // Fetch chapters from uploaded documents
  useEffect(() => {
    if (!isOpen || !isTutor || !token) {
      setChapters([]);
      setSelectedChapter(null);
      return;
    }
    axios.get(`${API}/tutor/documents`, { headers })
      .then(r => {
        const docs = r.data.documents || [];
        if (docs.length === 0) { setChapters([]); return null; }
        const docId = docs[0].id;
        return axios.get(`${API}/tutor/documents/${docId}/chapters`, { headers });
      })
      .then(r => {
        if (r && r.data?.chapters) {
          setChapters(r.data.chapters);
        } else {
          setChapters([]);
        }
      })
      .catch(() => setChapters([]));
  }, [isOpen, isTutor, token]);

  // Set greeting for new conversation (no messages loaded)
  useEffect(() => {
    if (!isOpen) return;
    if (isTutor && messages.length === 0 && !loading) {
      setMessages([{ role: "assistant", content: GREETINGS[selectedLang] || GREETINGS.de }]);
    } else if (!isTutor && question && messages.length === 0) {
      const qText = question.question_text_de || question.question_text;
      setMessages([{
        role: "assistant",
        content: `Hallo! Ich helfe Ihnen gerne bei dieser Frage:\n\n"${qText}"\n\nStellen Sie mir eine Frage zu diesem Thema!`,
      }]);
    }
  }, [isOpen, isTutor, question, selectedLang, messages.length, loading]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const startNewConversation = useCallback(() => {
    setConversationId(null);
    setMessages([{ role: "assistant", content: GREETINGS[selectedLang] || GREETINGS.de }]);
    setSelectedChapter(null);
    setChapters([]);
  }, [selectedLang]);

  const loadConversation = useCallback(async (convId) => {
    if (!convId) return;
    setLoading(true);
    try {
      const r = await axios.get(`${API}/ai/tutor/conversations/${convId}`, { headers });
      const conv = r.data;
      setConversationId(conv.id);
      setMessages(conv.messages && conv.messages.length > 0
        ? conv.messages
        : [{ role: "assistant", content: GREETINGS[selectedLang] || GREETINGS.de }]
      );
      setSelectedModel(conv.model || "deepseek-chat");
      setSelectedLang(conv.language || "de");
    } catch (e) {
      console.error("Failed to load conversation", e);
    } finally {
      setLoading(false);
    }
  }, [headers, selectedLang]);

  const deleteConversation = async (convId, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/ai/tutor/conversations/${convId}`, { headers });
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (conversationId === convId) startNewConversation();
    } catch (err) {
      console.error("Failed to delete conversation", err);
    }
  };

  const renameConversation = async (convId) => {
    const title = renameValue.trim();
    if (!title) { setRenamingId(null); return; }
    try {
      await axios.patch(`${API}/ai/tutor/conversations/${convId}/rename`, { title }, { headers });
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, title } : c));
    } catch (err) {
      console.error("Failed to rename conversation", err);
    }
    setRenamingId(null);
  };

  const pinConversation = async (convId, e) => {
    e.stopPropagation();
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    const isPinned = !conv.pinned;
    try {
      const r = await axios.patch(`${API}/ai/tutor/conversations/${convId}/pin`, { pinned: isPinned }, { headers });
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, pinned: r.data.pinned, pin_order: r.data.pin_order } : c));
    } catch (err) {
      console.error("Failed to pin conversation", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setLoadingPhase("generating");

    try {
      const payload = isTutor ? {
        user_message: userMessage,
        model: selectedModel,
        language: selectedLang,
        conversation_id: conversationId,
        specialty_id: selectedSpecialty || null,
        chapter_index: selectedChapter ?? null,
      } : {
        question_id: question.id,
        user_message: userMessage,
        model: selectedModel,
        language: selectedLang,
        context: messages.map(m => `${m.role}: ${m.content}`).join('\n'),
      };
      const endpoint = isTutor ? `${API}/ai/tutor` : `${API}/ai/chat`;
      const response = await axios.post(endpoint, payload, { headers, timeout: 300000 });

      const images = response.data.images || [];
      const docsUsed = response.data.documents_used || 0;
      let content = response.data.response;
      if (isTutor && docsUsed > 0) {
        content = `[Aus ${docsUsed} Dokument(en)]\n\n${content}`;
      }
      setMessages(prev => [...prev, { role: "assistant", content, model: selectedModel, images, documents_used: docsUsed, evidence: response.data.evidence || [], wiki_sources: response.data.wiki_sources || [], mcq_analysis: response.data.mcq_analysis || null }]);

      if (isTutor && response.data.conversation_id) {
        setConversationId(response.data.conversation_id);
        axios.get(`${API}/ai/tutor/conversations`, { headers })
          .then(r => setConversations(r.data.conversations))
          .catch(() => {});
      }
    } catch (error) {
      console.error("AI chat error:", error);
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      const errorMsgs = {
        429: {
          de: detail || "Tägliches KI-Limit erreicht. Bitte morgen weiter.",
          en: detail || "Daily AI limit reached. Please continue tomorrow.",
          ar: "تم الوصول إلى الحد اليومي للذكاء الاصطناعي. يرجى الاستمرار غداً.",
          ru: "Достигнут дневной лимит ИИ. Пожалуйста, продолжите завтра.",
        },
        403: {
          de: detail || "KI-Zugang nicht verfügbar. Testphase möglicherweise abgelaufen.",
          en: detail || "AI access not available. Trial may have expired.",
          ar: detail || "الوصول إلى الذكاء الاصطناعي غير متاح. ربما انتهت الفترة التجريبية.",
          ru: detail || "Доступ к ИИ недоступен. Возможно, пробный период истек.",
        },
        503: {
          de: detail || "KI-Dienst vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut.",
          en: detail || "AI service temporarily unavailable. Please try again later.",
          ar: detail || "خدمة الذكاء الاصطناعي غير متاحة مؤقتًا. يرجى المحاولة مرة أخرى لاحقًا.",
          ru: detail || "Сервис ИИ временно недоступен. Пожалуйста, попробуйте позже.",
        },
        default: {
          de: "Entschuldigung, ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
          en: "Sorry, an error occurred. Please try again.",
          ar: "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.",
          ru: "Извините, произошла ошибка. Пожалуйста, попробуйте снова.",
        },
      };
      const msgMap = errorMsgs[status] || errorMsgs.default;
      setMessages(prev => [...prev, { role: "assistant", content: msgMap[selectedLang] || msgMap.de }]);
    } finally { setLoading(false); setLoadingPhase("idle"); }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const openPageViewer = async (docId, page) => {
    setPageViewerDocId(docId);
    setPageViewerPage(page);
    setPageViewerLoading(true);
    setShowPageViewer(true);
    try {
      const r = await axios.get(`${API}/tutor/documents/${docId}/page/${page}`, { headers });
      setPageViewerImages(r.data.images || []);
    } catch (e) {
      setPageViewerImages([]);
    }
    setPageViewerLoading(false);
  };

  const clearChat = useCallback(() => {
    if (conversationId) {
      axios.delete(`${API}/ai/tutor/conversations/${conversationId}`, { headers })
        .then(() => {
          setConversations(prev => prev.filter(c => c.id !== conversationId));
          startNewConversation();
        })
        .catch(() => startNewConversation());
    } else {
      startNewConversation();
    }
  }, [conversationId, startNewConversation]);

  const toggleModelPicker = useCallback(() => {
    setShowModelPicker(prev => !prev);
    setShowLangPicker(false);
    setShowSpecialtyPicker(false);
    setShowChapterPicker(false);
  }, []);

  const toggleLangPicker = useCallback(() => {
    setShowLangPicker(prev => !prev);
    setShowModelPicker(false);
    setShowSpecialtyPicker(false);
    setShowChapterPicker(false);
  }, []);

  const toggleSpecialtyPicker = useCallback(() => {
    setShowSpecialtyPicker(prev => !prev);
    setShowModelPicker(false);
    setShowLangPicker(false);
    setShowChapterPicker(false);
  }, []);

  const toggleChapterPicker = useCallback(() => {
    setShowChapterPicker(prev => !prev);
    setShowModelPicker(false);
    setShowLangPicker(false);
    setShowSpecialtyPicker(false);
  }, []);

  const closeAllPickers = useCallback(() => {
    setShowModelPicker(false);
    setShowLangPicker(false);
    setShowSpecialtyPicker(false);
    setShowChapterPicker(false);
  }, []);

  const handleModelSelect = useCallback((id) => {
    setSelectedModel(id);
    closeAllPickers();
  }, [closeAllPickers]);

  const handleLangSelect = useCallback((id) => {
    setSelectedLang(id);
    closeAllPickers();
  }, [closeAllPickers]);

  const handleSpecialtySelect = useCallback((id) => {
    setSelectedSpecialty(id);
    closeAllPickers();
  }, [closeAllPickers]);

  const handleChapterSelect = useCallback((idx) => {
    setSelectedChapter(idx);
    closeAllPickers();
  }, [closeAllPickers]);

  const handleStartRename = useCallback((id, title) => {
    setRenamingId(id);
    setRenameValue(title);
  }, []);

  const handleRenameCancel = useCallback(() => {
    setRenamingId(null);
  }, []);

  const sidebarProps = {
    conversations,
    conversationId,
    conversationsLoading,
    renamingId,
    renameValue,
    onSelect: loadConversation,
    onDelete: deleteConversation,
    onRename: renameConversation,
    onPin: pinConversation,
    onNew: startNewConversation,
    onToggle: () => setSidebarOpen(false),
    onStartRename: handleStartRename,
    onRenameValueChange: setRenameValue,
    onRenameCancel: handleRenameCancel,
  };

  const headerProps = {
    isTutor,
    currentModel,
    currentLang,
    selectedModel,
    selectedLang,
    selectedSpecialty,
    selectedChapter,
    chapters,
    specialties,
    showModelPicker,
    showLangPicker,
    showSpecialtyPicker,
    showChapterPicker,
    sidebarOpen,
    conversationId,
    onModelSelect: handleModelSelect,
    onLangSelect: handleLangSelect,
    onSpecialtySelect: handleSpecialtySelect,
    onChapterSelect: handleChapterSelect,
    onToggleSidebar: () => setSidebarOpen(prev => !prev),
    onNewConversation: startNewConversation,
    onClose,
    onModelPickerToggle: toggleModelPicker,
    onLangPickerToggle: toggleLangPicker,
    onSpecialtyPickerToggle: toggleSpecialtyPicker,
    onChapterPickerToggle: toggleChapterPicker,
  };

  const messagesProps = {
    messages,
    loading,
    loadingPhase,
    selectedModel,
    selectedLang,
    currentModel,
    scrollRef,
    onPageViewerOpen: openPageViewer,
    onLightboxOpen: setLightboxImage,
  };

  const inputProps = {
    input,
    loading,
    selectedLang,
    inputRef,
    messagesLength: messages.length,
    onSend: sendMessage,
    onInputChange: (e) => setInput(e.target.value),
    onKeyDown: handleKeyPress,
    onClearChat: clearChat,
  };

  const modalProps = {
    pageViewer: {
      showPageViewer,
      pageViewerDocId,
      pageViewerPage,
      pageViewerImages,
      pageViewerLoading,
      onClose: () => setShowPageViewer(false),
    },
    lightbox: {
      lightboxImage,
      onClose: () => setLightboxImage(null),
    },
  };

  return {
    isTutor,
    sidebarOpen,
    sidebarProps,
    headerProps,
    messagesProps,
    inputProps,
    modalProps,
  };
}
