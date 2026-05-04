import { useState } from "react";

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
    return (
      <div className="space-y-2">
        <label className="font-medium">Lückentext (Satz mit Lücke)</label>
        <input className="w-full border p-2 rounded"
          placeholder="z.B. Das Herz pumpt ___ durch den Körper"
          value={formData.blank_text || ""}
          onChange={e => setFormData({ ...formData, blank_text: e.target.value })} />
        <label className="font-medium">Richtige Antworten (kommagetrennt)</label>
        <input className="w-full border p-2 rounded"
          placeholder="z.B. Blut, blood"
          value={(formData.blank_answers || []).join(", ")}
          onChange={e => setFormData({
            ...formData,
            blank_answers: e.target.value.split(",").map(s => s.trim())
          })} />
      </div>
    );
  }

  return null;
}