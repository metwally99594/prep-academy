import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { Check, Trash2, ChevronDown } from "lucide-react";

const makeId = () => Math.random().toString(36).slice(2, 9);

function parseBlanks(question) {
  const blankText = typeof question?.blank_text === 'string' ? question.blank_text : "";
  if (question?.blanks && Array.isArray(question.blanks) && question.blanks.length > 0) {
    let idx = 0;
    return {
      sentence: blankText.replace(/___/g, () => `[${++idx}]`),
      blanks: question.blanks,
    };
  }
  const blankAnswers = Array.isArray(question?.blank_answers) ? question.blank_answers : [];
  if (blankAnswers.length > 0) {
    let idx = 0;
    return {
      sentence: blankText.replace(/___/g, () => `[${++idx}]`),
      blanks: blankAnswers.map((ans, i) => ({
        id: `legacy-${i}`,
        type: "text",
        answer: typeof ans === 'string' ? ans : "",
        acceptedAnswers: typeof ans === 'string' ? [ans] : [],
        options: [],
      })),
    };
  }
  return { sentence: "", blanks: [] };
}

function isAnswerCorrect(ans, blank) {
  if (!blank || ans == null || ans === "") return null;
  if (blank.type === "text") {
    const accepted = blank.acceptedAnswers && blank.acceptedAnswers.length > 0
      ? blank.acceptedAnswers
      : (blank.answer ? [blank.answer] : []);
    return accepted.some(a => ans.trim().toLowerCase() === a.trim().toLowerCase()) ? "ok" : "bad";
  }
  const opt = (blank.options ?? []).find(o => o.text === ans);
  return opt?.correct ? "ok" : "bad";
}

export default function Luckentext({ question, submitted, answer, onChange, result }) {
  const { sentence, blanks } = useMemo(() => parseBlanks(question), [question]);

  return (
    <LuckentextInner
      sentence={sentence}
      blanks={blanks}
      submitted={submitted}
      externalAnswer={answer}
      onChange={onChange}
      result={result}
    />
  );
}

