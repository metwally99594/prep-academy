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
    <div className="answers-container">
      <p className="text-xs font-medium" style={{ color: '#3b82f6' }}>
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
            className={`answer-option ${status}`}
            data-testid={`choice-${index}`}
          >
            <div className="answer-circle">
              {status === 'correct' ? <Check className="w-4 h-4" /> :
               status === 'incorrect' ? <X className="w-4 h-4" /> :
               isSelected ? <Check className="w-4 h-4" /> :
               String.fromCharCode(65 + index)}
            </div>
            <p className="answer-text select-text">{choice.text_de || choice.text}</p>
          </button>
        );
      })}
    </div>
  );
}
