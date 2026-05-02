import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import axios from "axios";
import { API, useAuth } from "@/App";
import { 
  Sparkles, Send, X, Loader2, Bot, User, ChevronDown, Globe,
} from "lucide-react";

const MODELS = [
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", color: "#10a37f" },
  { id: "claude-sonnet", name: "Claude Sonnet", provider: "Anthropic", color: "#cc785c" },
  { id: "gemini-flash", name: "Gemini Flash", provider: "Google", color: "#4285f4" },
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

export default function AIChat({ question, isOpen, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gpt-4o");
  const [selectedLang, setSelectedLang] = useState("de");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const { token } = useAuth();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const currentModel = MODELS.find(m => m.id === selectedModel) || MODELS[0];
  const currentLang = LANGUAGES.find(l => l.id === selectedLang) || LANGUAGES[0];

  useEffect(() => {
    if (isOpen && question) {
      const questionText = question.question_text_de || question.question_text;
      const greetings = {
        de: `Hallo! Ich bin Ihr medizinischer KI-Assistent.\n\nIch helfe Ihnen gerne bei dieser Frage:\n\n"${questionText}"\n\nStellen Sie mir eine Frage zu diesem Thema!`,
        en: `Hello! I'm your medical AI assistant.\n\nI'm happy to help with this question:\n\n"${questionText}"\n\nAsk me anything about this topic!`,
        ar: `مرحباً! أنا مساعدك الطبي الذكي.\n\nسأساعدك في هذا السؤال:\n\n"${questionText}"\n\nاسألني أي شيء عن هذا الموضوع!`,
        ru: `Здравствуйте! Я ваш медицинский ИИ-ассистент.\n\nЯ помогу вам с этим вопросом:\n\n"${questionText}"\n\nЗадайте мне вопрос по этой теме!`,
      };
      setMessages([{ role: "assistant", content: greetings[selectedLang] || greetings.de }]);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, question]); // eslint-disable-line

  // Update greeting when language changes
  useEffect(() => {
    if (isOpen && question && messages.length === 1 && messages[0].role === "assistant") {
      const questionText = question.question_text_de || question.question_text;
      const greetings = {
        de: `Hallo! Ich bin Ihr medizinischer KI-Assistent.\n\nIch helfe Ihnen gerne bei dieser Frage:\n\n"${questionText}"\n\nStellen Sie mir eine Frage zu diesem Thema!`,
        en: `Hello! I'm your medical AI assistant.\n\nI'm happy to help with this question:\n\n"${questionText}"\n\nAsk me anything about this topic!`,
        ar: `مرحباً! أنا مساعدك الطبي الذكي.\n\nسأساعدك في هذا السؤال:\n\n"${questionText}"\n\nاسألني أي شيء عن هذا الموضوع!`,
        ru: `Здравствуйте! Я ваш медицинский ИИ-ассистент.\n\nЯ помогу вам с этим вопросом:\n\n"${questionText}"\n\nЗадайте мне вопрос по этой теме!`,
      };
      setMessages([{ role: "assistant", content: greetings[selectedLang] || greetings.de }]);
    }
  }, [selectedLang]); // eslint-disable-line

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await axios.post(`${API}/ai/chat`, {
        question_id: question.id,
        user_message: userMessage,
        model: selectedModel,
        language: selectedLang,
        context: messages.map(m => `${m.role}: ${m.content}`).join('\n'),
      }, { headers: { Authorization: `Bearer ${token}` } });

      setMessages(prev => [...prev, { role: "assistant", content: response.data.response, model: selectedModel }]);
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
      <div className="w-full max-w-2xl h-[600px] rounded-2xl border shadow-2xl flex flex-col overflow-hidden animate-fadeIn"
        style={{ background: '#0c1229', borderColor: 'rgba(201,168,76,0.15)' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'rgba(201,168,76,0.1)', background: 'rgba(201,168,76,0.03)' }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.1)' }}>
              <Sparkles className="w-5 h-5" style={{ color: '#c9a84c' }} />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">Medizinischer KI-Assistent</h3>
              <div className="flex items-center gap-2">
                {/* Model Picker */}
                <div className="relative">
                  <button onClick={() => { setShowModelPicker(!showModelPicker); setShowLangPicker(false); }}
                    className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md transition-colors hover:bg-white/5"
                    style={{ color: currentModel.color }} data-testid="model-picker-btn">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: currentModel.color }} />
                    {currentModel.name}
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  {showModelPicker && (
                    <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[180px]"
                      style={{ background: '#0f1a3a', borderColor: 'rgba(201,168,76,0.15)' }} data-testid="model-picker-dropdown">
                      {MODELS.map(m => (
                        <button key={m.id} onClick={() => { setSelectedModel(m.id); setShowModelPicker(false); }}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedModel === m.id ? 'bg-white/10' : 'hover:bg-white/5'}`}
                          data-testid={`model-${m.id}`}>
                          <span className="w-2 h-2 rounded-full" style={{ background: m.color }} />
                          <div>
                            <span className="text-white font-medium">{m.name}</span>
                            <span className="text-white/30 text-xs ml-2">{m.provider}</span>
                          </div>
                          {selectedModel === m.id && <span className="ml-auto text-xs" style={{ color: '#c9a84c' }}>&#10003;</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <span className="text-white/10">|</span>

                {/* Language Picker */}
                <div className="relative">
                  <button onClick={() => { setShowLangPicker(!showLangPicker); setShowModelPicker(false); }}
                    className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5"
                    data-testid="lang-picker-btn">
                    <Globe className="w-3 h-3" />
                    {currentLang.name}
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  {showLangPicker && (
                    <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[160px]"
                      style={{ background: '#0f1a3a', borderColor: 'rgba(201,168,76,0.15)' }} data-testid="lang-picker-dropdown">
                      {LANGUAGES.map(l => (
                        <button key={l.id} onClick={() => { setSelectedLang(l.id); setShowLangPicker(false); }}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedLang === l.id ? 'bg-white/10' : 'hover:bg-white/5'}`}
                          data-testid={`lang-${l.id}`}>
                          <span>{FLAG_EMOJI[l.flag]}</span>
                          <span className="text-white">{l.name}</span>
                          {selectedLang === l.id && <span className="ml-auto text-xs" style={{ color: '#c9a84c' }}>&#10003;</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-white/40 hover:text-white" data-testid="close-ai-chat">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div key={index} className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`} data-testid={`chat-message-${index}`}>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  message.role === "user" ? "bg-white/10" : ""
                }`} style={message.role !== "user" ? { background: `${(MODELS.find(m => m.id === (message.model || selectedModel))?.color || '#c9a84c')}15` } : {}}>
                  {message.role === "user"
                    ? <User className="w-4 h-4 text-white/60" />
                    : <Bot className="w-4 h-4" style={{ color: MODELS.find(m => m.id === (message.model || selectedModel))?.color || '#c9a84c' }} />
                  }
                </div>
                <div className={`flex-1 p-4 rounded-2xl text-sm leading-relaxed ${
                  message.role === "user" ? "rounded-tr-sm text-white/90" : "rounded-tl-sm text-white/80"
                }`} style={{ background: message.role === "user" ? 'rgba(201,168,76,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${message.role === "user" ? 'rgba(201,168,76,0.1)' : 'rgba(255,255,255,0.04)'}` }}>
                  <p className="whitespace-pre-wrap" style={{ direction: selectedLang === 'ar' ? 'rtl' : 'ltr' }}>{message.content}</p>
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
        <div className="p-4 border-t" style={{ borderColor: 'rgba(201,168,76,0.08)', background: 'rgba(0,0,0,0.2)' }}>
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={PLACEHOLDERS[selectedLang] || PLACEHOLDERS.de}
              className="flex-1 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-[#c9a84c]/30"
              disabled={loading}
              dir={selectedLang === 'ar' ? 'rtl' : 'ltr'}
              data-testid="ai-chat-input"
            />
            <Button onClick={sendMessage} disabled={loading || !input.trim()}
              className="border-0" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}
              data-testid="ai-chat-send">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
