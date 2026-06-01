export default function MessageImages({ images, onLightbox }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      {images.map((img, i) => (
        <div key={i} className="relative cursor-pointer" onClick={() => onLightbox(img)}>
          {img.data ? (
            <div className="block rounded-lg overflow-hidden border hover:opacity-80 transition-opacity"
              style={{ borderColor: 'rgba(255,255,255,0.08)', width: 120, height: 90 }}>
              <img src={img.data} alt={img.title || ''} loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
            </div>
          ) : (
            <a href={img.url} target="_blank" rel="noopener noreferrer"
              className="block rounded-lg overflow-hidden border transition-opacity hover:opacity-80"
              style={{ borderColor: 'rgba(255,255,255,0.08)', width: 120, height: 90 }}
              onClick={e => e.stopPropagation()}>
              <img src={img.thumbnail} alt={img.title} loading="lazy" className="w-full h-full object-cover" onError={e => { e.target.style.display = 'none'; }} />
            </a>
          )}
          {img._source && (
            <span className="absolute bottom-0 right-0 text-[9px] px-1 py-[1px] rounded-tl leading-tight"
              style={{ background: 'rgba(0,0,0,0.6)', color: 'rgba(255,255,255,0.6)' }}>
              {img._source === 'local_db' ? '●' : '◌'} {img._source}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
