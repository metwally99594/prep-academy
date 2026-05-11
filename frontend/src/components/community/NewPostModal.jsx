import { useState, useEffect, useCallback, useRef } from "react";
import apiClient from "@/lib/api";
import { X, Send, Loader2, Image, Video, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { TagPicker } from "./TagPicker";
import { POST_TYPE_OPTIONS, SPECIALTY_OPTIONS, TOPIC_OPTIONS } from "./communityConstants";
import { useFocusTrap } from "@/hooks/useFocusTrap";

const ALLOWED_MEDIA_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif", "video/mp4", "video/webm", "video/quicktime"];
const MAX_MEDIA_SIZE = 50 * 1024 * 1024;
const MAX_MEDIA_ITEMS = 5;

export function NewPostModal({ open, onClose, onCreated }) {
  const trapRef = useFocusTrap(open);
  const fileInputRef = useRef(null);
  const [type, setType] = useState("discussion");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [specialtyTags, setSpecialtyTags] = useState([]);
  const [topicTags, setTopicTags] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mediaItems, setMediaItems] = useState([]);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const wordCount = content.trim() ? content.trim().split(/\s+/).filter(Boolean).length : 0;
  const canSubmit = title.trim().length >= 5 && content.trim().length >= 50 && wordCount >= 5 && !submitting && !uploading;

  const handleMediaPick = useCallback(async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (files.length === 0) return;
    const remaining = MAX_MEDIA_ITEMS - mediaItems.length;
    if (remaining <= 0) { toast.error("Max. 5 Medien pro Beitrag"); return; }
    const toUpload = files.slice(0, remaining);
    for (const file of toUpload) {
      const typeOk = ALLOWED_MEDIA_TYPES.includes(file.type);
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!typeOk && !["jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov"].includes(ext)) {
        toast.error(`Nicht unterstützt: ${file.name}`);
        continue;
      }
      if (file.size > MAX_MEDIA_SIZE) {
        toast.error(`Datei zu groß (max. 50 MB): ${file.name}`);
        continue;
      }
      setUploading(true);
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await apiClient.post("/community/upload", form, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 120000,
        });
        setMediaItems(prev => [...prev, res.data]);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Upload fehlgeschlagen");
      } finally {
        setUploading(false);
      }
    }
  }, [mediaItems.length]);

  const removeMedia = useCallback((mediaId) => {
    setMediaItems(prev => prev.filter(m => m.id !== mediaId));
  }, []);

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
          media: mediaItems.map(m => ({
            id: m.id,
            media_type: m.media_type,
            mime_type: m.mime_type,
            filename: m.filename,
            size_bytes: m.size_bytes,
            data_uri: m.data_uri,
          })),
        },
      );

      const status = res.data.status;
      if (status === "moderation_queue") {
        toast.info("Beitrag eingereicht — wird nach Überprüfung veröffentlicht.");
      } else {
        toast.success("Beitrag veröffentlicht!");
      }

      setTitle("");
      setContent("");
      setType("discussion");
      setSpecialtyTags([]);
      setTopicTags([]);
      setMediaItems([]);

      onCreated(res.data.id, status);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, title, content, type, specialtyTags, topicTags, mediaItems, onCreated]);

  return (
    <div
      className={`fixed inset-0 z-50 items-end sm:items-center justify-center p-0 sm:p-4 ${open ? "flex" : "hidden"}`}
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
            <div className="flex justify-between text-[10px] mt-1">
              <span className={`transition-colors ${content.trim().length > 0 && (content.trim().length < 50 || wordCount < 5) ? "text-destructive" : "text-muted-foreground"}`}>
                {content.trim().length > 0 && content.trim().length < 50
                  ? `Noch ${50 - content.trim().length} Zeichen (min. 50)`
                  : content.trim().length >= 50 && wordCount < 5
                    ? "Mindestens 5 Wörter erforderlich"
                    : "Mindestens 50 Zeichen"}
              </span>
              <span className={`transition-colors ${content.length > 9500 ? "text-amber-500" : "text-muted-foreground"}`}>
                {content.length}/10000
              </span>
            </div>
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

          {/* Media */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Medien (optional)</p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/jpeg,image/jpg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime"
              multiple
              onChange={handleMediaPick}
            />
            {mediaItems.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {mediaItems.map(m => (
                  <div key={m.id} className="relative group">
                    {m.media_type === "video" ? (
                      <video src={m.data_uri} className="w-20 h-20 rounded-xl object-cover border border-border/50" />
                    ) : (
                      <img src={m.data_uri} alt="" className="w-20 h-20 rounded-xl object-cover border border-border/50" />
                    )}
                    <button
                      onClick={() => removeMedia(m.id)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label="Entfernen"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || mediaItems.length >= MAX_MEDIA_ITEMS}
              className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Image className="w-4 h-4" />
                  <Video className="w-4 h-4" />
                </>
              )}
              {uploading ? "Wird hochgeladen…" : "Bilder / Videos hinzufügen (max. 50 MB)"}
            </button>
          </div>
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
