import { Button } from "@/components/ui/button";
import { BookOpen, X, Loader2 } from "lucide-react";

export default function PageViewerModal({ showPageViewer, pageViewerDocId, pageViewerPage, pageViewerImages, pageViewerLoading, onClose }) {
  if (!showPageViewer) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) { onClose(); } }}>
      <div className="w-full max-w-4xl max-h-[85vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden animate-fadeIn"
        style={{ background: '#0c1229', borderColor: 'rgba(245,158,11,0.15)' }}>
        <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
          style={{ borderColor: 'rgba(245,158,11,0.1)', background: 'rgba(245,158,11,0.03)' }}>
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" style={{ color: '#f59e0b' }} />
            <span className="text-sm font-medium text-white/80">Seite {pageViewerPage}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-white/40 hover:text-white">
            <X className="w-5 h-5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {pageViewerLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 animate-spin text-white/30" />
            </div>
          ) : pageViewerImages.length === 0 ? (
            <p className="text-white/30 text-center py-20">Keine Bilder auf dieser Seite gefunden.</p>
          ) : (
            <div className="space-y-4">
              {pageViewerImages.map((img, i) => (
                <div key={i} className="rounded-lg overflow-hidden border"
                  style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
                  <img src={img.data_url} alt={`Seite ${img.page}`}
                    className="w-full h-auto" loading="lazy" />
                  {img.description && (
                    <p className="text-xs text-white/40 px-3 py-2" style={{ background: 'rgba(0,0,0,0.2)' }}>
                      {img.description}
                    </p>
                  )}
                  {img.width && (
                    <p className="text-[10px] text-white/20 px-3 pb-2">
                      {img.width} × {img.height}px
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