function LuckentextInner({ sentence, blanks, submitted, externalAnswer, onChange, result }) {
  const [answers, setAnswers] = useState({});
  const [openDropdown, setOpenDropdown] = useState(null);
  const initDone = useRef(false);

  useEffect(() => {
    if (!initDone.current && externalAnswer) {
      try {
        const parsed = JSON.parse(externalAnswer);
        if (typeof parsed === "object" && parsed !== null) {
          setAnswers(parsed);
        }
      } catch {}
      initDone.current = true;
    }
  }, [externalAnswer]);

  const setAnswer = useCallback((blankIdx, value) => {
    setAnswers(prev => {
      const next = { ...prev, [blankIdx]: value };
      if (onChange) onChange(JSON.stringify(next));
      return next;
    });
    setOpenDropdown(null);
  }, [onChange]);

  const parts = useMemo(() => sentence.split(/(\[\d+\])/g), [sentence]);

  const filledCount = useMemo(() =>
    Object.keys(answers).filter(k => answers[k] && answers[k].trim() !== '').length,
  [answers]);

  const evaluate = useCallback((blankIdx) => {
    if (!submitted) return null;
    return isAnswerCorrect(answers[blankIdx], blanks[blankIdx]);
  }, [submitted, blanks, answers]);

  const score = useMemo(() => {
    if (!submitted) return null;
    let correct = 0;
    blanks.forEach((b, i) => {
      const e = evaluate(i);
      if (e === "ok") correct++;
    });
    return { correct, total: blanks.length };
  }, [submitted, evaluate, blanks]);

  const reset = useCallback(() => {
    setAnswers({});
    setOpenDropdown(null);
    if (onChange) onChange("");
  }, [onChange]);

  if (blanks.length === 0) {
    return <p className="text-sm text-muted-foreground">Keine Lücken definiert.</p>;
  }

  const progressPct = blanks.length > 0 ? (filledCount / blanks.length) * 100 : 0;

  return (
    <div className="luckentext-card">
      <div className="luckentext-header">
        <span className="luckentext-badge">LÜCKENTEXT</span>
        <span className="luckentext-progress-text">{filledCount}/{blanks.length} ausgefüllt</span>
      </div>

      <div className="luckentext-progress-wrap">
        <div className="luckentext-progress-fill" style={{ width: `${progressPct}%` }} />
      </div>

      <p className="luckentext-instruction">FÜLLEN SIE DIE LÜCKEN AUS</p>

      <div className="luckentext-body">
        {parts.map((part, i) => {
          const match = part.match(/^\[(\d+)\]$/);
          if (match) {
            const idx = parseInt(match[1], 10) - 1;
            const blank = blanks[idx];
            if (!blank) return <span key={i} className="luckentext-error">[?]</span>;
            const resultState = evaluate(idx);
            if (blank.type === "text") {
              return (
                <LuckentextTextBlank
                  key={i}
                  value={answers[idx] || ""}
                  onChange={v => setAnswer(idx, v)}
                  result={resultState}
                />
              );
            }
            return (
              <LuckentextDropdownBlank
                key={i}
                blank={blank}
                value={answers[idx]}
                onChange={v => setAnswer(idx, v)}
                isOpen={openDropdown === idx}
                onToggle={() => setOpenDropdown(openDropdown === idx ? null : idx)}
                result={resultState}
              />
            );
          }
          return <span key={i} className="luckentext-text">{part}</span>;
        })}
      </div>

      {submitted && score && (
        <div className="luckentext-score">
          <div>
            <p className="luckentext-score-label">ERGEBNIS</p>
            <p className="luckentext-score-value">{score.correct} von {score.total} richtig</p>
          </div>
          <div className="luckentext-score-pct" style={{
            color: score.total > 0
              ? (score.correct === score.total ? '#1d9e75' : score.correct >= score.total / 2 ? '#c9a227' : '#d85a30')
              : '#7a6a3a'
          }}>
            {score.total > 0 ? `${Math.round((score.correct / score.total) * 100)}%` : '—'}
          </div>
        </div>
      )}

      {!submitted && (
        <div className="luckentext-actions">
          <button onClick={reset} className="luckentext-btn-secondary">
            <Trash2 size={15} /> Zurücksetzen
          </button>
        </div>
      )}
    </div>
  );
}

function LuckentextTextBlank({ value, onChange, result }) {
  let className = "luckentext-input";
  if (result === "ok") className += " ok";
  else if (result === "bad") className += " bad";
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder="…"
      className={className}
      autoComplete="off"
    />
  );
}

function LuckentextDropdownBlank({ blank, value, onChange, isOpen, onToggle, result }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) onToggle(); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen, onToggle]);

  let btnClass = "luckentext-dropdown-trigger";
  if (value) btnClass += " has-value";
  if (isOpen) btnClass += " luckentext-dropdown-open";
  if (result === "ok") btnClass += " ok";
  else if (result === "bad") btnClass += " bad";

  return (
    <span ref={ref} className="luckentext-dropdown-wrap">
      <button onClick={onToggle} className={btnClass}>
        <span>{value || "wählen…"}</span>
        <ChevronDown size={15} className={`luckentext-chevron ${isOpen ? "luckentext-chevron-open" : ""}`} />
      </button>
      {isOpen && (
        <div className="luckentext-dropdown-menu">
          {(blank.options ?? []).map(opt => {
            const selected = value === opt.text;
            return (
              <button
                key={opt.id}
                onClick={() => onChange(opt.text)}
                className={`luckentext-dropdown-item ${selected ? "luckentext-dropdown-item-selected" : ""}`}
              >
                <span className="luckentext-radio">
                  {selected && <Check size={11} />}
                </span>
                {opt.text}
              </button>
            );
          })}
        </div>
      )}
    </span>
  );
}
