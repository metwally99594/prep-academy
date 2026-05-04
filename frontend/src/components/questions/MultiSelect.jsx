import { Check, X } from "lucide-react";

export default function MultiSelect({ question, submitted, selectedChoices, onToggle, result }) {
  const choices = question.choices || [];

  const getStatus = (choice) => {
    if (!submitted) return selectedChoices.includes(choice.id) ? "selected" : "default";
    if (result?.correct_choice_ids?.includes(choice.id)) return "correct";
    if (selectedChoices.includes(choice.id)) return "incorrect";
    return "default";
  };

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium" style={{ color: '#c9a84c' }}>
        Mehrere Antworten möglich – alle richtigen auswählen
      </p>
      {choices.map((choice, index) => {
        const status = getStatus(choice);
        const isSelected = selectedChoices.includes(choice.id);
        return (
          <button
            key={choice.id}
            onClick={() => onToggle(choice.id)}
            disabled={submitted}
            className={`choice-btn w-full text-left p-4 rounded-xl flex items-center gap-4 ${
              status === 'correct' ? 'correct' :
              status === 'incorrect' ? 'incorrect' :
              isSelected ? 'selected' : ''
            }`}
            data-testid={`choice-${index}`}
          >
            <div className={`w-9 h-9 rounded flex items-center justify-center text-sm font-medium flex-shrink-0 border-2 ${
              status === 'correct' ? 'bg-emerald-500 text-white border-emerald-500' :
              status === 'incorrect' ? 'bg-red-500 text-white border-red-500' :
              isSelected ? 'border-[#c9a84c] bg-[#c9a84c]/20 text-[#c9a84c]' :
              'border-muted-foreground/30 text-muted-foreground'
            }`}>
              {status === 'correct' ? <Check className="w-4 h-4" /> :
               status === 'incorrect' ? <X className="w-4 h-4" /> :
               isSelected ? <Check className="w-4 h-4" /> :
               String.fromCharCode(65 + index)}
            </div>
            <p className="flex-1 font-medium select-text">{choice.text_de || choice.text}</p>
          </button>
        );
      })}
    </div>
  );
}
