export default function MessageSources({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t space-y-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Wissensdatenbank</p>
      {sources.slice(0, 3).map((w, i) => (
        <div key={i} className="rounded-lg p-3 text-xs" style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.1)' }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs" style={{ color: '#3b82f6' }}>📚</span>
            <span className="font-medium text-white/80">{w.title}</span>
          </div>
          <div className="text-white/40 mb-1">
            <span>Kategorie: {w.category}</span>
          </div>
          <p className="text-white/50 leading-relaxed italic">
            &ldquo;{w.excerpt}&rdquo;
          </p>
        </div>
      ))}
    </div>
  );
}
