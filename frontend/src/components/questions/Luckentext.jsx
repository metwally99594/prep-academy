export default function Luckentext({ question, submitted, answer, onChange, result }) {
  const text = question.blank_text || "";
  const parts = text.split("___");

  return (
    <div className="space-y-3">
      <div className="text-base leading-loose">
        {parts.map((part, i) => (
          <span key={i}>
            <span>{part}</span>
            {i < parts.length - 1 && (
              submitted ? (
                <span className={`inline-block px-3 py-0.5 rounded mx-1 font-semibold text-sm ${
                  result?.is_correct
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30 line-through'
                }`}>
                  {answer || '—'}
                </span>
              ) : (
                <input
                  type="text"
                  value={answer || ""}
                  onChange={e => onChange(e.target.value)}
                  className="inline-block border-b-2 border-[#3b82f6] bg-transparent text-center font-semibold mx-1 outline-none text-sm w-36 pb-0.5"
                  placeholder="Antwort eingeben"
                  autoComplete="off"
                />
              )
            )}
          </span>
        ))}
      </div>
      {submitted && result && !result.is_correct && (
        <div className="p-3 rounded-xl bg-muted/20 text-sm">
          <span className="text-muted-foreground">Richtige Antwort: </span>
          <span className="text-emerald-400 font-semibold">
            {(question.blank_answers || []).join(" / ")}
          </span>
        </div>
      )}
    </div>
  );
}
