import { memo } from "react";
import { X, FileText } from "lucide-react";

function fmt(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const AttachmentPreview = memo(function AttachmentPreview({ attachment, onRemove }) {
  if (!attachment) return null;
  const mime = attachment.mime || "";
  const isImage = mime.startsWith("image/");

  return (
    <div className="relative group">
      {isImage ? (
        <div className="w-16 h-16 rounded-xl overflow-hidden border border-border/50 bg-muted">
          {attachment.base64 ? (
            <img
              src={attachment.base64}
              alt={attachment.name || ""}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground text-[10px]">Kein Vorschau</div>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border/50 bg-muted max-w-[180px]">
          <FileText className="w-4 h-4 text-primary shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-medium truncate">{attachment.name || "Datei"}</p>
            <p className="text-[10px] text-muted-foreground">{fmt(attachment.size || 0)}</p>
          </div>
        </div>
      )}
      <button
        type="button"
        onClick={onRemove}
        className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity shadow-sm"
        title="Entfernen"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
});
