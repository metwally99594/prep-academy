import { useState } from "react";
import { Flag, Loader2, X } from "lucide-react";
import apiClient from "@/lib/api";
import { toast } from "sonner";

const REPORT_REASONS = [
  { value: "spam", label: "Spam" },
  { value: "inappropriate", label: "Unangemessener Inhalt" },
  { value: "misinformation", label: "Falschinformation" },
  { value: "harassment", label: "Belästigung" },
  { value: "other", label: "Sonstiges" },
];

export default function ReportModal({ targetId, targetType = "post", onClose }) {
  const [reason, setReason] = useState("");
  const [description, setDescription] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async () => {
    if (!reason) return toast.error("Bitte wähle einen Grund");
    setSending(true);
    try {
      await apiClient.post("/community/reports", {
        target_type: targetType,
        target_id: targetId,
        reason,
        description: description.trim() || undefined,
      });
      toast.success("Gemeldet — Admin prüft den Beitrag");
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Melden");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-sm animate-fade-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Flag className="w-4 h-4 text-destructive" />
            Beitrag melden
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-accent/50 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Grund *</label>
            {REPORT_REASONS.map(r => (
              <button
                key={r.value}
                onClick={() => setReason(r.value)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs border transition-colors ${
                  reason === r.value
                    ? "border-destructive/40 bg-destructive/5 text-destructive font-medium"
                    : "border-border hover:border-border/80 bg-card"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Details (optional)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Weitere Informationen..."
              className="w-full min-h-[72px] px-3 py-2 rounded-lg border border-border bg-transparent text-xs resize-none focus:outline-none focus:ring-1 focus:ring-destructive/40"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-medium bg-muted hover:bg-accent/50 transition-colors">
            Abbrechen
          </button>
          <button
            onClick={handleSubmit}
            disabled={!reason || sending}
            className="px-4 py-2 rounded-lg text-xs font-medium bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition-colors inline-flex items-center gap-1.5"
          >
            {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Flag className="w-3 h-3" />}
            Melden
          </button>
        </div>
      </div>
    </div>
  );
}
