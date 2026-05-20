import { useState, useMemo } from "react";
import { Plus, Trash2, Check, X, ChevronDown } from "lucide-react";

const makeId = () => Math.random().toString(36).slice(2, 9);

export default function QuestionTypeFields({ questionType, formData, setFormData }) {
  const addDragDropItem = () => {
    const items = formData.drag_drop_items || [];
    setFormData({
      ...formData,
      drag_drop_items: [...items, { id: Date.now().toString(), text: "", correct_category: "" }]
    });
  };

  const addDragDropCategory = () => {
    const cats = formData.drag_drop_categories || [];
    setFormData({
      ...formData,
      drag_drop_categories: [...cats, { id: Date.now().toString(), text: "" }]
    });
  };

  if (questionType === "drag_drop" || questionType === "kategorisierung") {
    return (
      <div className="space-y-4">
        <div>
          <label className="font-medium">Kategorien</label>
          {(formData.drag_drop_categories || []).map((cat, i) => (
            <input key={cat.id} className="w-full border p-2 rounded mt-1"
              placeholder={`Kategorie ${i + 1}`} value={cat.text}
              onChange={e => {
                const cats = [...(formData.drag_drop_categories || [])];
                cats[i] = { ...cats[i], text: e.target.value };
                setFormData({ ...formData, drag_drop_categories: cats });
              }} />
          ))}
          <button type="button" onClick={addDragDropCategory}
            className="mt-2 text-sm text-blue-600">+ Kategorie hinzufügen</button>
        </div>
        <div>
          <label className="font-medium">Begriffe</label>
          {(formData.drag_drop_items || []).map((item, i) => (
            <div key={item.id} className="flex gap-2 mt-1">
              <input className="flex-1 border p-2 rounded" placeholder="Begriff"
                value={item.text}
                onChange={e => {
                  const items = [...(formData.drag_drop_items || [])];
                  items[i] = { ...items[i], text: e.target.value };
                  setFormData({ ...formData, drag_drop_items: items });
                }} />
              <select className="border p-2 rounded" value={item.correct_category}
                onChange={e => {
                  const items = [...(formData.drag_drop_items || [])];
                  items[i] = { ...items[i], correct_category: e.target.value };
                  setFormData({ ...formData, drag_drop_items: items });
                }}>
                <option value="">Kategorie wählen</option>
                {(formData.drag_drop_categories || []).map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.text}</option>
                ))}
              </select>
            </div>
          ))}
          <button type="button" onClick={addDragDropItem}
            className="mt-2 text-sm text-blue-600">+ Begriff hinzufügen</button>
        </div>
      </div>
    );
  }

  if (questionType === "luckentext") {
    return <LuckentextBuilder formData={formData} setFormData={setFormData} />;
  }

  return null;
}

function blankTextToSentence(text) {
  let idx = 0;
  return (text || "").replace(/___/g, () => `[${++idx}]`);
}

function sentenceToBlankText(text) {
  return (text || "").replace(/\[\d+\]/g, "___");
}

function blanksToAnswers(blanks) {
  return blanks.filter(Boolean).map(b => {
    if (b.type === "text") return b.answer || "";
    const correct = (b.options || []).find(o => o.correct);
    return correct?.text || "";
  });
}

