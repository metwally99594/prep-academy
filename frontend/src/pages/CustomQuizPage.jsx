import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  SlidersHorizontal,
  Play,
  Search,
  Heart,
  BookOpen,
  Tag,
  Clock,
  Loader2,
  Filter,
  RotateCcw,
  MapPin,
} from "lucide-react";

const SPECIALTIES = [
  { id: "internal", name: "Innere Medizin" },
  { id: "surgery", name: "Chirurgische Fächer" },
  { id: "pediatrics", name: "Kinder- und Jugendheilkunde" },
  { id: "neurology", name: "Neurologie" },
  { id: "dermatology", name: "Dermatologie und Venerologie" },
  { id: "obgyn", name: "Frauenheilkunde/Gynäkologie" },
  { id: "emergency", name: "Notfall- und Intensivmedizin" },
  { id: "ent", name: "Hals-Nasen-Ohrenheilkunde" },
  { id: "psychiatry", name: "Psychiatrie" },
  { id: "ophthalmology", name: "Augenheilkunde" },
];

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 2009 + 1 }, (_, i) => currentYear - i);

export default function CustomQuizPage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [selectedSpecs, setSelectedSpecs] = useState([]);
  const [examLocation, setExamLocation] = useState("");
  const [textSearch, setTextSearch] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [questionLimit, setQuestionLimit] = useState([50]);
  const [quizMode, setQuizMode] = useState("exam");
  const [matchCount, setMatchCount] = useState(null);
  const [counting, setCounting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [tags, setTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [specCounts, setSpecCounts] = useState({});

  const toggleSpec = (id) => {
    setSelectedSpecs((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  useEffect(() => {
    axios.get(`${API}/tags`).then(r => setTags(r.data)).catch(() => {});
    // Fetch specialty question counts
    axios.get(`${API}/specialties`).then(r => {
      const counts = {};
      r.data.forEach(s => { counts[s.id] = s.question_count || 0; });
      setSpecCounts(counts);
    }).catch(() => {});
  }, []);

  const buildPayload = useCallback(() => ({
    specialties: selectedSpecs,
    text_search: textSearch.trim() || null,
    year_from: yearFrom ? parseInt(yearFrom) : null,
    year_to: yearTo ? parseInt(yearTo) : null,
    exam_location: examLocation || null,
    favorites_only: favoritesOnly,
    tags: selectedTags.length > 0 ? selectedTags : null,
    limit: questionLimit[0],
    mode: quizMode,
  }), [selectedSpecs, textSearch, yearFrom, yearTo, examLocation, favoritesOnly, selectedTags, questionLimit, quizMode]);

  // Debounced count
  useEffect(() => {
    const timer = setTimeout(async () => {
      setCounting(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.post(`${API}/questions/custom-quiz/count`, buildPayload(), { headers });
        setMatchCount(res.data.count);
      } catch {
        setMatchCount(null);
      } finally {
        setCounting(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [selectedSpecs, textSearch, yearFrom, yearTo, favoritesOnly, examLocation, token, buildPayload]);

  const startQuiz = async () => {
    setStarting(true);
    try {
      const payload = buildPayload();
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/questions/custom-quiz/count`, payload, { headers });
      if (!res.data || res.data.count === 0) {
        toast.error("Keine Fragen gefunden. Bitte ändern Sie Ihre Filter.");
        setStarting(false);
        return;
      }
      // Pass filter payload via route state - no sessionStorage needed
      const filterParams = new URLSearchParams();
      filterParams.set("mode", quizMode);
      if (payload.specialties?.length) filterParams.set("specs", payload.specialties.join(","));
      if (payload.text_search) filterParams.set("q", payload.text_search);
      if (payload.year_from) filterParams.set("yf", payload.year_from);
      if (payload.year_to) filterParams.set("yt", payload.year_to);
      if (payload.exam_location) filterParams.set("loc", payload.exam_location);
      if (payload.favorites_only) filterParams.set("fav", "1");
      if (payload.tags?.length) filterParams.set("tags", payload.tags.join(","));
      filterParams.set("limit", payload.limit);

      navigate(`/quiz/custom?${filterParams.toString()}`);
    } catch (err) {
      console.error("Failed to start quiz:", err);
      toast.error("Fehler beim Starten des Quiz. Bitte versuchen Sie es erneut.");
      setStarting(false);
    }
  };

  const resetFilters = () => {
    setSelectedSpecs([]);
    setExamLocation("");
    setTextSearch("");
    setYearFrom("");
    setYearTo("");
    setFavoritesOnly(false);
    setQuestionLimit([50]);
    setSelectedTags([]);
    setQuizMode("exam");
  };

  const hasAnyFilter = selectedSpecs.length > 0 || textSearch || yearFrom || yearTo || favoritesOnly || examLocation;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" data-testid="custom-quiz-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-primary/10">
            <SlidersHorizontal className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="custom-quiz-title">
              Eigene Auswahl
            </h1>
            <p className="text-sm text-muted-foreground">
              Erstellen Sie Ihr eigenes Quiz mit benutzerdefinierten Filtern
            </p>
          </div>
        </div>
        {hasAnyFilter && (
          <Button variant="ghost" size="sm" onClick={resetFilters} className="gap-2 text-muted-foreground" data-testid="reset-filters-btn">
            <RotateCcw className="w-4 h-4" />
            Zurücksetzen
          </Button>
        )}
      </div>

      <div className="space-y-6">
        {/* Fachgebiete */}
        <div className="glass-card rounded-2xl p-6" data-testid="specialty-filter-section">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Filter className="w-4 h-4 text-primary" />
            Fachgebiete
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SPECIALTIES.map((spec) => {
              const checked = selectedSpecs.includes(spec.id);
              const count = specCounts[spec.id] || 0;
              return (
                <div
                  key={spec.id}
                  onClick={() => toggleSpec(spec.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleSpec(spec.id); }}
                  data-testid={`spec-checkbox-${spec.id}`}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-[color,background-color,border-color] text-left cursor-pointer select-none ${
                    checked
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border hover:border-primary/30 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Checkbox checked={checked} className="pointer-events-none" />
                  <span className="text-sm font-medium flex-1">{spec.name}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${checked ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Prüfungsort (City) */}
        <div className="glass-card rounded-2xl p-6" data-testid="city-filter-section">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            Prüfungsort
          </h2>
          <div className="flex flex-wrap gap-3">
            {[
              { value: "", label: "Alle Orte" },
              { value: "vienna", label: "Wien" },
              { value: "innsbruck", label: "Innsbruck" },
              { value: "andere", label: "Andere Stadt" },
            ].map((city) => (
              <button
                key={city.value}
                onClick={() => setExamLocation(city.value)}
                data-testid={`city-filter-${city.value || "all"}`}
                className={`px-4 py-2.5 rounded-xl border-2 text-sm font-medium transition-[color,background-color,border-color] ${
                  examLocation === city.value
                    ? "border-primary bg-primary/5 text-foreground"
                    : "border-border hover:border-primary/30 text-muted-foreground hover:text-foreground"
                }`}
              >
                {city.label}
              </button>
            ))}
          </div>
        </div>

        {/* Prüfungsdatum */}
        <div className="glass-card rounded-2xl p-6" data-testid="date-filter-section">
          <h2 className="font-semibold mb-4">Prüfungsdatum (Zeitraum)</h2>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground mb-1 block">Von</Label>
              <select
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
                className="w-full h-10 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                data-testid="year-from-select"
              >
                <option value="">-- Alle --</option>
                {YEARS.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <span className="text-muted-foreground mt-5">—</span>
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground mb-1 block">Bis</Label>
              <select
                value={yearTo}
                onChange={(e) => setYearTo(e.target.value)}
                className="w-full h-10 rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                data-testid="year-to-select"
              >
                <option value="">-- Alle --</option>
                {YEARS.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Nur gemerkte Fragen */}
        <div className="glass-card rounded-2xl p-6" data-testid="extra-filters-section">
          <div className="flex flex-col sm:flex-row gap-3">
            <div
              onClick={() => setFavoritesOnly(!favoritesOnly)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setFavoritesOnly(!favoritesOnly); }}
              data-testid="favorites-only-btn"
              className={`flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all cursor-pointer select-none ${
                favoritesOnly
                  ? "border-red-400 bg-red-50 text-red-600"
                  : "border-border hover:border-red-300 text-muted-foreground"
              }`}
            >
              <Checkbox checked={favoritesOnly} className="pointer-events-none" />
              <Heart className={`w-4 h-4 ${favoritesOnly ? "text-red-500" : ""}`} />
              <span className="text-sm font-medium">Nur gemerkte Fragen</span>
            </div>
          </div>
        </div>

        {/* Tags Filter */}
        {tags.length > 0 && (
          <div className="glass-card rounded-2xl p-6" data-testid="tags-filter-section">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <Tag className="w-4 h-4 text-primary" />
              Tags filtern
            </h2>
            <div className="flex flex-wrap gap-2">
              {tags.map(tag => (
                <button key={tag.id} onClick={() => setSelectedTags(prev => prev.includes(tag.id) ? prev.filter(t => t !== tag.id) : [...prev, tag.id])}
                  data-testid={`tag-filter-${tag.id}`}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-[color,background-color,border-color,box-shadow] ${
                    selectedTags.includes(tag.id) ? "border-current ring-1 ring-current" : "border-border text-muted-foreground hover:border-current"
                  }`}
                  style={{ color: selectedTags.includes(tag.id) ? tag.color : undefined }}>
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: tag.color }} />
                  {tag.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Text search */}
        <div className="glass-card rounded-2xl p-6" data-testid="text-search-section">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Search className="w-4 h-4 text-primary" />
            Im Text suchen
          </h2>
          <Input
            value={textSearch}
            onChange={(e) => setTextSearch(e.target.value)}
            placeholder="Suchbegriff eingeben..."
            data-testid="text-search-input"
          />
        </div>

        {/* Question limit slider */}
        <div className="glass-card rounded-2xl p-6" data-testid="limit-slider-section">
          <h2 className="font-semibold mb-4">
            Anzahl Fragen:{" "}
            <span className="text-primary">{questionLimit[0]}</span>
          </h2>
          <Slider
            value={questionLimit}
            onValueChange={setQuestionLimit}
            min={5}
            max={200}
            step={5}
            className="w-full"
            data-testid="question-limit-slider"
          />
          <div className="flex justify-between mt-2 text-xs text-muted-foreground">
            <span>5</span>
            <span>200</span>
          </div>
        </div>

        {/* Mode */}
        <div className="glass-card rounded-2xl p-6" data-testid="mode-section">
          <h2 className="font-semibold mb-4">Modus wählen</h2>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setQuizMode("study")}
              data-testid="custom-study-mode-btn"
              className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-[color,background-color,border-color] ${
                quizMode === "study"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/30"
              }`}
            >
              <BookOpen className={`w-5 h-5 ${quizMode === "study" ? "text-primary" : "text-muted-foreground"}`} />
              <div className="text-left">
                <div className="font-semibold text-sm">Study</div>
                <div className="text-xs text-muted-foreground">Ohne Zeitdruck</div>
              </div>
            </button>
            <button
              onClick={() => setQuizMode("exam")}
              data-testid="custom-exam-mode-btn"
              className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-[color,background-color,border-color] ${
                quizMode === "exam"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/30"
              }`}
            >
              <Clock className={`w-5 h-5 ${quizMode === "exam" ? "text-primary" : "text-muted-foreground"}`} />
              <div className="text-left">
                <div className="font-semibold text-sm">Exam</div>
                <div className="text-xs text-muted-foreground">60s pro Frage</div>
              </div>
            </button>
          </div>
        </div>

        {/* Matching count + Start button */}
        <div className="glass-card rounded-2xl p-6 text-center" data-testid="start-section">
          <div className="mb-4">
            {counting ? (
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Fragen werden gezählt...</span>
              </div>
            ) : matchCount !== null ? (
              <p className="text-sm text-muted-foreground">
                <span className="text-2xl font-bold text-primary">{matchCount}</span>{" "}
                Fragen entsprechen Ihren Filtern
              </p>
            ) : null}
          </div>
          <Button
            onClick={startQuiz}
            size="lg"
            className="gap-2 px-8"
            disabled={starting || matchCount === 0}
            data-testid="start-custom-quiz-btn"
          >
            {starting ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            Quiz starten ({Math.min(questionLimit[0], matchCount || 0)} Fragen)
          </Button>
        </div>
      </div>
    </div>
  );
}
