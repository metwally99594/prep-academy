import { useState, useEffect, useCallback } from "react";
import { Trash2, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export function ModerationActionModal({ open, onClose, onConfirm, action, preview }) {
  const trapRef = useFocusTrap(open);
  const [note, setNote] = useState("");

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, onClose]);

  // Reset note when reopened
  useEffect(() => { if (open) setNote(""); }, [open]);

  const handleConfirm = useCallback(() => {
    onConfirm(note.trim() || null);
  }, [note, onConfirm]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        ref={trapRef}
        className="relative w-full max-w-sm rounded-2xl border bg-card shadow-2xl p-5 space-y-4"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Aktion bestätigen"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Inhalt löschen</h3>
              <p className="text-xs text-muted-foreground">Diese Aktion kann nicht rückgängig gemacht werden.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-accent text-muted-foreground"
            aria-label="Schließen"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {preview && (
          <div className="rounded-xl bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground line-clamp-3 leading-relaxed">
            {preview}
          </div>
        )}

        <div>
          <label className="text-xs font-medium text-muted-foreground block mb-1.5">
            Moderationsnotiz (optional)
          </label>
          <textarea
            className="w-full rounded-xl border bg-background/50 px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            rows={2}
            placeholder="Grund für die Löschung…"
            value={note}
            onChange={e => setNote(e.target.value)}
            maxLength={500}
            autoFocus
          />
        </div>

        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            Abbrechen
          </Button>
          <Button
            className="flex-1 gap-2 bg-red-600 hover:bg-red-700 text-white border-0"
            onClick={handleConfirm}
          >
            <Trash2 className="w-4 h-4" />
            Löschen
          </Button>
        </div>
      </div>
    </div>
  );
}
