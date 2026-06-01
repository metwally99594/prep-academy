import { API } from "@/App";

export default function MessageWikiImages({ images, onLightbox }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t space-y-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Medizinische Abbildungen</p>
      <div className="flex flex-wrap gap-2">
        {images.map((img, i) => (
          <div key={i} className="relative cursor-pointer group"
              onClick={() => onLightbox({
                url: `${API}/knowledge-lab/assets/images/${img.filename}`,
                title: img.caption_de || '',
                _source: 'Wissensdatenbank',
                width: img.width,
                height: img.height,
              })}>
            <img src={`${API}/knowledge-lab/assets/images/${img.filename}`}
              alt={img.caption_de || ''}
              className="w-[120px] h-[90px] object-cover rounded-lg border transition-all group-hover:scale-105 group-hover:border-blue-400/40"
              style={{ borderColor: 'rgba(59,130,246,0.15)' }}
              loading="lazy"
              onError={e => { e.target.style.display = 'none'; }} />
          </div>
        ))}
      </div>
    </div>
  );
}
