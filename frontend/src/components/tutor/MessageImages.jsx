export default function MessageImages({ images, onLightbox }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="mt-4 pt-3 px-3 rounded-lg border-t" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-2">Abbildungen</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {images.map((img, i) => (
          <div key={i} className="relative cursor-pointer group" onClick={() => onLightbox(img, i)}>
            <div className="aspect-square rounded-lg overflow-hidden border"
              style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
              {img.data ? (
                <img src={img.data} alt={img.title || ''} loading="lazy"
                  className="w-full h-full object-cover transition-opacity group-hover:opacity-80"
                  onError={e => { e.target.style.display = 'none'; }} />
              ) : (
                <a href={img.url} target="_blank" rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="block w-full h-full">
                  <img src={img.thumbnail} alt={img.title} loading="lazy"
                    className="w-full h-full object-cover transition-opacity group-hover:opacity-80"
                    onError={e => { e.target.style.display = 'none'; }} />
                </a>
              )}
            </div>
            {img._source && (
              <span className="absolute top-1 left-1 text-[9px] px-1 py-[1px] rounded leading-tight"
                style={{ background: 'rgba(0,0,0,0.6)', color: 'rgba(255,255,255,0.6)' }}>
                {img._source === 'local_db' ? '●' : '◌'} {img._source}
              </span>
            )}
            {img.title && (
              <p className="mt-1 text-xs text-white/40 truncate">{img.title}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
