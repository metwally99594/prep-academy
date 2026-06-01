import { useEffect } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";

export default function ImageLightbox({ image, images, index, onClose, onPrev, onNext }) {
  const hasGallery = Array.isArray(images) && images.length > 1 && typeof index === "number" && onPrev && onNext;
  const currentImage = hasGallery && index != null ? images[index] : image;

  useEffect(() => {
    if (!currentImage) return;
    const handler = (e) => {
      if (e.key === "Escape") onClose();
      if (hasGallery) {
        if (e.key === "ArrowLeft") { e.preventDefault(); onPrev(); }
        if (e.key === "ArrowRight") { e.preventDefault(); onNext(); }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentImage, hasGallery, onClose, onPrev, onNext]);

  if (!currentImage) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}>
      <div className="relative max-w-[90vw] max-h-[90vh]" onClick={e => e.stopPropagation()}>
        <button onClick={onClose}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full flex items-center justify-center bg-black/60 border border-white/20 text-white/60 hover:text-white"
          style={{ background: '#0c1229' }}>
          <X className="w-4 h-4" />
        </button>

        {hasGallery && (
          <>
            <button onClick={onPrev}
              className="absolute left-2 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full flex items-center justify-center bg-black/50 text-white/60 hover:text-white hover:bg-black/70 transition-colors">
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button onClick={onNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full flex items-center justify-center bg-black/50 text-white/60 hover:text-white hover:bg-black/70 transition-colors">
              <ChevronRight className="w-5 h-5" />
            </button>
          </>
        )}

        {currentImage.data ? (
          <img src={currentImage.data} alt={currentImage.title || ''}
            className="max-w-full max-h-[85vh] rounded-lg object-contain" />
        ) : currentImage.url ? (
          <img src={currentImage.url} alt={currentImage.title || ''}
            className="max-w-full max-h-[85vh] rounded-lg object-contain" />
        ) : null}

        <div className="mt-2 flex items-center justify-between gap-3 text-xs text-white/40 px-1">
          <div className="flex items-center gap-3 min-w-0">
            {currentImage.title && <span className="truncate">{currentImage.title}</span>}
            {currentImage.width && <span className="shrink-0">{currentImage.width} × {currentImage.height}px</span>}
            {currentImage._source && <span className="shrink-0">{currentImage._source}</span>}
          </div>
          {hasGallery && (
            <span className="shrink-0">{index + 1} / {images.length}</span>
          )}
        </div>
      </div>
    </div>
  );
}
