import { useState, useEffect, useCallback } from "react";
import apiClient from "@/lib/api";
import { X, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { TagPicker } from "./TagPicker";
import { POST_TYPE_OPTIONS, SPECIALTY_OPTIONS, TOPIC_OPTIONS } from "./communityConstants";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export function NewPostModal({ open, onClose, onCreated }) {
  const trapRef = useFocusTrap(open);
  const [type, setType] = useState("discussion");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [specialtyTags, setSpecialtyTags] = useState([]);
  const [topicTags, setTopicTags] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  // ESC to close (desktop)
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Prevent body scroll when modal open
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const canSubmit = title.trim().length >= 5 && content.trim().length >= 10 && !submitting;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const res = await apiClient.post(
        "/community/posts",
        {
          title: title.trim(),
          content: content.trim(),
          type,
          specialty_tags: specialtyTags,
          topic_tags: topicTags,
          image_ids: [],
        },
      );

      const status = res.data.status;
      if (status === "moderation_queue") {
        toast.info("Beitrag eingereicht — wird nach Überprüfung veröffentlicht.");
      } else {
        toast.success("Beitrag veröffentlicht!");
      }

      // Reset draft
      setTitle("");
      setContent("");
      setType("discussion");
      setSpecialtyTags([]);
      setTopicTags([]);

      onCreated(res.data.id, status);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, title, content, type, specialtyTags, topicTags, onCreated]);

  // Keep mounted so draft survives accidental close → reopen
  return (
    <div
      className={`fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 ${open ? "" : "hidden"}`}
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        ref={trapRef}
        className="relative w-full sm:max-w-xl rounded-t-2xl sm:rounded-2xl border bg-card shadow-2xl flex flex-col"
        style={{ maxHeight: "90dvh" }}
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Neuen Beitrag erstellen"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/50 shrink-0">
          <h3 className="font-semibold">Neuer Beitrag</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground"
            aria-label="Schließen"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-5 space-y-4">
          {/* Type selector */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Beitragstyp</p>
            <div className="grid grid-cols-2 gap-2">
              {POST_TYPE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setType(opt.value)}
                  className={`px-3 py-2.5 rounded-xl text-sm border transition-colors text-left ${
                    type === opt.value
                      ? "border-primary bg-primary/8 text-foreground"
                      : "border-border/50 text-muted-foreground hover:border-border hover:text-foreground"
                  }`}
                >
                  <span className="block font-medium">{opt.icon} {opt.label}</span>
                  <span className="text-[10px] font-normal text-muted-foreground/70 mt-0.5 block">{opt.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">
              Titel <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              className="w-full rounded-xl border bg-background/50 px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Aussagekräftiger Titel…"
              value={title}
              onChange={e => setTitle(e.target.value)}
              maxLength={200}
              autoFocus={open}
            />
            <p className={`text-[10px] mt-1 text-right transition-colors ${title.length > 180 ? "text-amber-500" : "text-muted-foreground"}`}>
              {title.length}/200
            </p>
          </div>

          {/* Content */}
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">
              Inhalt <span className="text-destructive">*</span>
            </label>
            <textarea
              className="w-full rounded-xl border bg-background/50 px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Schreiben Sie Ihren Beitrag…"
              value={content}
              onChange={e => setContent(e.target.value)}
              maxLength={10000}
              rows={5}
            />
            <p className={`text-[10px] mt-1 text-right transition-colors ${content.length > 9500 ? "text-amber-500" : "text-muted-foreground"}`}>
              {content.length}/10000
            </p>
          </div>

          {/* Tags */}
          <TagPicker
            label="Fachgebiet (max. 3)"
            options={SPECIALTY_OPTIONS}
            selected={specialtyTags}
            onChange={setSpecialtyTags}
            max={3}
          />
          <TagPicker
            label="Thema (max. 3)"
            options={TOPIC_OPTIONS}
            selected={topicTags}
            onChange={setTopicTags}
            max={3}
          />
        </div>

        {/* Footer */}
        <div
          className="px-5 py-4 border-t border-border/50 shrink-0 flex gap-3"
          style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
        >
          <Button variant="outline" className="flex-1" onClick={onClose} disabled={submitting}>
            Abbrechen
          </Button>
          <Button
            className="flex-1 gap-2"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {submitting ? "Wird gesendet…" : "Veröffentlichen"}
          </Button>
        </div>
      </div>
    </div>
  );
}
