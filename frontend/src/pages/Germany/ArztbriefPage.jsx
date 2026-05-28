import { useState, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Upload, FileText, X, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { analyzeArztbrief } from "@/lib/api";

const STRUCTURE_CARDS = [
  { title: "Briefkopf", desc: "Absender, Datum, Betreff, Patientendaten" },
  { title: "Diagnosen", desc: "Haupt- und Nebendiagnosen kodiert (ICD)" },
  { title: "Anamnese", desc: "Jetzige Beschwerden, Vorgeschichte, Risikofaktoren" },
  { title: "Befunde", desc: "Klinische Untersuchung, Labor, Bildgebung" },
  { title: "Therapie", desc: "Medikamente, Interventionen, Operationen" },
  { title: "Procedere", desc: "Weiteres Vorgehen, Kontrollen, Überweisungen" },
  { title: "Medikamente", desc: "Dosierung, Änderungen, Neuverordnungen" },
  { title: "Grußformel", desc: "Mit freundlichen Grüßen, Unterschrift" },
];

export default function ArztbriefPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const reset = () => {
    setFile(null);
    setPreview(null);
    setFeedback(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleFile = useCallback((f) => {
    setError(null);
    if (!f) return;
    const ext = f.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setError("Nur JPG, PNG und WebP sind erlaubt");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("Datei zu groß (max 10MB)");
      return;
    }
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeArztbrief(file);
      setFeedback(data.feedback);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg || String(d)).join("; "));
      } else {
        setError(detail || "Fehler bei der Analyse");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link to="/de">
        <Button variant="ghost" size="sm" className="gap-1 mb-6">
          <ArrowLeft className="w-4 h-4" /> Zurück
        </Button>
      </Link>

      <h1 className="text-3xl font-bold mb-2">Arztbrief Korrektur</h1>
      <p className="text-muted-foreground mb-8">
        Lade einen Arztbrief hoch und erhalte KI-gestütztes Feedback zu Struktur, Sprache und Vollständigkeit
      </p>

      {/* Main 2-column grid */}
      <div className="grid md:grid-cols-2 gap-6 mb-10">
        {/* Left: Upload */}
        <div>
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => inputRef.current?.click()}
            className={`relative rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : preview
                  ? "border-primary/40 bg-card/50"
                  : "border-border/60 hover:border-primary/40 hover:bg-card/30"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {preview ? (
              <div className="relative">
                <img src={preview} alt="Arztbrief" className="max-h-[400px] mx-auto rounded-lg object-contain" />
                <button onClick={(e) => { e.stopPropagation(); reset(); }}
                  className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center hover:bg-destructive/90">
                  <X className="w-4 h-4" />
                </button>
                <p className="text-xs text-muted-foreground mt-2">{file?.name}</p>
              </div>
            ) : (
              <div>
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-6 h-6 text-primary" />
                </div>
                <p className="text-sm font-medium mb-1">Arztbrief hier ablegen</p>
                <p className="text-xs text-muted-foreground">oder klicken zum Durchsuchen</p>
                <p className="text-xs text-muted-foreground mt-2">JPG, PNG, WebP — max 10MB</p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-3 text-sm text-destructive bg-destructive/10 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          <Button
            size="lg"
            className="w-full mt-4 gap-2"
            onClick={handleAnalyze}
            disabled={!file || loading}
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> KI analysiert...</>
            ) : (
              <><FileText className="w-5 h-5" /> Arztbrief analysieren</>
            )}
          </Button>

          {feedback && (
            <Button variant="outline" size="sm" className="w-full mt-2 gap-2" onClick={reset}>
              <Trash2 className="w-4 h-4" /> Neue Analyse
            </Button>
          )}
        </div>

        {/* Right: Feedback */}
        <div>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Feedback</h2>
          {feedback ? (
            <div className="rounded-xl border border-border/60 bg-card p-5 min-h-[300px] whitespace-pre-wrap text-sm leading-relaxed">
              {feedback}
            </div>
          ) : loading ? (
            <div className="rounded-xl border border-border/60 bg-card/50 p-5 min-h-[300px] flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">KI analysiert den Arztbrief...</p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border/40 bg-card/30 p-5 min-h-[300px] flex items-center justify-center">
              <div className="text-center">
                <FileText className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">Laden Sie einen Arztbrief hoch,<br />um Feedback zu erhalten</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Structure guide */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Aufbau eines Arztbriefes</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {STRUCTURE_CARDS.map((card) => (
            <div key={card.title} className="rounded-xl border border-border/60 bg-card p-4">
              <h3 className="text-sm font-semibold mb-1">{card.title}</h3>
              <p className="text-xs text-muted-foreground">{card.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
