import { useState, useEffect, useCallback, useMemo } from "react";
import { Trash2, EyeOff, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useFocusTrap } from "@/hooks/useFocusTrap";

const ACTION_CONFIG = {
  delete: {
    icon: Trash2,
    iconColor: "text-red-500",
    bgColor: "bg-red-500/10",
    btnClass: "bg-red-600 hover:bg-red-700 text-white border-0",
    title: "Inhalt löschen",
    desc: "Diese Aktion kann nicht rückgängig gemacht werden.",
    placeholder: "Grund für die Löschung…",
    btnLabel: "Löschen",
  },
  hide: {
    icon: EyeOff,
    iconColor: "text-slate-500",
    bgColor: "bg-slate-500/10",
    btnClass: "bg-slate-600 hover:bg-slate-700 text-white border-0",
    title: "Inhalt ausblenden",
    desc: "Der Inhalt wird ausgeblendet, kann aber wiederhergestellt werden.",
    placeholder: "Grund für das Ausblenden…",
    btnLabel: "Ausblenden",
  },
};

export function ModerationActionModal({ open, onClose, onConfirm, action, preview }) {
  const trapRef = useFocusTrap(open);
  const [note, setNote] = useState("");
  const cfg = useMemo(() => ACTION_CONFIG[action] || ACTION_CONFIG.delete, [action]);
  const Icon = cfg.icon;

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
            <div className={`w-9 h-9 rounded-xl ${cfg.bgColor} flex items-center justify-center`}>
              <AlertTriangle className={`w-5 h-5 ${cfg.iconColor}`} />
            </div>
            <div>
              <h3 className="font-semibold text-sm">{cfg.title}</h3>
              <p className="text-xs text-muted-foreground">{cfg.desc}</p>
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
            placeholder={cfg.placeholder}
            value={note}
            onChange={e => setNote(e.target.value)}
            maxLength={500}
            autoFocus
          />
          <div className="text-right text-[10px] text-muted-foreground mt-0.5">
            {note.length}/500
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            Abbrechen
          </Button>
          <Button
            className={`flex-1 gap-2 ${cfg.btnClass}`}
            onClick={handleConfirm}
          >
            <Icon className="w-4 h-4" />
            {cfg.btnLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
