import { ExternalLink } from "lucide-react";

export default function MessageEvidence({ evidence, onPageViewer }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Quellen</p>
      {evidence.slice(0, 3).map((e, i) => (
        <div key={i} className="rounded-lg p-3 text-xs" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.1)' }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs" style={{ color: '#f59e0b' }}>📄</span>
            <span className="font-medium text-white/80">{e.filename}</span>
          </div>
          <div className="flex items-center gap-3 text-white/40 mb-1">
            <span>Kapitel: {e.chapter}</span>
            <span>Seite: {e.page_start}{e.page_end !== e.page_start ? `–${e.page_end}` : ''}</span>
          </div>
          <p className="text-white/50 leading-relaxed italic mb-2">
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
        </div>
      ))}
    </div>
  );
}
