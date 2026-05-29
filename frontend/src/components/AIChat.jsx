import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import axios from "axios";
import { API, useAuth } from "@/App";
import {
  Sparkles, Send, X, Loader2, Bot, User, ChevronDown, Globe, BookOpen,
  Plus, MessageSquare, Trash2, Pencil, Check, PanelLeftClose, PanelLeft, Database,
} from "lucide-react";

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

export default function AIChat({ question, isOpen, onClose }) {
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
  const [documentsCount, setDocumentsCount] = useState(0);
  const [chapters, setChapters] = useState([]);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [showChapterPicker, setShowChapterPicker] = useState(false);
  const { token } = useAuth();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const isTutor = !question;

  const currentModel = MODELS.find(m => m.id === selectedModel) || MODELS[0];
  const currentLang = LANGUAGES.find(l => l.id === selectedLang) || LANGUAGES[0];

  const headers = { Authorization: `Bearer ${token}` };

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
        // Fetch chapters from the most recent document
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

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // Start a new conversation
  const startNewConversation = useCallback(() => {
    setConversationId(null);
    setMessages([{ role: "assistant", content: GREETINGS[selectedLang] || GREETINGS.de }]);
    setSelectedChapter(null);
    setChapters([]);
  }, [selectedLang]);

  // Load a conversation from backend
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

  // Delete a conversation
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

  // Rename a conversation
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

  // Send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

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
      setMessages(prev => [...prev, { role: "assistant", content, model: selectedModel, images, documents_used: docsUsed }]);

      if (isTutor && response.data.conversation_id) {
        setConversationId(response.data.conversation_id);
        // Refresh conversation list
        axios.get(`${API}/ai/tutor/conversations`, { headers })
          .then(r => setConversations(r.data.conversations))
          .catch(() => {});
      }
    } catch (error) {
      console.error("AI chat error:", error);
      const errorMsgs = {
        de: "Entschuldigung, ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
        en: "Sorry, an error occurred. Please try again.",
        ar: "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.",
        ru: "Извините, произошла ошибка. Пожалуйста, попробуйте снова.",
      };
      setMessages(prev => [...prev, { role: "assistant", content: errorMsgs[selectedLang] || errorMsgs.de }]);
    } finally { setLoading(false); }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-6xl h-[85vh] min-h-[500px] max-h-[90vh] rounded-2xl border shadow-2xl flex overflow-hidden animate-fadeIn"
        style={{ background: '#0c1229', borderColor: 'rgba(59,130,246,0.15)' }}>

        {/* ── Sidebar (tutor only) ── */}
        {isTutor && sidebarOpen && (
          <div className="w-64 flex-shrink-0 border-r flex flex-col" style={{ borderColor: 'rgba(59,130,246,0.1)', background: 'rgba(0,0,0,0.15)' }}>
            <div className="flex items-center justify-between px-3 py-3 border-b" style={{ borderColor: 'rgba(59,130,246,0.1)' }}>
              <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Verlauf</span>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" className="w-7 h-7" onClick={startNewConversation} title="Neue Konversation">
                  <Plus className="w-4 h-4 text-white/60" />
                </Button>
                <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => setSidebarOpen(false)} title="Sidebar ausblenden">
                  <PanelLeftClose className="w-4 h-4 text-white/40" />
                </Button>
              </div>
            </div>
            <ScrollArea className="flex-1 p-2">
              {conversationsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-white/30" />
                </div>
              ) : conversations.length === 0 ? (
                <p className="text-xs text-white/30 text-center py-8">Noch keine Konversationen</p>
              ) : (
                <div className="space-y-1">
                  {conversations.map(c => (
                    <div key={c.id}
                      className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                        conversationId === c.id ? 'bg-white/10' : 'hover:bg-white/5'
                      }`}
                      onClick={() => loadConversation(c.id)}
                      style={conversationId === c.id ? { border: '1px solid rgba(59,130,246,0.2)' } : {}}
                    >
                      <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-white/30" />
                      {renamingId === c.id ? (
                        <div className="flex-1 flex items-center gap-1">
                          <input
                            value={renameValue}
                            onChange={e => setRenameValue(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') renameConversation(c.id); if (e.key === 'Escape') setRenamingId(null); }}
                            className="flex-1 text-xs bg-white/10 border border-white/20 rounded px-1 py-0.5 text-white outline-none"
                            autoFocus
                            onClick={e => e.stopPropagation()}
                          />
                          <button onClick={e => { e.stopPropagation(); renameConversation(c.id); }} className="text-green-400 hover:text-green-300">
                            <Check className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="flex-1 truncate text-white/70 group-hover:text-white/90">{c.title}</span>
                          <div className="hidden group-hover:flex items-center gap-0.5">
                            <button onClick={e => { e.stopPropagation(); setRenamingId(c.id); setRenameValue(c.title); }} className="p-0.5 text-white/30 hover:text-white/60">
                              <Pencil className="w-3 h-3" />
                            </button>
                            <button onClick={e => deleteConversation(c.id, e)} className="p-0.5 text-red-400/50 hover:text-red-400">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        )}

        {/* ── Main Chat Area ── */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'rgba(59,130,246,0.1)', background: 'rgba(59, 130, 246, 0.03)' }}>
            <div className="flex items-center gap-3">
              {isTutor && !sidebarOpen && (
                <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => setSidebarOpen(true)} title="Sidebar einblenden">
                  <PanelLeft className="w-4 h-4 text-white/40" />
                </Button>
              )}
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: isTutor ? 'rgba(245,158,11,0.12)' : 'rgba(59,130,246,0.1)' }}>
                {isTutor ? <BookOpen className="w-5 h-5" style={{ color: '#f59e0b' }} /> : <Sparkles className="w-5 h-5" style={{ color: '#3b82f6' }} />}
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm">{isTutor ? "Medizinischer KI-Tutor" : "Medizinischer KI-Assistent"}</h3>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <button onClick={() => { setShowModelPicker(!showModelPicker); setShowLangPicker(false); setShowSpecialtyPicker(false); }}
                      className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md transition-colors hover:bg-white/5"
                      style={{ color: currentModel.color }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: currentModel.color }} />
                      {currentModel.name}
                      <ChevronDown className="w-3 h-3" />
                    </button>
                    {showModelPicker && (
                      <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[180px]"
                        style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                        {MODELS.map(m => (
                          <button key={m.id} onClick={() => { setSelectedModel(m.id); setShowModelPicker(false); }}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedModel === m.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                            <span className="w-2 h-2 rounded-full" style={{ background: m.color }} />
                            <div>
                              <span className="text-white font-medium">{m.name}</span>
                              <span className="text-white/30 text-xs ml-2">{m.provider}</span>
                            </div>
                            {selectedModel === m.id && <span className="ml-auto text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {isTutor && (
                    <>
                      <span className="text-white/10">|</span>
                      <div className="relative">
                        <button onClick={() => { setShowSpecialtyPicker(!showSpecialtyPicker); setShowModelPicker(false); setShowLangPicker(false); }}
                          className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                          <Database className="w-3 h-3" />
                          {selectedSpecialty ? specialties.find(s => s.id === selectedSpecialty)?.name || selectedSpecialty : "Alle Fächer"}
                          <ChevronDown className="w-3 h-3" />
                        </button>
                        {showSpecialtyPicker && (
                          <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[180px] max-h-[300px] overflow-y-auto"
                            style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                            <button onClick={() => { setSelectedSpecialty(""); setShowSpecialtyPicker(false); }}
                              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${!selectedSpecialty ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                              <Database className="w-3.5 h-3.5 text-white/40" />
                              <span className="text-white">Alle Fächer</span>
                            </button>
                            {specialties.map(s => (
                              <button key={s.id} onClick={() => { setSelectedSpecialty(s.id); setShowSpecialtyPicker(false); }}
                                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedSpecialty === s.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                                <span>{s.icon || "📄"}</span>
                                <span className="text-white">{s.name}</span>
                                <span className="ml-auto text-[10px] text-white/30">{s.question_count || ""}</span>
                                {selectedSpecialty === s.id && <span className="text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      {chapters.length > 0 && (
                        <>
                          <span className="text-white/10">|</span>
                          <div className="relative">
                            <button onClick={() => { setShowChapterPicker(!showChapterPicker); setShowModelPicker(false); setShowLangPicker(false); setShowSpecialtyPicker(false); }}
                              className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                              <BookOpen className="w-3 h-3" />
                              {selectedChapter !== null ? (chapters.find(c => c.index === selectedChapter)?.title || `Kapitel ${selectedChapter + 1}`) : "Ganzes Dokument"}
                              <ChevronDown className="w-3 h-3" />
                            </button>
                            {showChapterPicker && (
                              <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[220px] max-h-[300px] overflow-y-auto"
                                style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                                <button onClick={() => { setSelectedChapter(null); setShowChapterPicker(false); }}
                                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedChapter === null ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                                  <BookOpen className="w-3.5 h-3.5 text-white/40" />
                                  <span className="text-white">Ganzes Dokument</span>
                                </button>
                                {chapters.map(ch => (
                                  <button key={ch.index} onClick={() => { setSelectedChapter(ch.index); setShowChapterPicker(false); }}
                                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedChapter === ch.index ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                                    <span className="text-white/40 text-xs w-5">{ch.index + 1}.</span>
                                    <span className="text-white truncate">{ch.title}</span>
                                    <span className="ml-auto text-[10px] text-white/30">S. {ch.page_start}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </>
                  )}
                  <span className="text-white/10">|</span>
                  <div className="relative">
                    <button onClick={() => { setShowLangPicker(!showLangPicker); setShowModelPicker(false); setShowSpecialtyPicker(false); }}
                      className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                      <Globe className="w-3 h-3" />
                      {currentLang.name}
                      <ChevronDown className="w-3 h-3" />
                    </button>
                    {showLangPicker && (
                      <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[160px]"
                        style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                        {LANGUAGES.map(l => (
                          <button key={l.id} onClick={() => { setSelectedLang(l.id); setShowLangPicker(false); }}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedLang === l.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                            <span>{FLAG_EMOJI[l.flag]}</span>
                            <span className="text-white">{l.name}</span>
                            {selectedLang === l.id && <span className="ml-auto text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-white/40 hover:text-white">
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-4" ref={scrollRef}>
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div key={index} className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    message.role === "user" ? "bg-white/10" : ""
                  }`} style={message.role !== "user" ? { background: `${(MODELS.find(m => m.id === (message.model || selectedModel))?.color || '#3b82f6')}15` } : {}}>
                    {message.role === "user"
                      ? <User className="w-4 h-4 text-white/60" />
                      : <Bot className="w-4 h-4" style={{ color: MODELS.find(m => m.id === (message.model || selectedModel))?.color || '#3b82f6' }} />
                    }
                  </div>
                  <div className={`flex-1 p-4 rounded-2xl text-sm leading-relaxed ${
                    message.role === "user" ? "rounded-tr-sm text-white/90" : "rounded-tl-sm text-white/80"
                  }`} style={{ background: message.role === "user" ? 'rgba(59,130,246,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${message.role === "user" ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.04)'}` }}>
                    <p className="whitespace-pre-wrap" style={{ direction: selectedLang === 'ar' ? 'rtl' : 'ltr' }}>{message.content}</p>
                    {message.images && message.images.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                        {message.images.map((img, i) => (
                          <div key={i} className="relative">
                            {img.data ? (
                              <div className="block rounded-lg overflow-hidden border"
                                style={{ borderColor: 'rgba(255,255,255,0.08)', width: 120, height: 90 }}>
                                <img src={img.data} alt={img.title || ''} loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
                              </div>
                            ) : (
                              <a href={img.url} target="_blank" rel="noopener noreferrer"
                                className="block rounded-lg overflow-hidden border transition-opacity hover:opacity-80"
                                style={{ borderColor: 'rgba(255,255,255,0.08)', width: 120, height: 90 }}>
                                <img src={img.thumbnail} alt={img.title} loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
                              </a>
                            )}
                            {img._source && (
                              <span className="absolute bottom-0 right-0 text-[9px] px-1 py-[1px] rounded-tl leading-tight"
                                style={{ background: 'rgba(0,0,0,0.6)', color: 'rgba(255,255,255,0.6)' }}>
                                {img._source === 'local_db' ? '●' : '◌'} {img._source}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${currentModel.color}15` }}>
                    <Bot className="w-4 h-4" style={{ color: currentModel.color }} />
                  </div>
                  <div className="flex-1 p-4 rounded-2xl rounded-tl-sm" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
                    <div className="flex items-center gap-2 text-sm text-white/40">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {currentModel.name} ...
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Input */}
          <div className="p-4 border-t" style={{ borderColor: 'rgba(59,130,246,0.08)', background: 'rgba(0,0,0,0.2)' }}>
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={PLACEHOLDERS[selectedLang] || PLACEHOLDERS.de}
                className="flex-1 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-[#3b82f6]/30"
                disabled={loading}
                dir={selectedLang === 'ar' ? 'rtl' : 'ltr'}
              />
              <Button onClick={sendMessage} disabled={loading || !input.trim()}
                className="border-0" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}