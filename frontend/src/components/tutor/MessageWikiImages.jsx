import { API } from "@/App";

export default function MessageWikiImages({ images, onLightbox }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="mt-4 pt-3 rounded-lg space-y-2" style={{ background: 'rgba(255,255,255,0.02)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider ml-3">Medizinische Abbildungen</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {images.map((img, i) => (
          <div key={i} className="relative cursor-pointer group"
              onClick={() => onLightbox({
                url: `${API}/knowledge-lab/assets/images/${img.filename}`,
                title: img.caption_de || '',
                _source: 'Wissensdatenbank',
                width: img.width,
                height: img.height,
              }, i)}>
            <div className="aspect-square rounded-lg overflow-hidden border"
              style={{ borderColor: 'rgba(59,130,246,0.15)' }}>
              <img src={`${API}/knowledge-lab/assets/images/${img.filename}`}
                alt={img.caption_de || ''}
                className="w-full h-full object-cover transition-all group-hover:scale-105 group-hover:border-blue-400/40"
                loading="lazy"
                onError={e => { e.target.style.display = 'none'; }} />
            </div>
            <span className="absolute top-1 left-1 text-[9px] px-1 py-[1px] rounded leading-tight"
              style={{ background: 'rgba(0,0,0,0.6)', color: 'rgba(255,255,255,0.6)' }}>
              Wissensdatenbank
            </span>
            {img.caption_de && (
              <p className="mt-1 text-[11px] text-white/40 truncate">{img.caption_de}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
