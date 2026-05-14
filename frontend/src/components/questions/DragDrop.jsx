import { useState } from "react";
import { Check, X } from "lucide-react";

export default function DragDrop({ question, submitted, answer, onChange, result }) {
  const [selectedItem, setSelectedItem] = useState(null);

  const items = question.drag_drop_items || [];
  const categories = question.drag_drop_categories || [];
  const assignedItems = answer || {};
  const unassignedItems = items.filter(item => !assignedItems[item.id]);

  const handleItemClick = (itemId) => {
    if (submitted) return;
    setSelectedItem(prev => prev === itemId ? null : itemId);
  };

  const handleCategoryClick = (catId) => {
    if (submitted || !selectedItem) return;
    onChange({ ...assignedItems, [selectedItem]: catId });
    setSelectedItem(null);
  };

  const removeFromCategory = (e, itemId) => {
    e.stopPropagation();
    if (submitted) return;
    const next = { ...assignedItems };
    delete next[itemId];
    onChange(next);
  };

  const getItemStatus = (item) => {
    if (!submitted) return null;
    return assignedItems[item.id] === item.correct_category ? "correct" : "incorrect";
  };

  return (
    <div className="space-y-4">
      {/* Unassigned pool */}
      <div className="p-4 rounded-xl border border-border/30 bg-muted/10 min-h-[60px]">
        <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">Begriffe</p>
        <div className="flex flex-wrap gap-2">
          {unassignedItems.map(item => (
            <button
              key={item.id}
              onClick={() => handleItemClick(item.id)}
              disabled={submitted}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-[color,background-color,border-color,box-shadow] ${
                selectedItem === item.id
                  ? 'border-[#3b82f6] bg-[#3b82f6]/20 text-[#3b82f6] shadow-sm'
                  : 'border-border/40 bg-muted/30 hover:border-[#3b82f6]/40 hover:bg-muted/50'
              }`}
            >
              {item.text}
            </button>
          ))}
          {unassignedItems.length === 0 && !submitted && (
            <span className="text-xs text-muted-foreground italic">Alle Begriffe zugeordnet ✓</span>
          )}
        </div>
        {selectedItem && !submitted && (
          <p className="text-xs mt-2" style={{ color: '#3b82f6' }}>
            → Klicke auf eine Kategorie, um den Begriff zuzuordnen
          </p>
        )}
      </div>

      {/* Category buckets */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {categories.map(cat => {
          const catItems = items.filter(item => assignedItems[item.id] === cat.id);
          const isTarget = !submitted && !!selectedItem;
          return (
            <div
              key={cat.id}
              onClick={() => handleCategoryClick(cat.id)}
              className={`p-3 rounded-xl border-2 min-h-[80px] transition-[color,background-color,border-color] ${
                submitted
                  ? 'cursor-default border-border/20 bg-muted/5'
                  : isTarget
                  ? 'border-[#3b82f6]/60 bg-[#3b82f6]/5 cursor-pointer hover:bg-[#3b82f6]/10'
                  : 'border-border/30 bg-muted/10'
              }`}
            >
              <p className="text-sm font-semibold mb-2">{cat.text}</p>
              <div className="flex flex-wrap gap-1.5">
                {catItems.map(item => {
                  const status = getItemStatus(item);
                  return (
                    <span
                      key={item.id}
                      onClick={e => removeFromCategory(e, item.id)}
                      className={`px-2 py-1 rounded-md text-xs font-medium inline-flex items-center gap-1 transition-colors ${
                        status === 'correct'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : status === 'incorrect'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : 'bg-[#3b82f6]/20 text-[#3b82f6] border border-[#3b82f6]/30 cursor-pointer hover:bg-red-500/10 hover:text-red-400'
                      }`}
                    >
                      {status === 'correct' && <Check className="w-3 h-3" />}
                      {status === 'incorrect' && <X className="w-3 h-3" />}
                      {item.text}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Correct answer reveal after wrong submission */}
      {submitted && result && !result.is_correct && (
        <div className="p-3 rounded-xl bg-muted/20 space-y-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Richtige Zuordnung:</p>
          {items.map(item => {
            const correctCat = categories.find(c => c.id === item.correct_category);
            return (
              <p key={item.id} className="text-xs">
                <span className="font-medium">{item.text}</span>
                <span className="text-muted-foreground"> → </span>
                <span className="text-emerald-400 font-medium">{correctCat?.text || '?'}</span>
              </p>
            );
          })}
        </div>
      )}
    </div>
  );
}
