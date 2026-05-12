import { useState, useRef, useEffect, useCallback } from "react";
import { Paperclip, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { AttachmentPreview } from "./AttachmentPreview";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/webm", "video/quicktime", "application/pdf"];
const MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024; // 2 MB after compression
const MAX_ATTACHMENTS = 5;

async function compressImage(file, targetBytes = 600 * 1024) {
  try {
    if (file.size <= targetBytes) return file;
    const bitmap = await createImageBitmap(file);
    const ratio = Math.sqrt(targetBytes / file.size);
    const w = Math.max(1, Math.floor(bitmap.width * ratio));
    const h = Math.max(1, Math.floor(bitmap.height * ratio));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    return new Promise(resolve =>
      canvas.toBlob(b => resolve(b || file), file.type === "image/png" ? "image/jpeg" : file.type, 0.82),
    );
  } catch {
    return file;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function processFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    toast.error(`Dateityp nicht unterstützt: ${file.name.slice(0, 30)}`);
    return null;
  }
  let processed = file;
  if (file.type.startsWith("image/") && file.size > 400 * 1024) {
    processed = await compressImage(file);
  }
  if (processed.size > MAX_ATTACHMENT_BYTES) {
    toast.error(`Datei zu groß nach Komprimierung (max. 2 MB): ${file.name.slice(0, 30)}`);
    return null;
  }
  const base64 = await fileToBase64(processed);
  return {
    id: `att-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    name: file.name,
    mime: file.type,
    size: processed.size,
    base64,
    preview: file.type.startsWith("image/") ? base64 : null,
  };
}

export function MessageInput({ onSend, disabled = false }) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [sending, setSending] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-grow textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [text]);

  const handleFiles = useCallback(async (files) => {
    const remaining = MAX_ATTACHMENTS - attachments.length;
    if (remaining <= 0) { toast.error("Max. 5 Anhänge pro Nachricht"); return; }
    const selected = Array.from(files).slice(0, remaining);
    setProcessing(true);
    try {
      const results = await Promise.all(selected.map(f => processFile(f).catch(() => null)));
      setAttachments(prev => [...prev, ...results.filter(Boolean)]);
    } catch {
      toast.error("Fehler beim Verarbeiten der Dateien");
    } finally {
      setProcessing(false);
    }
  }, [attachments.length]);

  const removeAttachment = useCallback((id) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = text.trim();
    if ((!trimmed && attachments.length === 0) || disabled || sending) return;
    setSending(true);
    const atts = attachments.map(a => ({
      filename: a.name,
      mime_type: a.mime,
      size_bytes: a.size,
      image_base64: a.base64,
      type: a.mime?.startsWith("image/") ? "image" : "file",
    }));
    try {
      await onSend(trimmed, atts);
      setText("");
      setAttachments([]);
      // Reset textarea height
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    } catch (e) {
      toast.error(e.response?.data?.detail || "Nachricht konnte nicht gesendet werden");
    } finally {
      setSending(false);
    }
  }, [text, attachments, disabled, sending, onSend]);

  const onKeyDown = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // Drag-and-drop
  const onDragOver = useCallback((e) => { e.preventDefault(); setIsDragging(true); }, []);
  const onDragLeave = useCallback(() => setIsDragging(false), []);
  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const canSend = (text.trim() || attachments.length > 0) && !disabled && !sending;

  return (
    <div
      className={`relative border-t border-border/50 bg-card/30 shrink-0 transition-colors duration-150 ${isDragging ? "bg-primary/5 border-primary/30" : ""}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      {isDragging && (
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none rounded-b-2xl">
          <div className="text-sm text-primary font-medium bg-background/95 px-4 py-2 rounded-xl border border-primary/30 shadow-sm">
            Dateien hier ablegen…
          </div>
        </div>
      )}

      {attachments.length > 0 && (
        <div className="px-3 pt-3 flex flex-wrap gap-2">
          {attachments.map(a => (
            <AttachmentPreview key={a.id} attachment={a} onRemove={() => removeAttachment(a.id)} />
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end p-3">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept={ALLOWED_TYPES.join(",")}
          multiple
          onChange={e => { handleFiles(e.target.files); e.target.value = ""; }}
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={processing || attachments.length >= MAX_ATTACHMENTS || disabled}
          className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-accent transition-colors shrink-0 disabled:opacity-40"
          title="Anhang hinzufügen (Bilder, PDF)"
        >
          {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
        </button>

        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            className="w-full rounded-xl border bg-background px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed overflow-hidden"
            style={{ minHeight: "42px", maxHeight: "160px" }}
            placeholder="Nachricht schreiben… (Enter senden, Shift+Enter Zeilenumbruch)"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
            aria-label="Nachricht"
          />
        </div>

        <Button
          size="icon"
          className="h-10 w-10 rounded-xl shrink-0"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Senden"
        >
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}
