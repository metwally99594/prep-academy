import { memo } from "react";

export const TagPicker = memo(function TagPicker({ options, selected, onChange, label, max = 3 }) {
  const toggle = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter(v => v !== value));
    } else if (selected.length < max) {
      onChange([...selected, value]);
    }
  };

  return (
    <div>
      {label && (
        <p className="text-xs font-medium text-muted-foreground mb-2">
          {label}
          {selected.length > 0 && (
            <span className="ml-2 text-primary">({selected.length}/{max})</span>
          )}
        </p>
      )}
      <div className="flex flex-wrap gap-1.5">
        {options.map(({ value, label: optLabel }) => {
          const isSelected = selected.includes(value);
          const isDisabled = !isSelected && selected.length >= max;
          return (
            <button
              key={value}
              type="button"
              onClick={() => toggle(value)}
              disabled={isDisabled}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                isSelected
                  ? "bg-primary text-primary-foreground"
                  : isDisabled
                    ? "bg-muted/40 text-muted-foreground/40 cursor-not-allowed"
                    : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {optLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
});
