import { User, Bot } from "lucide-react";
import { MODELS } from "@/hooks/useAIChat";
import MessageText from "./MessageText";
import MessageMCQ from "./MessageMCQ";
import MessageImages from "./MessageImages";
import MessageEvidence from "./MessageEvidence";
import MessageSources from "./MessageSources";
import MessageWikiImages from "./MessageWikiImages";

export default function AIChatMessageBubble({ message, selectedModel, selectedLang, onPageViewer, onLightbox }) {
  const modelColor = MODELS.find(m => m.id === (message.model || selectedModel))?.color || '#3b82f6';

  return (
    <div className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        message.role === "user" ? "bg-white/10" : ""
      }`} style={message.role !== "user" ? { background: `${modelColor}15` } : {}}>
        {message.role === "user"
          ? <User className="w-4 h-4 text-white/60" />
          : <Bot className="w-4 h-4" style={{ color: modelColor }} />
        }
      </div>
      <div className={`flex-1 p-4 rounded-2xl text-sm leading-relaxed ${
        message.role === "user" ? "rounded-tr-sm text-white/90" : "rounded-tl-sm text-white/80"
      }`} style={{ background: message.role === 'user' ? 'rgba(59,130,246,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${message.role === "user" ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.04)'}` }}>
        <MessageText content={message.content} selectedLang={selectedLang} />
        <MessageMCQ analysis={message.mcq_analysis} />
        <MessageImages images={message.images} onLightbox={onLightbox} />
        <MessageEvidence evidence={message.evidence} onPageViewer={onPageViewer} />
        <MessageSources sources={message.wiki_sources} />
        <MessageWikiImages images={message.wiki_images} onLightbox={onLightbox} />
      </div>
    </div>
  );
}
