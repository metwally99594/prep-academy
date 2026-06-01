import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Loader2, Eraser } from "lucide-react";
import { PLACEHOLDERS } from "@/hooks/useAIChat";
import ClearChatDialog from "./ClearChatDialog";

export default function AIChatInput({ input, loading, selectedLang, inputRef, messagesLength, onSend, onInputChange, onKeyDown, onClearChat }) {
  const [showClearDialog, setShowClearDialog] = useState(false);

  return (
    <div className="p-4 border-t" style={{ borderColor: 'rgba(59,130,246,0.08)', background: 'rgba(0,0,0,0.2)' }}>
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
          placeholder={PLACEHOLDERS[selectedLang] || PLACEHOLDERS.de}
          className="flex-1 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-[#3b82f6]/30"
          disabled={loading}
          dir={selectedLang === 'ar' ? 'rtl' : 'ltr'}
        />
        <Button onClick={onSend} disabled={loading || !input.trim()} aria-label="Nachricht senden"
          className="border-0" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
        {!loading && messagesLength > 0 && (
          <Button variant="ghost" size="icon" onClick={() => setShowClearDialog(true)}
            className="text-white/30 hover:text-red-400" aria-label="Chatverlauf l&ouml;schen">
            <Eraser className="w-4 h-4" />
          </Button>
        )}
      </div>
      <ClearChatDialog
        isOpen={showClearDialog}
        onConfirm={() => { onClearChat(); setShowClearDialog(false); }}
        onCancel={() => setShowClearDialog(false)}
      />
    </div>
  );
}
