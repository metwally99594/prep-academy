export default function MessageMCQ({ analysis }) {
  if (!analysis) return null;

  return (
    <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Antwortanalyse</p>
      <div className="rounded-lg p-3" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.15)' }}>
        <div className="flex items-start gap-2">
          <span className="text-green-400 text-sm mt-0.5">✅</span>
          <div>
            <span className="text-green-400 font-bold text-sm">{analysis.correct_answer}</span>
            <p className="text-white/70 text-xs mt-0.5">{analysis.correct_reason}</p>
          </div>
        </div>
      </div>
      {analysis.wrong_answers.map((wa, i) => (
        <div key={i} className="rounded-lg p-3" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.12)' }}>
          <div className="flex items-start gap-2">
            <span className="text-red-400 text-sm mt-0.5">❌</span>
            <div>
              <span className="text-red-400 font-bold text-sm">{wa.option}</span>
              <p className="text-white/60 text-xs mt-0.5">{wa.reason}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
