import { memo } from "react";
import { CheckCheck, FileText, Download } from "lucide-react";

function fmtMsgTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function fmt(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentItem({ att, isMe }) {
  const isImage = att.mime_type?.startsWith("image/");
  if (isImage) {
    return (
      <a href={att.file_url} target="_blank" rel="noopener noreferrer" className="block mt-1.5">
        <img
          src={att.file_url}
          alt={att.file_name || "Bild"}
          className="max-w-[240px] max-h-48 rounded-xl object-cover border border-white/10 hover:opacity-90 transition-opacity cursor-pointer"
          loading="lazy"
        />
      </a>
    );
  }
  // PDF / other file
  return (
    <a
      href={att.file_url}
      download={att.file_name || "datei"}
      className={`mt-1.5 flex items-center gap-2.5 px-3 py-2.5 rounded-xl border transition-colors ${
        isMe
          ? "border-white/20 bg-white/10 hover:bg-white/20 text-primary-foreground"
          : "border-border/50 bg-background/60 hover:bg-accent text-foreground"
      }`}
    >
      <div className={`p-1.5 rounded-lg ${isMe ? "bg-white/15" : "bg-primary/10"}`}>
        <FileText className={`w-4 h-4 ${isMe ? "text-primary-foreground" : "text-primary"}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium truncate">{att.file_name || "Datei"}</p>
        {att.size_bytes > 0 && (
          <p className={`text-[10px] ${isMe ? "text-primary-foreground/60" : "text-muted-foreground"}`}>
            {fmt(att.size_bytes)}
          </p>
        )}
      </div>
      <Download className="w-3.5 h-3.5 opacity-60 shrink-0" />
    </a>
  );
}

export const MessageBubble = memo(function MessageBubble({ msg, isMe, readByOther }) {
  if (msg.is_system_message) {
    return (
      <div className="flex justify-center my-1">
        <span className="text-[11px] text-muted-foreground/55 bg-muted/40 px-3 py-1 rounded-full select-none">
          {msg.content}
        </span>
      </div>
    );
  }

  const atts = msg.attachments || [];
  const hasText = Boolean(msg.content?.trim());

  return (
    <div className={`flex ${isMe ? "justify-end" : "justify-start"} group`}>
      <div className={`max-w-[78%] ${isMe ? "items-end" : "items-start"} flex flex-col`}>
        {atts.map((att, i) => (
          <AttachmentItem key={i} att={att} isMe={isMe} />
        ))}

        {hasText && (
          <div className={`rounded-2xl px-4 py-2.5 mt-1 ${
            isMe
              ? `bg-primary text-primary-foreground rounded-br-sm ${msg._optimistic ? "opacity-70" : ""}`
              : "bg-muted text-foreground rounded-bl-sm"
          }`}>
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
          </div>
        )}

        <div className={`flex items-center gap-1 mt-1 px-1 ${isMe ? "justify-end" : "justify-start"}`}>
          <span className="text-[10px] text-muted-foreground/55">{fmtMsgTime(msg.created_at)}</span>
          {isMe && !msg._optimistic && (
            <CheckCheck className={`w-3 h-3 transition-colors ${
              readByOther ? "text-primary" : "text-muted-foreground/40"
            }`} />
          )}
          {isMe && msg._optimistic && (
            <span className="w-3 h-3 rounded-full border border-muted-foreground/30 inline-block" />
          )}
        </div>
      </div>
    </div>
  );
});
