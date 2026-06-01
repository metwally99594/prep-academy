import { useEffect, useState } from "react";
import { X, ChevronLeft, ChevronRight, ImageOff } from "lucide-react";

export default function ImageLightbox({ image, images, index, onClose, onPrev, onNext }) {
  const hasGallery = Array.isArray(images) && images.length > 1 && typeof index === "number" && onPrev && onNext;
  const currentImage = hasGallery && index != null ? images[index] : image;

  // Fallback chain for non-base64 images:
  //   0 = try currentImage.url    (full-size)
  //   1 = try currentImage.thumbnail (smaller cached copy)
  //   2 = neither loaded — render placeholder
  // Resets to 0 whenever the displayed image changes (e.g., gallery navigation).
  const [fallbackLevel, setFallbackLevel] = useState(0);

  useEffect(() => {
    setFallbackLevel(0);
  }, [currentImage]);

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

  // Decide which image node to render.
  let imageNode = null;
  if (currentImage.data) {
    // Inline base64 — render as-is, preserve existing behaviour (no fallback chain).
    imageNode = (
      <img src={currentImage.data} alt={currentImage.title || ''}
        className="max-w-full max-h-[85vh] rounded-lg object-contain" />
    );
  } else if (fallbackLevel === 0 && currentImage.url) {
    imageNode = (
      <img src={currentImage.url} alt={currentImage.title || ''}
        className="max-w-full max-h-[85vh] rounded-lg object-contain"
        onError={() => {
          // eslint-disable-next-line no-console
          console.warn('[ImageLightbox] Full-size image failed to load:', currentImage.url);
          setFallbackLevel(1);
        }} />
    );
  } else if (fallbackLevel <= 1 && currentImage.thumbnail) {
    imageNode = (
      <img src={currentImage.thumbnail} alt={currentImage.title || ''}
        className="max-w-full max-h-[85vh] rounded-lg object-contain"
        onError={() => setFallbackLevel(2)} />
    );
  } else {
    imageNode = (
      <div
        className="flex flex-col items-center justify-center px-8 py-10 rounded-lg border text-white/50"
        style={{ background: 'rgba(0,0,0,0.4)', borderColor: 'rgba(255,255,255,0.08)', minWidth: 240 }}
      >
        <ImageOff className="w-10 h-10 mb-3 opacity-60" />
        <p className="text-sm">Bild konnte nicht geladen werden</p>
        {currentImage.url && (
          <a
            href={currentImage.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 text-xs text-blue-400 hover:underline"
          >
            Original in neuem Tab öffnen
          </a>
        )}
      </div>
    );
  }

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

        {imageNode}

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
