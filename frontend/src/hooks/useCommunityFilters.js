import { useState, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";

export function useCommunityFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(() => searchParams.get("search") || "");
  const debounceRef = useRef(null);

  const filters = {
    sort: searchParams.get("sort") || "recent",
    specialty: searchParams.get("specialty") || "",
    topic: searchParams.get("topic") || "",
    type: searchParams.get("type") || "",
    search: searchParams.get("search") || "",
  };

  const setFilter = useCallback((key, value) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const handleSearchInput = useCallback((value) => {
    setSearchInput(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchParams(prev => {
        const next = new URLSearchParams(prev);
        if (value.trim()) next.set("search", value.trim());
        else next.delete("search");
        return next;
      }, { replace: true });
    }, 350);
  }, [setSearchParams]);

  const clearFilters = useCallback(() => {
    clearTimeout(debounceRef.current);
    setSearchParams({}, { replace: true });
    setSearchInput("");
  }, [setSearchParams]);

  const hasActiveFilters = !!(filters.specialty || filters.topic || filters.type || filters.search);

  return { filters, setFilter, searchInput, handleSearchInput, clearFilters, hasActiveFilters };
}
