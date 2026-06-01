import { useState } from "react";
import { ExternalLink, FileText, ChevronDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";

export default function MessageEvidence({ evidence, onPageViewer }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Quellen</p>
      {evidence.slice(0, 3).map((e, i) => (
        <EvidenceCard key={i} evidence={e} onPageViewer={onPageViewer} />
      ))}
    </div>
  );
}

function EvidenceCard({ evidence: e, onPageViewer }) {
  const [open, setOpen] = useState(false);

  return (
    <Card className="border-0" style={{ background: 'rgba(245,158,11,0.06)' }}>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="w-full">
          <CardContent className="p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-3.5 h-3.5 shrink-0" style={{ color: '#f59e0b' }} />
                <span className="font-medium text-xs text-white/80 truncate">{e.filename}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-white/40 whitespace-nowrap">
                  S. {e.page_start}{e.page_end !== e.page_start ? `–${e.page_end}` : ''}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-white/40 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
              </div>
            </div>
          </CardContent>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="px-3 pb-3 pt-0">
            <p className="text-xs text-white/50 leading-relaxed italic mb-2 line-clamp-4">
              &ldquo;{e.excerpt}&rdquo;
            </p>
            {e.document_id && (
              <button onClick={() => onPageViewer(e.document_id, e.page_start)}
                className="flex items-center gap-1 text-[11px] px-2 py-1 rounded transition-colors"
                style={{ color: '#f59e0b', border: '1px solid rgba(245,158,11,0.2)' }}>
                <ExternalLink className="w-3 h-3" />
                Seite {e.page_start} öffnen
              </button>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
