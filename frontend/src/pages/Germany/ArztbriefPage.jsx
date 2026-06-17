import { useState, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Upload, FileText, X, Loader2, Trash2, Image as ImageIcon, FileCheck2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { analyzeArztbrief } from "@/lib/api";

const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "webp"];
const IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"];

const STRUCTURE_CARDS = [
  { title: "Kopf & Patient", desc: "Absender, Empfaenger, Datum, Betreff, Patientendaten, Zeitraum" },
  { title: "Diagnosen", desc: "Haupt-/Nebendiagnosen, ICD, klare Priorisierung" },
  { title: "Anamnese", desc: "Beschwerden, Vorgeschichte, Risikofaktoren, Allergien" },
  { title: "Befunde", desc: "Status, Vitalwerte, Labor, Bildgebung, Funktionstests" },
  { title: "Verlauf / Epikrise", desc: "Klinischer Verlauf, Interpretation, Komplikationen" },
  { title: "Therapie", desc: "Massnahmen, OP/Intervention, Medikationsaenderungen" },
  { title: "Medikation", desc: "Wirkstoff, Dosis, Schema, Dauer, Hinweise" },
  { title: "Procedere", desc: "Nachsorge, Kontrollen, Warnzeichen, Wiedervorstellung" },
];

function fileExtension(name = "") {
  return name.includes(".") ? name.split(".").pop().toLowerCase() : "";
}

function formatFileSize(size = 0) {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${Math.round(size / 1024)} KB`;
  return `${size} B`;
}

export default function ArztbriefPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [resultMeta, setResultMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const selectedExt = fileExtension(file?.name);
  const selectedType = selectedExt === "pdf" ? "PDF" : file ? "Bild/Scan" : null;

  const reset = () => {
    setFile(null);
    setPreview(null);
    setFeedback(null);
    setResultMeta(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleFile = useCallback((nextFile) => {
    setError(null);
    setFeedback(null);
    setResultMeta(null);
    setPreview(null);

    if (!nextFile) return;
    const ext = fileExtension(nextFile.name);
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError("Bitte PDF, JPG, PNG oder WebP hochladen.");
      return;
    }
    if (ext === "pdf" && nextFile.size > 20 * 1024 * 1024) {
      setError("PDF zu gross (max 20MB).");
      return;
    }
    if (IMAGE_EXTENSIONS.includes(ext) && nextFile.size > 10 * 1024 * 1024) {
      setError("Bild zu gross (max 10MB).");
      return;
    }

    setFile(nextFile);
    if (IMAGE_EXTENSIONS.includes(ext)) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(nextFile);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) handleFile(droppedFile);
  }, [handleFile]);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeArztbrief(file);
      setFeedback(data.feedback);
      setResultMeta(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((d) => d.msg || String(d)).join("; ") : detail || "Fehler bei der Analyse");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link to="/de">
        <Button variant="ghost" size="sm" className="gap-1 mb-6">
          <ArrowLeft className="w-4 h-4" /> Zurueck
        </Button>
      </Link>

      <h1 className="text-3xl font-bold mb-2">Arztbrief Korrektur</h1>
      <p className="text-muted-foreground mb-8">
        Lade einen PDF-Arztbrief oder einen gut lesbaren Scan hoch und erhalte Feedback zu Struktur, Sprache und Vollstaendigkeit.
      </p>

      <div className="grid md:grid-cols-2 gap-6 mb-10">
        <div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="rounded-lg border border-border/60 bg-card px-4 py-3 flex items-center gap-3">
              <FileCheck2 className="w-5 h-5 text-primary" />
              <div>
                <p className="text-sm font-semibold">PDF</p>
                <p className="text-xs text-muted-foreground">Text-PDF bis 20MB</p>
              </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-card px-4 py-3 flex items-center gap-3">
              <ImageIcon className="w-5 h-5 text-primary" />
              <div>
                <p className="text-sm font-semibold">Bild / Scan</p>
                <p className="text-xs text-muted-foreground">JPG, PNG, WebP bis 10MB</p>
              </div>
            </div>
          </div>

          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => inputRef.current?.click()}
            className={`relative rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : file
                  ? "border-primary/40 bg-card/50"
                  : "border-border/60 hover:border-primary/40 hover:bg-card/30"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {file ? (
              <div className="relative">
                {preview ? (
                  <img src={preview} alt="Arztbrief Vorschau" className="max-h-[360px] mx-auto rounded-lg object-contain" />
                ) : (
                  <div className="min-h-[220px] flex items-center justify-center">
                    <div className="text-center">
                      <FileText className="w-14 h-14 text-primary mx-auto mb-3" />
                      <p className="text-sm font-semibold">PDF bereit zur Analyse</p>
                    </div>
                  </div>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); reset(); }}
                  className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center hover:bg-destructive/90"
                  aria-label="Datei entfernen"
                >
                  <X className="w-4 h-4" />
                </button>
                <p className="text-xs text-muted-foreground mt-2">
                  {selectedType} · {file.name} · {formatFileSize(file.size)}
                </p>
              </div>
            ) : (
              <div>
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-6 h-6 text-primary" />
                </div>
                <p className="text-sm font-medium mb-1">Arztbrief hier ablegen</p>
                <p className="text-xs text-muted-foreground">oder klicken zum Durchsuchen</p>
                <p className="text-xs text-muted-foreground mt-2">PDF, JPG, PNG, WebP</p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-3 text-sm text-destructive bg-destructive/10 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          <Button size="lg" className="w-full mt-4 gap-2" onClick={handleAnalyze} disabled={!file || loading}>
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

        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Feedback</h2>
            {resultMeta?.file_type && (
              <span className="text-xs text-muted-foreground">
                {resultMeta.file_type === "pdf" ? `${resultMeta.extracted_chars || 0} Zeichen extrahiert` : "Vision-Analyse"}
              </span>
            )}
          </div>
          {feedback ? (
            <div className="rounded-xl border border-border/60 bg-card p-5 min-h-[360px] whitespace-pre-wrap text-sm leading-relaxed">
              {feedback}
            </div>
          ) : loading ? (
            <div className="rounded-xl border border-border/60 bg-card/50 p-5 min-h-[360px] flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">KI analysiert Struktur, Inhalt und Sprache...</p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border/40 bg-card/30 p-5 min-h-[360px] flex items-center justify-center">
              <div className="text-center">
                <FileText className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">Laden Sie einen Arztbrief hoch,<br />um Feedback zu erhalten</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Aufbau eines Arztbriefes</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {STRUCTURE_CARDS.map((card) => (
            <div key={card.title} className="rounded-lg border border-border/60 bg-card p-4 min-h-[112px]">
              <h3 className="text-sm font-semibold mb-1">{card.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{card.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
