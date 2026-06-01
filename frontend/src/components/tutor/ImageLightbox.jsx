import { X } from "lucide-react";

export default function ImageLightbox({ image, onClose }) {
  if (!image) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}>
      <div className="relative max-w-[90vw] max-h-[90vh]" onClick={e => e.stopPropagation()}>
        <button onClick={onClose}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full flex items-center justify-center bg-black/60 border border-white/20 text-white/60 hover:text-white"
          style={{ background: '#0c1229' }}>
          <X className="w-4 h-4" />
        </button>
        {image.data ? (
          <img src={image.data} alt={image.title || ''}
            className="max-w-full max-h-[85vh] rounded-lg object-contain" />
        ) : image.url ? (
          <img src={image.url} alt={image.title || ''}
            className="max-w-full max-h-[85vh] rounded-lg object-contain" />
        ) : null}
        <div className="mt-2 flex items-center gap-3 text-xs text-white/40 px-1">
          {image.title && <span>{image.title}</span>}
          {image.width && <span>{image.width} × {image.height}px</span>}
          {image._source && <span>{image._source}</span>}
        </div>
      </div>
    </div>
  );
}
