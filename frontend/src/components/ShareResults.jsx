import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { 
  Share2, 
  Copy, 
  Check,
  MessageCircle,
  X
} from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function ShareResults({ score, total, specialty, level, xp, isOpen, onClose }) {
  const [copied, setCopied] = useState(false);
  const cardRef = useRef(null);

  const accuracy = total > 0 ? Math.round((score / total) * 100) : 0;
  const emoji = accuracy >= 90 ? "🏆" : accuracy >= 70 ? "🎯" : accuracy >= 50 ? "📚" : "💪";
  
  const appUrl = window.location.origin;
  const shareText = `${emoji} Prep Academy – ${specialty || 'Quiz'}\n\n✅ ${score}/${total} richtig (${accuracy}%)\n📊 Level: ${level?.name_de || 'Praktikant'} (${xp || 0} XP)\n\nBereite dich auf die Medizinprüfung vor!\n👉 ${appUrl}`;

  const shareWhatsApp = () => {
    window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank');
  };

  const shareTelegram = () => {
    window.open(`https://t.me/share/url?url=${encodeURIComponent(appUrl)}&text=${encodeURIComponent(shareText)}`, '_blank');
  };

  const shareTwitter = () => {
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`, '_blank');
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      toast.success("Text kopiert!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Kopieren fehlgeschlagen");
    }
  };

  const nativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Prep Academy – Ergebnis',
          text: shareText,
        });
      } catch (err) {
        if (err.name !== 'AbortError') console.error('Share failed:', err);
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="w-5 h-5 text-primary" />
            Ergebnis teilen
          </DialogTitle>
        </DialogHeader>

        {/* Result Preview Card */}
        <div ref={cardRef} className="rounded-2xl p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border border-primary/20" data-testid="share-preview-card">
          <div className="text-center">
            <div className="text-4xl mb-2">{emoji}</div>
            <h3 className="text-lg font-bold">{specialty || 'Quiz'} Ergebnis</h3>
            <div className="mt-4 flex items-center justify-center gap-6">
              <div>
                <div className="text-3xl font-bold text-primary">{accuracy}%</div>
                <div className="text-xs text-muted-foreground">Genauigkeit</div>
              </div>
              <div className="w-px h-10 bg-border" />
              <div>
                <div className="text-3xl font-bold">{score}/{total}</div>
                <div className="text-xs text-muted-foreground">Richtig</div>
              </div>
            </div>
            <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full">
              <span className="text-sm font-medium">{level?.name_de || 'Praktikant'}</span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-sm text-primary font-medium">{(xp || 0).toLocaleString()} XP</span>
            </div>
          </div>
        </div>

        {/* Share Buttons */}
        <div className="grid grid-cols-2 gap-3 mt-2">
          <Button
            variant="outline"
            className="gap-2 h-12 bg-[#25D366]/10 border-[#25D366]/30 hover:bg-[#25D366]/20 text-[#25D366]"
            onClick={shareWhatsApp}
            data-testid="share-whatsapp"
          >
            <MessageCircle className="w-5 h-5" />
            WhatsApp
          </Button>
          <Button
            variant="outline"
            className="gap-2 h-12 bg-[#0088cc]/10 border-[#0088cc]/30 hover:bg-[#0088cc]/20 text-[#0088cc]"
            onClick={shareTelegram}
            data-testid="share-telegram"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
            Telegram
          </Button>
          <Button
            variant="outline"
            className="gap-2 h-12 bg-black/5 border-black/10 hover:bg-black/10"
            onClick={shareTwitter}
            data-testid="share-twitter"
          >
            <X className="w-5 h-5" />
            X / Twitter
          </Button>
          <Button
            variant="outline"
            className="gap-2 h-12"
            onClick={copyToClipboard}
            data-testid="share-copy"
          >
            {copied ? <Check className="w-5 h-5 text-emerald-500" /> : <Copy className="w-5 h-5" />}
            {copied ? 'Kopiert!' : 'Kopieren'}
          </Button>
        </div>

        {/* Native Share (mobile) */}
        {typeof navigator !== 'undefined' && navigator.share && (
          <Button className="w-full gap-2 mt-1" onClick={nativeShare} data-testid="share-native">
            <Share2 className="w-4 h-4" />
            Mehr Optionen...
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}
