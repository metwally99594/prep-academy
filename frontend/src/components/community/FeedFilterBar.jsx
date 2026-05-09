import { memo } from "react";
import { Search, X } from "lucide-react";
import {
  SPECIALTY_OPTIONS, SPECIALTY_LABELS,
  TOPIC_OPTIONS, TOPIC_LABELS,
  SORT_OPTIONS,
} from "./communityConstants";

export const FeedFilterBar = memo(function FeedFilterBar({
  filters,
  setFilter,
  searchInput,
  onSearchInput,
  hasActiveFilters,
  onClear,
}) {
  return (
    <div className="space-y-2 mb-4">
      {/* Sort tabs */}
      <div className="flex gap-1 bg-muted/40 rounded-xl p-1">
        {SORT_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setFilter("sort", opt.value)}
            className={`flex-1 text-xs py-1.5 rounded-lg font-medium transition-colors ${
              filters.sort === opt.value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
        <input
          type="search"
          className="w-full pl-8 pr-8 py-2 text-sm rounded-xl border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="Beiträge suchen…"
          value={searchInput}
          onChange={e => onSearchInput(e.target.value)}
          aria-label="Beiträge suchen"
        />
        {searchInput && (
          <button
            onClick={() => onSearchInput("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Suche leeren"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Specialty + Topic selects */}
      <div className="flex gap-2">
        <select
          value={filters.specialty}
          onChange={e => setFilter("specialty", e.target.value)}
          className="flex-1 text-xs rounded-xl border bg-background px-2.5 py-2 focus:outline-none focus:ring-1 focus:ring-primary text-muted-foreground cursor-pointer"
          aria-label="Fachgebiet filtern"
        >
          <option value="">Alle Fachgebiete</option>
          {SPECIALTY_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={filters.topic}
          onChange={e => setFilter("topic", e.target.value)}
          className="flex-1 text-xs rounded-xl border bg-background px-2.5 py-2 focus:outline-none focus:ring-1 focus:ring-primary text-muted-foreground cursor-pointer"
          aria-label="Thema filtern"
        >
          <option value="">Alle Themen</option>
          {TOPIC_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Active filter chips */}
      {hasActiveFilters && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {filters.specialty && (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">
              {SPECIALTY_LABELS[filters.specialty]}
              <button
                onClick={() => setFilter("specialty", "")}
                className="hover:text-primary/60"
                aria-label="Fachgebiet-Filter entfernen"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.topic && (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">
              {TOPIC_LABELS[filters.topic]}
              <button
                onClick={() => setFilter("topic", "")}
                className="hover:text-primary/60"
                aria-label="Thema-Filter entfernen"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.search && (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">
              „{filters.search}"
              <button
                onClick={() => onSearchInput("")}
                className="hover:text-primary/60"
                aria-label="Suche-Filter entfernen"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          <button
            onClick={onClear}
            className="text-[11px] text-muted-foreground hover:text-foreground ml-auto transition-colors"
          >
            Alle zurücksetzen
          </button>
        </div>
      )}
    </div>
  );
});