function LuckentextBuilder({ formData, setFormData }) {
  const [sentence, setSentence] = useState(() => blankTextToSentence(formData.blank_text));
  const [blanks, setBlanks] = useState(() => {
    if (Array.isArray(formData.blanks) && formData.blanks.length > 0) {
      return formData.blanks.map(b => ({ ...b, id: b.id || makeId() }));
    }
    const ba = formData.blank_answers || [];
    if (ba.length > 0) {
      return ba.map((ans, i) => ({ id: makeId(), type: "text", answer: ans, options: [] }));
    }
    return [];
  });

  const markerNums = useMemo(() => {
    const nums = [];
    const re = /\[(\d+)\]/g;
    let m;
    while ((m = re.exec(sentence)) !== null) {
      const n = parseInt(m[1], 10);
      if (!nums.includes(n)) nums.push(n);
    }
    return nums.sort((a, b) => a - b);
  }, [sentence]);

  const effectiveBlanks = useMemo(() => {
    const b = [...blanks];
    let changed = false;
    for (const n of markerNums) {
      while (b.length < n) {
        b.push({ id: makeId(), type: "text", answer: "", options: [] });
        changed = true;
      }
      if (!b[n - 1]) {
        b[n - 1] = { id: makeId(), type: "text", answer: "", options: [] };
        changed = true;
      }
    }
    return changed ? b : blanks;
  }, [blanks, markerNums]);

  const maxMarker = markerNums.length > 0 ? Math.max(...markerNums) : 0;

  const syncForm = (newSentence, newBlanks) => {
    const bt = sentenceToBlankText(newSentence != null ? newSentence : sentence);
    const blk = newBlanks != null ? newBlanks : effectiveBlanks;
    const ba = blanksToAnswers(blk);
    setFormData(prev => ({ ...prev, blank_text: bt, blank_answers: ba, blanks: blk }));
  };

  const handleSentenceChange = (e) => {
    const val = e.target.value;
    setSentence(val);
    syncForm(val, null);
  };

  const insertMarker = () => {
    const next = maxMarker + 1;
    const newSentence = sentence + ` [${next}] `;
    setSentence(newSentence);
    const newBlanks = [...effectiveBlanks];
    while (newBlanks.length < next) {
      newBlanks.push({ id: makeId(), type: "text", answer: "", options: [] });
    }
    if (!newBlanks[next - 1]) {
      newBlanks[next - 1] = { id: makeId(), type: "text", answer: "", options: [] };
    }
    setBlanks(newBlanks);
    syncForm(newSentence, newBlanks);
  };

  const toggleType = (idx) => {
    const b = effectiveBlanks[idx];
    if (!b) return;
    let newBlanks;
    if (b.type === "text") {
      newBlanks = effectiveBlanks.map((bl, i) => i === idx ? {
        ...bl, type: "dropdown",
        options: [
          { id: makeId(), text: "", correct: true },
          { id: makeId(), text: "", correct: false },
        ],
        answer: undefined,
      } : bl);
    } else {
      newBlanks = effectiveBlanks.map((bl, i) => i === idx ? { ...bl, type: "text", answer: "", options: [] } : bl);
    }
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const updateAnswer = (idx, answer) => {
    const newBlanks = effectiveBlanks.map((b, i) => i === idx ? { ...b, answer } : b);
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const addOption = (idx) => {
    const b = effectiveBlanks[idx];
    if (!b || b.type !== "dropdown") return;
    const newBlanks = effectiveBlanks.map((bl, i) => i === idx ? {
      ...bl,
      options: [...bl.options, { id: makeId(), text: "", correct: false }],
    } : bl);
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const removeOption = (idx, oid) => {
    const b = effectiveBlanks[idx];
    if (!b || b.type !== "dropdown" || b.options.length <= 2) return;
    const newBlanks = effectiveBlanks.map((bl, i) => i === idx ? {
      ...bl,
      options: bl.options.filter(o => o.id !== oid),
    } : bl);
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const updateOption = (idx, oid, text) => {
    const b = effectiveBlanks[idx];
    if (!b || b.type !== "dropdown") return;
    const newBlanks = effectiveBlanks.map((bl, i) => i === idx ? {
      ...bl,
      options: bl.options.map(o => o.id === oid ? { ...o, text } : o),
    } : bl);
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const setCorrect = (idx, oid) => {
    const b = effectiveBlanks[idx];
    if (!b || b.type !== "dropdown") return;
    const newBlanks = effectiveBlanks.map((bl, i) => i === idx ? {
      ...bl,
      options: bl.options.map(o => ({ ...o, correct: o.id === oid })),
    } : bl);
    setBlanks(newBlanks);
    syncForm(null, newBlanks);
  };

  const previewParts = useMemo(() => sentence.split(/(\[\d+\])/g), [sentence]);

  return (
    <div className="builder-luckentext">
      <div className="builder-luckentext-header">
        <span className="builder-luckentext-badge">LÜCKENTEXT · BUILDER</span>
      </div>

      <label className="builder-luckentext-label">SATZ MIT LÜCKEN ([1] [2] … für jede Lücke)</label>
      <textarea value={sentence}
        onChange={handleSentenceChange}
        className="builder-textarea"
        placeholder='z.B. Gestern [1] ich ins Kino und der Film war [2].'
        rows={2} />

      <button onClick={insertMarker} className="builder-btn-add-blank" style={{ marginBottom: 16 }}>
        <Plus size={16} /> Lücke einfügen [N]
      </button>

      <label className="builder-luckentext-label">VORSCHAU</label>
      <div className="builder-luckentext-preview">
        {previewParts.map((part, i) => {
          const match = part.match(/^\[(\d+)\]$/);
          if (match) {
            const idx = parseInt(match[1], 10) - 1;
            const b = effectiveBlanks[idx];
            if (b?.type === "dropdown") {
              const correct = b.options.find(o => o.correct);
              return (
                <span key={i} className="builder-blank-chip builder-blank-dropdown" title="Dropdown">
                  {correct?.text || "dropdown"} <ChevronDown size={12} />
                </span>
              );
            }
            return (
              <span key={i} className="builder-blank-chip builder-blank-text" title="Texteingabe">
                {b?.answer || "..."}
              </span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </div>

      <label className="builder-luckentext-label">LÜCKEN DEFINIEREN</label>
      <div className="builder-luckentext-blanks">
        {markerNums.map(n => {
          const idx = n - 1;
          const b = effectiveBlanks[idx];
          if (!b) return null;
          return (
            <div key={`m${n}`} className="builder-blank-editor">
              <div className="builder-blank-editor-header">
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="builder-luckentext-badge-sm">Lücke [{n}]</span>
                  <select value={b.type} onChange={() => toggleType(idx)}
                    className="builder-type-select">
                    <option value="text">Texteingabe</option>
                    <option value="dropdown">Dropdown</option>
                  </select>
                </div>
              </div>

              {b.type === "text" ? (
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
                  <span className="builder-label-sm">Richtige Antwort:</span>
                  <input value={b.answer || ""} onChange={e => updateAnswer(idx, e.target.value)}
                    placeholder="Richtige Antwort" className="builder-input builder-input-sm" />
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
                  {b.options.map(opt => (
                    <div key={opt.id}
                      className={`builder-option-row ${opt.correct ? "builder-option-correct" : ""}`}>
                      <button onClick={() => setCorrect(idx, opt.id)}
                        className={`builder-correct-btn ${opt.correct ? "builder-correct-active" : ""}`}
                        title={opt.correct ? "Richtige Antwort" : "Als richtig markieren"}>
                        {opt.correct && <Check size={13} />}
                      </button>
                      <input value={opt.text} onChange={e => updateOption(idx, opt.id, e.target.value)}
                        placeholder={opt.correct ? "Richtige Antwort" : "Falsche Option"}
                        className="builder-input builder-option-input" />
                      {opt.correct ? (
                        <span className="builder-correct-label">RICHTIG</span>
                      ) : (
                        b.options.length > 2 && (
                          <button onClick={() => removeOption(idx, opt.id)}
                            className="builder-btn-icon-sm" title="Option entfernen">
                            <X size={13} />
                          </button>
                        )
                      )}
                    </div>
                  ))}
                  <button onClick={() => addOption(idx)}
                    className="builder-btn-add-option">
                    <Plus size={14} /> Option hinzufügen
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
