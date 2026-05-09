import { memo, useState } from "react";
import { FileText, MessageSquare, Check, EyeOff, Trash2, ChevronDown, ChevronUp, User } from "lucide-react";
import { ModerationStatusPill } from "./ModerationStatusPill";
import { ReportReasonBadge } from "./ReportReasonBadge";
import { ModerationActionModal } from "./ModerationActionModal";
import { Button } from "@/components/ui/button";

function formatTs(ts) {
  const d = new Date(ts * 1000);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `vor ${mins} Min.`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `vor ${hrs} Std.`;
  return d.toLocaleDateString("de-AT", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export const ModerationQueueItem = memo(function ModerationQueueItem({
  item,
  isFocused,
  onFocus,
  onAction,
  reviewed,
}) {
  const [expanded, setExpanded] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const TypeIcon = item.target_type === "post" ? FileText : MessageSquare;

  const handleApprove = (e) => { e?.stopPropagation?.(); onAction(item, "approve"); };
  const handleHide    = (e) => { e?.stopPropagation?.(); onAction(item, "hide"); };
  const handleDelete  = (e) => { e?.stopPropagation?.(); setDeleteModalOpen(true); };

  return (
    <>
      <div
        tabIndex={0}
        onFocus={onFocus}
        className={`rounded-xl border bg-card transition-all outline-none ${
          isFocused
            ? "border-primary/60 ring-1 ring-primary/20 shadow-sm"
            : "border-border/40 hover:border-border/70"
        }`}
        aria-label={`${item.target_type === "post" ? "Beitrag" : "Kommentar"}: ${item.target_preview?.slice(0, 60) ?? "—"}`}
      >
        {/* Header row */}
        <div className="flex items-start gap-3 px-4 py-3">
          <div className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
            <TypeIcon className="w-3.5 h-3.5 text-muted-foreground" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="text-xs font-semibold text-foreground capitalize">
                {item.target_type === "post" ? "Beitrag" : "Kommentar"}
              </span>
              <ModerationStatusPill severity={item.severity} />
              {item.reason_key && <ReportReasonBadge reasonKey={item.reason_key} />}
              {reviewed && item.action_taken && (
                <ModerationStatusPill action={item.action_taken} />
              )}
              <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                {formatTs(item.created_at)}
              </span>
            </div>

            {/* Author */}
            {item.target_author_name && (
              <div className="flex items-center gap-1 mb-1">
                <User className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">{item.target_author_name}</span>
              </div>
            )}

            {/* Preview */}
            <p className={`text-xs text-foreground/80 leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
              {item.target_preview || <span className="italic text-muted-foreground">[Inhalt gelöscht]</span>}
            </p>

            {item.target_preview && item.target_preview.length > 120 && (
              <button
                onClick={() => setExpanded(v => !v)}
                className="text-[10px] text-primary hover:underline mt-0.5 flex items-center gap-0.5"
              >
                {expanded ? <><ChevronUp className="w-3 h-3" />Weniger</> : <><ChevronDown className="w-3 h-3" />Mehr</>}
              </button>
            )}
          </div>
        </div>

        {/* Action bar */}
        {!reviewed && (
          <div className="flex items-center gap-2 px-4 pb-3 border-t border-border/30 pt-2.5">
            <span className="text-[9px] text-muted-foreground/50 font-mono mr-auto">
              A·H·D
            </span>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5 text-emerald-600 border-emerald-500/30 hover:bg-emerald-500/10"
              onClick={handleApprove}
              aria-label="Genehmigen (A)"
              title="Genehmigen (A)"
            >
              <Check className="w-3.5 h-3.5" />
              Genehmigen
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5 text-slate-600 dark:text-slate-400 border-slate-500/30 hover:bg-slate-500/10"
              onClick={handleHide}
              aria-label="Ausblenden (H)"
              title="Ausblenden (H)"
            >
              <EyeOff className="w-3.5 h-3.5" />
              Ausblenden
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5 text-red-600 dark:text-red-400 border-red-500/30 hover:bg-red-500/10"
              onClick={handleDelete}
              aria-label="Löschen (D)"
              title="Löschen (D)"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Löschen
            </Button>
          </div>
        )}

        {/* Reviewed state footer */}
        {reviewed && item.reviewed_at && (
          <div className="px-4 pb-3 text-[10px] text-muted-foreground border-t border-border/30 pt-2.5">
            Bearbeitet {formatTs(new Date(item.reviewed_at).getTime() / 1000)}
            {item.reviewed_by && ` · ID ${item.reviewed_by.slice(0, 8)}…`}
          </div>
        )}
      </div>

      <ModerationActionModal
        open={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={(note) => { setDeleteModalOpen(false); onAction(item, "delete", note); }}
        action="delete"
        preview={item.target_preview}
      />
    </>
  );
});
