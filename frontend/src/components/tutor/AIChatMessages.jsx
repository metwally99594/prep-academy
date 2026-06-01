import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot } from "lucide-react";
import AIChatMessageBubble from "./AIChatMessageBubble";
import ThinkingIndicator from "./ThinkingIndicator";

export default function AIChatMessages({
  messages, loading, selectedModel, selectedLang, currentModel, scrollRef,
  onPageViewerOpen, onLightboxOpen,
}) {
  return (
    <ScrollArea className="flex-1 p-4" ref={scrollRef}>
      <div className="space-y-4">
        {messages.map((message, index) => (
          <AIChatMessageBubble
            key={index}
            message={message}
            selectedModel={selectedModel}
            selectedLang={selectedLang}
            onPageViewer={onPageViewerOpen}
            onLightbox={onLightboxOpen}
          />
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${currentModel.color}15` }}>
              <Bot className="w-4 h-4" style={{ color: currentModel.color }} />
            </div>
            <div className="flex-1 p-4 rounded-2xl rounded-tl-sm" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
              <ThinkingIndicator modelName={currentModel.name} />
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
