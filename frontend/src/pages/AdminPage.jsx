import React, { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import QuestionTypeFields from "@/components/QuestionTypeFields";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import AdminReportsTab from "@/components/AdminReportsTab";
import AdminTagsTab from "@/components/AdminTagsTab";
import AdminPodcastTab from "@/components/AdminPodcastTab";
import AdminRagTab from "@/components/AdminRagTab";
import AdminAccessRequestsTab from "@/components/AdminAccessRequestsTab";
import { ADVANCED_FEATURES_ENABLED } from "@/lib/features";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { 
  Settings,
  ArrowLeft,
  Plus,
  Pencil,
  Trash2,
  Upload,
  X,
  Users,
  FileQuestion,
  Heart,
  Loader2,
  Shield,
  Mail,
  Calendar,
  Trophy,
  Download,
  Wifi,
  WifiOff,
  BarChart3,
  BookOpen,
  Copy,
  Activity,
  Merge,
  Sparkles,
  Flag,
  Tag,
  Headphones,
  ShieldCheck,
  Play,
  Search,
  FileText,
  GraduationCap,
  Database,
  CheckCircle,
  XCircle,
} from "lucide-react";

const SPECIALTIES = [
  { id: "surgery", name: "Chirurgie" },
  { id: "internal", name: "Innere Medizin" },
  { id: "pediatrics", name: "Pädiatrie" },
  { id: "emergency", name: "Notfallmedizin" },
  { id: "ophthalmology", name: "Ophthalmologie" },
  { id: "dermatology", name: "Dermatologie" },
  { id: "ent", name: "HNO" },
  { id: "obgyn", name: "Gynäkologie" },
  { id: "neurology", name: "Neurologie" },
  { id: "psychiatry", name: "Psychiatrie" },
  { id: "pharma", name: "Pharmakologie" },
  { id: "special", name: "Special" },
];

const CITIES = [
  { id: "vienna", name: "Wien" },
  { id: "innsbruck", name: "Innsbruck" },
  { id: "hamburg", name: "Hamburg" },
  { id: "berlin", name: "Berlin" },
  { id: "munich", name: "Muenchen" },
  { id: "zurich", name: "Zuerich" },
  { id: "basel", name: "Basel" },
  { id: "andere", name: "Andere Stadt" },
];

const COUNTRY_BADGES = {
  austria: { label: "AT", className: "bg-red-500/10 text-red-500 border-red-500/20" },
  at: { label: "AT", className: "bg-red-500/10 text-red-500 border-red-500/20" },
  germany: { label: "DE", className: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20" },
  de: { label: "DE", className: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20" },
  switzerland: { label: "CH", className: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  ch: { label: "CH", className: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
};

const getCountryBadge = (country) => {
  const key = String(country || "").trim().toLowerCase();
  return COUNTRY_BADGES[key] || (key ? { label: key.toUpperCase(), className: "bg-gray-500/10 text-gray-500 border-gray-500/20" } : null);
};

const getCityLabel = (city) => CITIES.find(c => c.id === city)?.name || city || "—";

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 2009 + 6 }, (_, i) => 2009 + i);

const emptyQuestion = {
  specialty_id: "",
  year: new Date().getFullYear(),
  exam_location: "vienna",
  country: "",
  status: "published",
  question_text: "",
  question_text_de: "",
  question_type: "single_choice",
  choices: [
    { id: "1", text: "", text_de: "", is_correct: false },
    { id: "2", text: "", text_de: "", is_correct: false },
    { id: "3", text: "", text_de: "", is_correct: false },
    { id: "4", text: "", text_de: "", is_correct: false },
    { id: "5", text: "", text_de: "", is_correct: false },
  ],
  explanation: "",
  explanation_de: "",
  image_base64: "",
  tags: [],
  drag_drop_items: [],
  drag_drop_categories: [],
  blank_text: "",
  blank_answers: [],
  blanks: [],
};

function ImportQuestionsTab({ token, onImportComplete }) {
  const [mode, setMode] = useState("file");
  const [file, setFile] = useState(null);
  const [pasteJson, setPasteJson] = useState("");
  const [parsedQuestions, setParsedQuestions] = useState(null);
  const [preview, setPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [xlsxMode, setXlsxMode] = useState(false);
  const [xlsxResult, setXlsxResult] = useState(null);
  const [xlsxImporting, setXlsxImporting] = useState(false);

  const normalizeImportMetadata = (q) => {
    const subject = q.subject || {};
    const nestedSpecialty = subject.specialty || subject.subspecialty || subject.branch || subject.topic || {};
    const plainSpecialty = typeof q.specialty === "string" ? q.specialty : "";
    const subjectId = q.subject_id || subject.id || q.fach || plainSpecialty || q.specialty_id || "";
    const subspecialtyId = q.subspecialty_id || q.branch_id || q.topic_id || nestedSpecialty.id || "";
    const city = q.city || q.exam_location || q.stadt || q.ort || q.location || null;

    return {
      specialty_id: q.specialty_id || subjectId,
      subject: q.subject || null,
      subject_id: subjectId,
      subject_name_de: q.subject_name_de || subject.name_de || subject.name || null,
      subspecialty_id: subspecialtyId || null,
      subspecialty_name_de: q.subspecialty_name_de || q.branch_name_de || nestedSpecialty.name_de || nestedSpecialty.name || null,
      city,
      exam_location: city,
      country: q.country || q.land || null,
      tags: q.tags || [],
    };
  };

  const parseQuestions = (data) => {
    if (!Array.isArray(data)) {
      toast.error("JSON muss ein Array von Fragen sein");
      return null;
    }
    const items = data.map(q => {
      let choices = q.choices_de || q.choices || [];
      if (choices.length > 0 && typeof choices[0] === 'string') {
        choices = choices.map((text, ci) => ({
          id: String.fromCharCode(97 + ci),
          text,
          is_correct: ci === 0,
        }));
      }
      const metadata = normalizeImportMetadata(q);
      return {
        ...metadata,
        question_text_de: q.question_text_de || q.question_text || q.question || q.frage || q.text || "",
        question_type: q.question_type || "mcq",
        choices_de: choices,
        explanation_de: q.explanation_de || q.explanation || null,
        year: q.year || null,
        drag_drop_items: q.drag_drop_items || q.interactive_data?.items || [],
        drag_drop_categories: q.drag_drop_categories || q.interactive_data?.categories || [],
        blanks: q.blanks || q.interactive_data?.blanks || [],
      };
    });
    const specs = {};
    items.forEach(q => {
      const sid = q.specialty_id || "unknown";
      specs[sid] = (specs[sid] || 0) + 1;
    });
    setParsedQuestions(items);
    setPreview({ total: items.length, specialties: specs, sample: items.slice(0, 3) });
    setResult(null);
    setValidationResult(null);
    return items;
  };

  const handleFileSelect = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (!f.name.endsWith('.json')) {
      toast.error("Nur JSON-Dateien sind erlaubt");
      return;
    }
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        parseQuestions(data);
      } catch {
        toast.error("Ungültige JSON-Datei");
        setFile(null);
      }
    };
    reader.readAsText(f);
  };

  const handleXlsxSelect = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (!f.name.endsWith('.xlsx') && !f.name.endsWith('.xls')) {
      toast.error("Nur Excel-Dateien (.xlsx/.xls) sind erlaubt");
      return;
    }
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        parseQuestions(data);
      } catch {
        toast.error("Ungültige Excel-Datei");
        setFile(null);
      }
    };
    reader.readAsText(f);
  };

  const handlePaste = () => {
    if (!pasteJson.trim()) { toast.error("Bitte JSON einfügen"); return; }
    try {
      const data = JSON.parse(pasteJson);
      parseQuestions(data);
    } catch {
      toast.error("Ungültiges JSON");
    }
  };

  const handleXlsxImport = async () => {
    if (!file) { toast.error("Bitte eine Excel-Datei auswählen"); return; }
    setXlsxImporting(true);
    setXlsxResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post(
        `${API}/admin/import-questions/xlsx`,
        formData,
        {
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" },
          timeout: 120000,
        }
      );
      setXlsxResult(res.data);
      toast.success(`${res.data.imported} Fragen aus Excel importiert!`);
      if (onImportComplete) onImportComplete();
    } catch (err) {
      toast.error(_safeErr(err, "XLSX-Import fehlgeschlagen"));
    } finally {
      setXlsxImporting(false);
    }
  };

  const handleValidate = async () => {
    if (!parsedQuestions || parsedQuestions.length === 0) { toast.error("Keine Fragen zum Validieren"); return; }
    setValidating(true);
    try {
      const res = await axios.post(
        `${API}/admin/questions/validate`,
        { questions: parsedQuestions, filename: file?.name || "paste" },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 30000 }
      );
      setValidationResult(res.data);
      if (res.data.valid) {
        toast.success(`${res.data.valid_count} Fragen gültig ✓`);
      } else {
        toast.error(`${res.data.error_count} Fragen haben Fehler`);
      }
    } catch (err) {
      toast.error(_safeErr(err, "Validierung fehlgeschlagen"));
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!parsedQuestions || parsedQuestions.length === 0) { toast.error("Keine Fragen zum Importieren"); return; }
    setImporting(true);
    try {
      const res = await axios.post(
        `${API}/admin/questions/import`,
        { questions: parsedQuestions, filename: file?.name || "paste" },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 }
      );
      setResult(res.data);
      toast.success(`${res.data.imported} Fragen importiert!`);
      if (onImportComplete) onImportComplete();
    } catch (err) {
      toast.error(_safeErr(err, "Import fehlgeschlagen"));
    } finally {
      setImporting(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPasteJson("");
    setParsedQuestions(null);
    setPreview(null);
    setResult(null);
    setValidationResult(null);
    setXlsxResult(null);
  };

  return (
    <div className="glass-card rounded-2xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Fragen importieren</h2>
          <p className="text-sm text-muted-foreground">
            JSON importieren, validieren und direkt in MongoDB speichern
          </p>
        </div>
      </div>

      {/* Mode switcher */}
      {!parsedQuestions && !xlsxResult && (
        <div className="flex gap-2 flex-wrap">
          <Button variant={!xlsxMode && mode === "file" ? "default" : "outline"} onClick={() => { setXlsxMode(false); setMode("file"); }} className="gap-2">
            <Upload className="w-4 h-4" /> JSON
          </Button>
          <Button variant={xlsxMode ? "default" : "outline"} onClick={() => { setXlsxMode(true); setMode("file"); }} className="gap-2">
            <Upload className="w-4 h-4" /> Excel (XLSX)
          </Button>
          <Button variant={!xlsxMode && mode === "paste" ? "default" : "outline"} onClick={() => { setXlsxMode(false); setMode("paste"); }} className="gap-2">
            <Copy className="w-4 h-4" /> JSON einfügen
          </Button>
        </div>
      )}

      {/* JSON File upload */}
      {!xlsxMode && mode === "file" && !parsedQuestions && (
        <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-primary/30 rounded-2xl cursor-pointer hover:border-primary/60 hover:bg-primary/5 transition-all">
          <Upload className="w-10 h-10 text-primary/50 mb-3" />
          <span className="text-sm font-medium text-primary">JSON-Datei auswählen</span>
          <span className="text-xs text-muted-foreground mt-1">oder hierher ziehen</span>
          <input type="file" accept=".json" className="hidden" onChange={handleFileSelect} />
        </label>
      )}

      {/* XLSX File upload */}
      {xlsxMode && !parsedQuestions && !xlsxResult && (
        <div className="space-y-3">
          <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-emerald-500/30 rounded-2xl cursor-pointer hover:border-emerald-500/60 hover:bg-emerald-500/5 transition-all">
            <Upload className="w-10 h-10 text-emerald-500/50 mb-3" />
            <span className="text-sm font-medium text-emerald-500">Excel-Datei auswählen (.xlsx)</span>
            <span className="text-xs text-muted-foreground mt-1">Spalten: Fragetext, Fachgebiet, Antwort A-E, Richtige Antwort, Erklärung, Jahr, Ort, Land</span>
            <input type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => {
              const f = e.target.files[0];
              if (!f) return;
              if (!f.name.endsWith('.xlsx') && !f.name.endsWith('.xls')) {
                toast.error("Nur Excel-Dateien (.xlsx/.xls) sind erlaubt");
                return;
              }
              setFile(f);
              setXlsxResult(null);
            }} />
          </label>
          {file && xlsxMode && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <div className="flex items-center gap-2 text-sm">
                <Upload className="w-4 h-4 text-emerald-500" />
                <span className="font-medium">{file.name}</span>
                <span className="text-muted-foreground">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => { setFile(null); setXlsxResult(null); }} variant="ghost" size="sm">
                  <X className="w-4 h-4" />
                </Button>
                <Button onClick={handleXlsxImport} disabled={xlsxImporting} className="gap-2 bg-emerald-600 hover:bg-emerald-500">
                  {xlsxImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {xlsxImporting ? "Importiere..." : "Excel importieren"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* XLSX result */}
      {xlsxResult && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <h3 className="font-medium text-emerald-600 mb-2">Excel-Import abgeschlossen!</h3>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-emerald-600">{xlsxResult.imported}</div>
              <div className="text-xs text-muted-foreground">Importiert</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-amber-500">{xlsxResult.skipped}</div>
              <div className="text-xs text-muted-foreground">Übersprungen</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-primary">{xlsxResult.total_in_db}</div>
              <div className="text-xs text-muted-foreground">Gesamt in DB</div>
            </div>
          </div>
          {xlsxResult.errors?.length > 0 && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-3 max-h-32 overflow-y-auto">
              {xlsxResult.errors.map((e, i) => <div key={i} className="text-xs text-red-600 py-0.5">{e}</div>)}
            </div>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setFile(null); setXlsxResult(null); }} className="gap-2">
              <Upload className="w-4 h-4" /> Weiteres Excel importieren
            </Button>
          </div>
        </div>
      )}

      {/* Paste JSON */}
      {!xlsxMode && mode === "paste" && !parsedQuestions && (
        <div className="space-y-3">
          <Textarea
            placeholder='[{&quot;country&quot;:&quot;germany&quot;,&quot;city&quot;:&quot;hamburg&quot;,&quot;year&quot;:2020,&quot;subject&quot;:{&quot;id&quot;:&quot;internal&quot;,&quot;specialty&quot;:{&quot;id&quot;:&quot;cardiology&quot;}},&quot;question_text_de&quot;:&quot;...&quot;}]'
            className="min-h-[200px] font-mono text-sm"
            value={pasteJson}
            onChange={(e) => setPasteJson(e.target.value)}
          />
          <Button onClick={handlePaste} className="gap-2 w-full">
            <Copy className="w-4 h-4" /> Fragen parsen
          </Button>
        </div>
      )}

      {/* Preview */}
      {preview && !result && (
        <div className="p-4 rounded-xl bg-muted/50 border border-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">{preview.total} Fragen gefunden</h3>
            <Button variant="ghost" size="sm" onClick={handleClear}><X className="w-4 h-4" /></Button>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries(preview.specialties).map(([id, count]) => (
              <span key={id} className="px-2 py-1 rounded-full bg-primary/10 text-xs font-medium">{id}: {count}</span>
            ))}
          </div>
          {preview.sample.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Beispiel:</p>
              {preview.sample.map((q, i) => (
                <div key={i} className="text-xs p-2 rounded-lg bg-background border border-border truncate">
                  {q.question_text_de || '(Kein Text)'}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Validation errors */}
      {validationResult && !validationResult.valid && !result && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <h3 className="font-medium text-red-600 mb-2">Validierungsfehler ({validationResult.error_count})</h3>
          <div className="max-h-48 overflow-y-auto space-y-1 text-sm">
            {validationResult.errors.slice(0, 30).map((e, i) => (
              <div key={i} className="p-2 rounded bg-red-500/5 text-red-700 text-xs">
                Frage #{e.index + 1} — <strong>{e.field}</strong>: {e.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation passed */}
      {validationResult && validationResult.valid && !result && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <h3 className="font-medium text-emerald-600 mb-1">✓ {validationResult.valid_count} Fragen gültig</h3>
          <p className="text-xs text-muted-foreground">Keine Validierungsfehler</p>
        </div>
      )}

      {/* Import result */}
      {result && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <h3 className="font-medium text-emerald-600 mb-2">Import abgeschlossen!</h3>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-emerald-600">{result.imported}</div>
              <div className="text-xs text-muted-foreground">Importiert</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-amber-500">{result.skipped_duplicates}</div>
              <div className="text-xs text-muted-foreground">Duplikate</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-background">
              <div className="text-xl font-bold text-red-500">{result.validation_errors}</div>
              <div className="text-xs text-muted-foreground">Fehler</div>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">Dauer: {result.duration_ms}ms</p>
        </div>
      )}

      {/* Actions */}
      {preview && !result && (
        <div className="flex gap-3">
          <Button onClick={handleValidate} disabled={validating} variant="outline" className="flex-1 gap-2">
            {validating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Validieren
          </Button>
          <Button onClick={handleImport} disabled={importing} className="flex-1 gap-2">
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {importing ? `Importiere...` : `${preview.total} Fragen importieren`}
          </Button>
        </div>
      )}
      {result && (
        <Button variant="outline" onClick={handleClear} className="w-full gap-2">
          <Upload className="w-4 h-4" /> Weitere Fragen importieren
        </Button>
      )}

      {/* JSON Format Reference */}
      <div className="border-t border-border pt-4 mt-4">
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground select-none">
            JSON-Format anzeigen
          </summary>
          <div className="mt-3 space-y-4 text-xs">
            <div>
              <p className="font-medium text-primary mb-1">Empfohlen: Land / Stadt / Fach / Teilgebiet</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">{`[
  {
    "country": "germany",
    "city": "hamburg",
    "year": 2020,
    "subject": {
      "id": "internal",
      "name_de": "Innere Medizin",
      "specialty": {
        "id": "cardiology",
        "name_de": "Kardiologie"
      }
    },
    "question_type": "single_choice",
    "question_text_de": "Welche Aussage zur Herzinsuffizienz trifft zu?",
    "choices_de": [
      {"id": "a", "text": "Antwort A", "is_correct": false},
      {"id": "b", "text": "Antwort B", "is_correct": true}
    ],
    "correct_answers": ["b"],
    "explanation_de": "Begruendung..."
  }
]`}</pre>
              <p className="mt-2 text-muted-foreground">
                Legacy bleibt erlaubt: <code>specialty_id</code>, <code>exam_location</code> und <code>country</code> funktionieren weiterhin.
              </p>
            </div>
            <div>
              <p className="font-medium text-primary mb-1">MCQ / Multi-Select</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">{`[
  {
    "specialty_id": "surgery",
    "question_text_de": "Was ist...?",
    "question_type": "mcq",
    "choices_de": [
      {"id": "a", "text": "Antwort A", "is_correct": false},
      {"id": "b", "text": "Antwort B", "is_correct": true}
    ],
    "correct_answers": ["b"],
    "year": 2024,
    "exam_location": "vienna",
    "country": "austria",
    "explanation_de": "Erklärung..."
  }
]`}</pre>
            </div>
            <div>
              <p className="font-medium text-primary mb-1">Drag & Drop / Kategorisierung</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">{`{
  "specialty_id": "internal",
  "question_type": "drag_drop",
  "question_text_de": "Ordnen Sie zu.",
  "interactive_data": {
    "items": [
      {"id": "i1", "text_de": "Brustschmerz"},
      {"id": "i2", "text_de": "Schwindel"}
    ],
    "categories": [
      {"id": "cat_a", "label_de": "Kardial"},
      {"id": "cat_b", "label_de": "Harmlos"}
    ],
    "correct_mapping": {"i1": "cat_a", "i2": "cat_b"}
  },
  "year": 2025,
  "exam_location": "vienna",
  "country": "austria"
}`}</pre>
            </div>
            <div>
              <p className="font-medium text-primary mb-1">Lückentext</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">{`{
  "specialty_id": "internal",
  "question_type": "fill_blank",
  "question_text_de": "Beschriften Sie.",
  "interactive_data": {
    "prompt_de": "Tragen Sie den korrekten Begriff ein:",
    "blanks": [
      {
        "id": "b1",
        "label": "1",
        "hint_de": "Oben rechts",
        "correct_answers": ["Rechter Vorhof", "RA"],
        "case_sensitive": false
      }
    ]
  },
  "year": 2025,
  "exam_location": "vienna",
  "country": "austria"
}`}</pre>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium mb-1">Erlaubte Werte</p>
              <p>Fragetypen: <code className="text-primary">mcq</code> <code className="text-primary">multi_select</code> <code className="text-primary">drag_drop</code> <code className="text-primary">categorize</code> <code className="text-primary">fill_blank</code></p>
              <p className="mt-1">Specialty IDs: <code className="text-primary">surgery</code> <code className="text-primary">internal</code> <code className="text-primary">ophthalmology</code> <code className="text-primary">dermatology</code> <code className="text-primary">ent</code> <code className="text-primary">obgyn</code> <code className="text-primary">neurology</code> <code className="text-primary">emergency</code> <code className="text-primary">pediatrics</code> <code className="text-primary">psychiatry</code></p>
              <p className="mt-1">Teilgebiete: <code className="text-primary">cardiology</code> <code className="text-primary">gastroenterology</code> <code className="text-primary">pneumology</code> <code className="text-primary">nephrology</code> <code className="text-primary">endocrinology</code></p>
              <p className="mt-1">Orte: <code className="text-primary">vienna</code> <code className="text-primary">innsbruck</code> <code className="text-primary">hamburg</code> <code className="text-primary">berlin</code> <code className="text-primary">munich</code> <code className="text-primary">zurich</code> <code className="text-primary">basel</code> <code className="text-primary">andere</code></p>
              <p className="mt-1">Länder: <code className="text-primary">austria</code> <code className="text-primary">germany</code> <code className="text-primary">switzerland</code></p>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

function MasterclassAdminTab({ token }) {
  const [seeding, setSeeding] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);

  const handleSeed = async () => {
    setSeeding(true);
    setResult(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/masterclass/seed`, {}, { headers });
      setResult({ ok: true, message: `✅ ${res.data.created} Levels erfolgreich erstellt (insgesamt ${res.data.total_levels})` });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg || String(d)).join("; ") : (detail || "Fehler beim Seed");
      setResult({ ok: false, message: `❌ ${msg}` });
    } finally {
      setSeeding(false);
    }
  };

  const handleGenerateContent = async () => {
    setGenerating(true);
    setResult(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/masterclass/generate-content`, {}, { headers });
      setResult({ ok: true, message: `✅ ${res.data.updated} Levels mit Inhalt befüllt (${res.data.failed} Kapitel fehlgeschlagen)` });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg || String(d)).join("; ") : (detail || "Fehler bei Generierung");
      setResult({ ok: false, message: `❌ ${msg}` });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Masterclass</h2>
      <p className="text-muted-foreground">
        Erstellt 90 Lerneinheiten in der Datenbank und generiert echte Inhalte per KI
      </p>
      <div className="flex gap-2">
        <Button onClick={handleSeed} disabled={seeding} className="gap-2">
          {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          🎓 90 Levels seeden
        </Button>
        <Button onClick={handleGenerateContent} disabled={generating} className="gap-2" variant="outline">
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          🤖 Inhalt generieren (9 KI-Aufrufe)
        </Button>
      </div>
      {result && (
        <div className={`p-4 rounded-xl text-sm ${result.ok ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
          {result.message}
        </div>
      )}
    </div>
  );
}

function TutorDocsAdminTab({ token }) {
  const [docs, setDocs] = useState([]);
  const [specialties, setSpecialties] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const [docsRes, specRes] = await Promise.all([
        axios.get(`${API}/tutor/documents`, { headers }),
        axios.get(`${API}/specialties`, { headers }),
      ]);
      setDocs(docsRes.data.documents || []);
      setSpecialties(specRes.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !selectedSpecialty) { setUploadResult({ ok: false, message: "Bitte Fach und PDF auswählen" }); return; }
    setUploading(true);
    setUploadResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("specialty_id", selectedSpecialty);
      const res = await axios.post(`${API}/tutor/documents/upload`, form, { headers, timeout: 120000 });
      setUploadResult({ ok: true, message: `✅ ${res.data.filename} hochgeladen (${res.data.pages} Seiten, ${res.data.chapters} Kapitel${res.data.images_extracted ? `, ${res.data.images_extracted} Bilder` : ''})` });
      e.target.value = "";
      fetchDocs();
    } catch (err) {
      const msg = err.response?.data?.detail || "Fehler beim Upload";
      setUploadResult({ ok: false, message: `❌ ${msg}` });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    try {
      await axios.delete(`${API}/tutor/documents/${docId}`, { headers });
      fetchDocs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold flex items-center gap-2"><Database className="w-5 h-5" /> Tutor Dokumente</h2>

      {/* Upload */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="font-medium mb-4">PDF hochladen</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm text-muted-foreground mb-1">Fach</label>
            <select value={selectedSpecialty} onChange={e => setSelectedSpecialty(e.target.value)}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm">
              <option value="">— Fach wählen —</option>
              {specialties.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm text-muted-foreground mb-1">PDF Datei</label>
            <input type="file" accept=".pdf" onChange={handleUpload} disabled={uploading}
              className="w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20" />
          </div>
        </div>
        {uploading && <p className="text-sm text-muted-foreground mt-2"><Loader2 className="w-4 h-4 inline animate-spin" /> Verarbeite PDF...</p>}
        {uploadResult && (
          <p className={`text-sm mt-2 ${uploadResult.ok ? 'text-green-500' : 'text-red-500'}`}>
            {uploadResult.ok ? <CheckCircle className="w-4 h-4 inline" /> : <XCircle className="w-4 h-4 inline" />} {uploadResult.message}
          </p>
        )}
      </div>

      {/* Document List */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="font-medium mb-4">Hochgeladene Dokumente ({docs.length})</h3>
        {loading ? (
          <p className="text-muted-foreground">Lade...</p>
        ) : docs.length === 0 ? (
          <p className="text-muted-foreground">Keine Dokumente hochgeladen</p>
        ) : (
          <div className="space-y-2">
            {docs.map(doc => (
              <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg border bg-background/50">
                  <div>
                    <p className="font-medium text-sm">{doc.filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {specialties.find(s => s.id === doc.specialty_id)?.name || doc.specialty_id}
                      {" · "}{doc.page_count} Seiten · {doc.chapter_count || doc.chunk_count} Kapitel · {doc.word_count} Wörter
                      {doc.has_images && (
                        doc.descriptions_pending
                          ? <span className="text-amber-500 ml-2">⏳ Bilder werden beschrieben...</span>
                          : <span className="text-green-500 ml-2">🖼️ Bilder beschrieben</span>
                      )}
                    </p>
                  </div>
                <button onClick={() => handleDelete(doc.id)} className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminPage() {
  // Safely extract human-readable error from API responses — prevents React crash when detail is an array of {type,loc,msg,input} objects from FastAPI 422
  const _safeErr = (err, fallback) => {
    let d = err?.response?.data?.detail;
    if (Array.isArray(d)) return d.map(e => e?.msg || JSON.stringify(e)).filter(Boolean).join("; ");
    return d || fallback;
  };
  const [adminStats, setAdminStats] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [users, setUsers] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [formData, setFormData] = useState(emptyQuestion);
  const [submitting, setSubmitting] = useState(false);
  const [filterSpecialty, setFilterSpecialty] = useState("all");
  const [filterCity, setFilterCity] = useState("all");
  const [filterCountry, setFilterCountry] = useState("all");
  const [filterSearch, setFilterSearch] = useState("");
  const [activeTab, setActiveTab] = useState("questions");
  const [exportCats, setExportCats] = useState(null);
  const [exportCatsLoading, setExportCatsLoading] = useState(false);
  const [exportSubject, setExportSubject] = useState("all");
  const [exportUniversity, setExportUniversity] = useState("all");
  const [exportDownloading, setExportDownloading] = useState(false);
  const [deletingQuestion, setDeletingQuestion] = useState(null);
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [questionPage, setQuestionPage] = useState(0);
  const [duplicates, setDuplicates] = useState(null);
  const [loadingDupes, setLoadingDupes] = useState(false);
  const [dupeFilter, setDupeFilter] = useState("all");
  const [selectedDupes, setSelectedDupes] = useState([]);
  const [expandedGroup, setExpandedGroup] = useState(null);
  const [merging, setMerging] = useState(false);
  const [mergeResult, setMergeResult] = useState(null);
  const [batchSource, setBatchSource] = useState("text");
  const [batchText, setBatchText] = useState("");
  const [batchTopic, setBatchTopic] = useState("");
  const [batchMix, setBatchMix] = useState({ mcq: 3, multi_select: 0, drag_drop: 0, kategorisierung: 0, lueckentext: 0 });
  const [batchFach, setBatchFach] = useState("surgery");
  const [batchYear, setBatchYear] = useState(2024);
  const [batchCity, setBatchCity] = useState("innsbruck");
  const [batchNotebook, setBatchNotebook] = useState("");
  const [notebookTitle, setNotebookTitle] = useState("");
  const [notebooks, setNotebooks] = useState([]);
  const [allSpecialties, setAllSpecialties] = useState([]);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [batchError, setBatchError] = useState(null);
  const [allTags, setAllTags] = useState([]);
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState(null);
  const [kpJsonText, setKpJsonText] = useState("");
  const [kpImportResult, setKpImportResult] = useState(null);
  const [kpImporting, setKpImporting] = useState(false);
  const [kpBulkFile, setKpBulkFile] = useState(null);
  const [kpBulkImporting, setKpBulkImporting] = useState(false);
  const [kpBulkResult, setKpBulkResult] = useState(null);
  const batchTotal = React.useMemo(() => Object.values(batchMix).reduce((a, b) => a + b, 0), [batchMix]);
  const PAGE_SIZE = 30;
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    fetchData();
    axios.get(`${API}/tags`).then(r => setAllTags(r.data)).catch(() => {});
  }, [token]);

  useEffect(() => {
    const editQId = searchParams.get("edit");
    if (editQId && token) {
      const headers = { Authorization: `Bearer ${token}` };
      axios.get(`${API}/admin/questions/${editQId}`, { headers }).then(res => {
        editQuestion(res.data);
        setActiveTab("questions");
        setSearchParams({});
      }).catch(() => {
        const q = questions.find(q => q.id === editQId);
        if (q) { editQuestion(q); setActiveTab("questions"); }
        setSearchParams({});
      });
    }
  }, [searchParams, token]);

  useEffect(() => {
    setQuestionPage(0);
    setSelectedQuestions([]);
    fetchQuestions();
  }, [filterSpecialty, filterCity, filterSearch, token]);

  useEffect(() => {
    fetchQuestions();
  }, [questionPage]);

  useEffect(() => {
    if (activeTab !== "export" || exportCats || exportCatsLoading) return;
    setExportCatsLoading(true);
    axios.get(`${API}/export/categories`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setExportCats(r.data))
      .catch(() => toast.error("Fehler beim Laden der Kategorien"))
      .finally(() => setExportCatsLoading(false));
  }, [activeTab, token]); // eslint-disable-line

  const seedKpReports = async () => {
    setSeeding(true);
    setSeedResult(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/kp-reports/seed`, {}, { headers });
      setSeedResult({ message: `${res.data.seeded} von ${res.data.total} Protokollen importiert.`, error: false });
      toast.success("KP Protokolle importiert");
    } catch (err) {
      const msg = _safeErr(err, "Fehler beim Import");
      setSeedResult({ message: msg, error: true });
      toast.error(msg);
    } finally {
      setSeeding(false);
    }
  };

  const importKpReportsJson = async () => {
    setKpImporting(true);
    setKpImportResult(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const data = JSON.parse(kpJsonText);
      const res = await axios.post(`${API}/admin/kp-reports/import-json`, data, { headers });
      setKpImportResult({ message: `${res.data.imported} importiert, ${res.data.skipped} übersprungen. Gesamt: ${res.data.total_in_db}`, error: false });
      toast.success("KP Protokolle importiert");
    } catch (err) {
      const msg = _safeErr(err, err.message || "Fehler beim Import");
      setKpImportResult({ message: msg, error: true });
      toast.error(msg);
    } finally {
      setKpImporting(false);
    }
  };

  const handleKpBulkImport = async () => {
    if (!kpBulkFile) { toast.error("Bitte eine JSON-Datei auswählen"); return; }
    setKpBulkImporting(true);
    setKpBulkResult(null);
    try {
      const text = await kpBulkFile.text();
      const data = JSON.parse(text);
      if (!Array.isArray(data)) {
        toast.error("JSON muss ein Array sein");
        setKpBulkImporting(false);
        return;
      }
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/kp-reports/import-bulk`, data, { headers });
      setKpBulkResult({ message: `${res.data.inserted} Protokolle importiert`, error: false });
      toast.success(`${res.data.inserted} Protokolle importiert`);
    } catch (err) {
      const msg = _safeErr(err, err.message || "Fehler beim Import");
      setKpBulkResult({ message: msg, error: true });
      toast.error(msg);
    } finally {
      setKpBulkImporting(false);
      setKpBulkFile(null);
    }
  };

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsRes, usersRes, leaderboardRes, onlineRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/users`, { headers }),
        axios.get(`${API}/admin/leaderboard`, { headers }),
        axios.get(`${API}/admin/activity/online`, { headers }),
      ]);
      setAdminStats(statsRes.data);
      setUsers(usersRes.data);
      setLeaderboard(leaderboardRes.data);
      setOnlineUsers(onlineRes.data);
      await fetchQuestions();
    } catch (error) {
      console.error("Failed to fetch admin data:", error);
      toast.error("Fehler beim Laden der Fragendaten. Bitte aktualisieren Sie die Seite.");
    } finally {
      setLoading(false);
    }
  };

  const fetchQuestions = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      let params = `limit=${PAGE_SIZE}&skip=${questionPage * PAGE_SIZE}`;
      if (filterSpecialty !== "all") params += `&specialty_id=${filterSpecialty}`;
      if (filterCity !== "all") params += `&exam_location=${filterCity}`;
      if (filterCountry !== "all") params += `&country=${filterCountry}`;
      if (filterSearch.trim()) params += `&search=${encodeURIComponent(filterSearch.trim())}`;
      const response = await axios.get(`${API}/questions?${params}`, { headers });
      setQuestions(response.data);
    } catch (error) {
      console.error("Failed to fetch questions:", error);
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setFormData(prev => ({ ...prev, image_base64: reader.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  const updateChoice = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      choices: prev.choices.map((c, i) => 
        i === index ? { ...c, [field]: value } : c
      )
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.specialty_id || !formData.question_text_de) {
      toast.error("Bitte füllen Sie alle Pflichtfelder aus");
      return;
    }

    const questionType = formData.question_type || "single_choice";
    
    if (questionType === "single_choice" || questionType === "multi_select") {
      const hasCorrectAnswer = formData.choices.some(c => c.is_correct);
      if (!hasCorrectAnswer) {
        toast.error("Bitte markieren Sie mindestens eine richtige Antwort");
        return;
      }
    }

    setSubmitting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const payload = {
        ...formData,
        question_text: formData.question_text_de,
        choices: formData.choices
          .filter(c => c.text_de.trim() !== "")
          .map(c => ({
            ...c,
            text: c.text_de
          })),
        explanation: formData.explanation_de
      };

      if (editingQuestion) {
        await axios.put(`${API}/questions/${editingQuestion.id}`, payload, { headers });
        toast.success("Frage erfolgreich aktualisiert");
      } else {
        await axios.post(`${API}/questions`, payload, { headers });
        toast.success("Frage erfolgreich hinzugefügt");
      }

      setDialogOpen(false);
      setEditingQuestion(null);
      setFormData(emptyQuestion);
      fetchData();
    } catch (error) {
      console.error("Failed to save question:", error);
      toast.error("Fehler beim Speichern der Frage");
    } finally {
      setSubmitting(false);
    }
  };

  const editQuestion = (question) => {
    setEditingQuestion(question);
    const filledChoices = (Array.isArray(question.choices) && question.choices.length > 0)
      ? question.choices
      : (Array.isArray(question.choices_de) ? question.choices_de : []);
    const paddedChoices = [
      ...filledChoices,
      ...Array(Math.max(0, 5 - filledChoices.length)).fill(null).map(() => ({
        id: Math.random().toString(),
        text: "",
        text_de: "",
        is_correct: false
      }))
    ];
    
    setFormData({
      ...emptyQuestion,
      ...question,
      question_text_de: question.question_text_de || question.question_text,
      explanation_de: question.explanation_de || question.explanation,
      choices: paddedChoices.map(c => ({
        ...c,
        text_de: c.text_de || c.text
      }))
    });
    setDialogOpen(true);
  };

  const deleteQuestion = async (questionId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/questions/${questionId}`, { headers });
      toast.success("Frage gelöscht");
      setSelectedQuestions(prev => prev.filter(id => id !== questionId));
      fetchData();
    } catch (error) {
      console.error("Failed to delete question:", error);
      toast.error("Fehler beim Löschen der Frage");
    }
  };

  const toggleSelectQuestion = (questionId) => {
    setSelectedQuestions(prev =>
      prev.includes(questionId) ? prev.filter(id => id !== questionId) : [...prev, questionId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedQuestions.length === questions.length) {
      setSelectedQuestions([]);
    } else {
      setSelectedQuestions(questions.map(q => q.id));
    }
  };

  const bulkDeleteQuestions = async () => {
    if (selectedQuestions.length === 0) return;
    setBulkDeleting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/admin/questions/bulk-delete`, { question_ids: selectedQuestions }, { headers });
      toast.success(`${selectedQuestions.length} Fragen gelöscht`);
      setSelectedQuestions([]);
      fetchData();
    } catch (error) {
      console.error("Bulk delete failed:", error);
      toast.error("Fehler beim Löschen. Bitte versuchen Sie es erneut.");
    } finally {
      setBulkDeleting(false);
    }
  };

  const deleteUser = async (userId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/admin/users/${userId}`, { headers });
      toast.success("Benutzer gelöscht");
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (error) {
      console.error("Failed to delete user:", error);
      toast.error(error.response?.data?.detail || "Fehler beim Löschen des Benutzers");
    }
  };

  const toggleNotebook = async (userId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/notebook/toggle/${userId}`, {}, { headers });
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, notebook_enabled: res.data.notebook_enabled } : u));
      toast.success(res.data.notebook_enabled ? "Notebook freigeschaltet" : "Notebook gesperrt");
    } catch (error) {
      toast.error("Fehler beim Ändern des Notebook-Zugangs");
    }
  };

  const toggleAnalyzer = async (userId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/analyzer/toggle/${userId}`, {}, { headers });
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, analyzer_enabled: res.data.analyzer_enabled } : u));
      toast.success(res.data.analyzer_enabled ? "Analyzer freigeschaltet" : "Analyzer gesperrt");
    } catch (error) {
      toast.error("Fehler beim Ändern des Analyzer-Zugangs");
    }
  };

  const togglePodcast = async (userId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/podcast/toggle/${userId}`, {}, { headers });
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, podcast_enabled: res.data.podcast_enabled } : u));
      toast.success(res.data.podcast_enabled ? "Podcast freigeschaltet" : "Podcast gesperrt");
    } catch (error) {
      toast.error("Fehler beim Ändern des Podcast-Zugangs");
    }
  };

  const toggleAI = async (userId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/ai/toggle/${userId}`, {}, { headers });
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, ai_enabled: res.data.ai_enabled } : u));
      toast.success(res.data.ai_enabled ? "KI freigeschaltet" : "KI gesperrt");
    } catch (error) {
      toast.error("Fehler beim Ändern des KI-Zugangs");
    }
  };

  const fetchDuplicates = async () => {
    setLoadingDupes(true);
    setSelectedDupes([]);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const params = dupeFilter !== "all" ? `?specialty_id=${dupeFilter}` : "";
      const res = await axios.get(`${API}/admin/questions/duplicates${params}`, { headers });
      setDuplicates(res.data);
    } catch {
      toast.error("Fehler beim Laden der Duplikate");
    } finally {
      setLoadingDupes(false);
    }
  };

  const bulkDeleteDupes = async () => {
    if (selectedDupes.length === 0) return;
    setBulkDeleting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/admin/questions/bulk-delete`, { question_ids: selectedDupes }, { headers });
      toast.success(`${selectedDupes.length} Duplikate gelöscht`);
      setSelectedDupes([]);
      fetchDuplicates();
      fetchData();
    } catch {
      toast.error("Fehler beim Löschen. Bitte versuchen Sie es erneut.");
    } finally {
      setBulkDeleting(false);
    }
  };

  const autoSelectDupes = () => {
    if (!duplicates?.groups) return;
    const toDelete = [];
    duplicates.groups.forEach(group => {
      group.questions.slice(1).forEach(q => toDelete.push(q.id));
    });
    setSelectedDupes(toDelete);
  };

  const smartMergeDupes = async () => {
    setMerging(true);
    setMergeResult(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const params = dupeFilter !== "all" ? `?specialty_id=${dupeFilter}` : "";
      const res = await axios.post(`${API}/admin/questions/smart-merge${params}`, {}, { headers });
      setMergeResult(res.data);
      toast.success(`${res.data.merged_groups} Gruppen zusammengeführt, ${res.data.deleted_count} Kopien gelöscht`);
      setSelectedDupes([]);
      fetchDuplicates();
      fetchData();
    } catch {
      toast.error("Fehler beim Smart Merge");
    } finally {
      setMerging(false);
    }
  };

  const fetchNotebooks = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API}/admin/notebooks/list`, { headers });
      setNotebooks(res.data || []);
    } catch { /* ignore */ }
  };

  const handleBatchGenerate = async () => {
    setBatchGenerating(true);
    setBatchResult(null);
    setBatchError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      let source_text = batchText;
      if (batchSource === "notebook" && batchNotebook) {
        const nb = notebooks.find(n => n.id === batchNotebook);
        source_text = nb?.text || "";
      }
      const payload = {
        raw_text: source_text,
        topic: batchTopic,
        mix: batchMix,
        fachgebiet: batchFach,
        jahr: batchYear,
        stadt: batchCity,
        notebook_id: batchSource === "notebook" ? batchNotebook : null,
      };
      const res = await axios.post(`${API}/admin/batch-generator/generate`, payload, { headers, timeout: 300000 });
      setBatchResult(res.data);
      setBatchText("");
      setBatchTopic("");
      setBatchMix({ mcq: 3, multi_select: 0, drag_drop: 0, kategorisierung: 0, lueckentext: 0 });
      toast.success(`${res.data.generated} Fragen erstellt!`);
    } catch (err) {
      const msg = _safeErr(err, err.message || "Fehler bei der Generierung");
      setBatchError(msg);
      toast.error(msg);
    } finally {
      setBatchGenerating(false);
    }
  };

  useEffect(() => {
    if (token) fetchNotebooks();
  }, [token]);

  useEffect(() => {
    axios.get(`${API}/specialties`).then(r => setAllSpecialties(r.data)).catch(() => {});
  }, []);

  const openNewQuestion = () => {
    setEditingQuestion(null);
    setFormData(emptyQuestion);
    setDialogOpen(true);
  };


  const downloadExportPDF = async () => {
    setExportDownloading(true);
    try {
      const url = `${API}/export/questions/pdf?subject=${encodeURIComponent(exportSubject)}&university=${encodeURIComponent(exportUniversity)}`;
      const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Export fehlgeschlagen (${response.status})`);
      }
      const blob = await response.blob();
      const disp = response.headers.get("content-disposition") || "";
      const nameMatch = disp.match(/filename="([^"]+)"/);
      const filename = nameMatch ? nameMatch[1] : "PrepAcademy_Export.pdf";
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      toast.success("PDF erfolgreich erstellt");
    } catch (err) {
      console.error("[PDF export] failed:", err);
      toast.error(err.message || "Download fehlgeschlagen", { duration: 8000 });

    } finally {
      setExportDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8" style={{ paddingBottom: "max(2rem, env(safe-area-inset-bottom))" }}>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-primary/10">
            <Settings className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="admin-title">Admin-Bereich</h1>
            <p className="text-muted-foreground">Fragen und Benutzer verwalten</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/admin/analytics">
            <Button variant="outline" className="gap-2">
              <BarChart3 className="w-4 h-4" />
              Analytics
            </Button>
          </Link>
          <Link to="/">
            <Button variant="ghost" className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Zurück
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="glass-card rounded-xl p-6" data-testid="admin-stat-users">
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-5 h-5 text-primary" />
            <span className="text-sm text-muted-foreground">Benutzer</span>
          </div>
          <div className="text-3xl font-bold">{adminStats?.total_users || 0}</div>
        </div>
        <div className="glass-card rounded-xl p-6" data-testid="admin-stat-questions">
          <div className="flex items-center gap-3 mb-2">
            <FileQuestion className="w-5 h-5 text-emerald-500" />
            <span className="text-sm text-muted-foreground">Fragen</span>
          </div>
          <div className="text-3xl font-bold">{adminStats?.total_questions || 0}</div>
        </div>
        <div className="glass-card rounded-xl p-6" data-testid="admin-stat-favorites">
          <div className="flex items-center gap-3 mb-2">
            <Heart className="w-5 h-5 text-red-500" />
            <span className="text-sm text-muted-foreground">Favoriten</span>
          </div>
          <div className="text-3xl font-bold">{adminStats?.total_favorites || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Link
          to="/admin/question-import"
          className="glass-card rounded-xl p-6 hover:shadow-lg transition-shadow group cursor-pointer block"
          title="Bulk import exam questions from PDF or Markdown files"
        >
          <div className="flex items-center gap-3 mb-2">
            <Upload className="w-5 h-5 text-blue-500" />
            <span className="text-sm font-semibold">Question Import Tool</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Import PDF and Markdown exam files, validate questions, generate missing options and export results.
          </p>
        </Link>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex flex-wrap gap-x-1 gap-y-2 border-b border-border mb-6 bg-transparent p-0 h-auto">
          <TabsTrigger value="questions" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <FileQuestion className="w-4 h-4" />
            Fragen
          </TabsTrigger>
          <TabsTrigger value="users" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <Users className="w-4 h-4" />
            Benutzer
          </TabsTrigger>
          <TabsTrigger value="leaderboard" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <Trophy className="w-4 h-4" />
            Rangliste
          </TabsTrigger>
          <TabsTrigger value="export" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <Download className="w-4 h-4" />
            Export
          </TabsTrigger>
          <TabsTrigger value="import" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="import-tab">
            <Upload className="w-4 h-4" />
            Import
          </TabsTrigger>
          <TabsTrigger value="duplicates" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="duplicates-tab" onClick={() => { if (!duplicates) fetchDuplicates(); }}>
            <Copy className="w-4 h-4" />
            Duplikate
          </TabsTrigger>
          <TabsTrigger value="batch-generator" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" onClick={() => fetchNotebooks()}>
            <Sparkles className="w-4 h-4" />
            Batch Generator
          </TabsTrigger>
          <TabsTrigger value="reports" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="reports-tab">
            <Flag className="w-4 h-4" />
            Meldungen
          </TabsTrigger>
          <TabsTrigger value="kp-reports" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <FileText className="w-4 h-4" />
            KP Protokolle
          </TabsTrigger>
          <TabsTrigger value="masterclass" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <GraduationCap className="w-4 h-4" />
            Masterclass
          </TabsTrigger>
          <TabsTrigger value="access-requests" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="access-requests-tab">
            <ShieldCheck className="w-4 h-4" />
            Zugang
          </TabsTrigger>
          <TabsTrigger value="tags" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="tags-tab">
            <Tag className="w-4 h-4" />
            Tags
          </TabsTrigger>
          <TabsTrigger value="podcast" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="podcast-tab">
            <Headphones className="w-4 h-4" />
            Daily Podcast
          </TabsTrigger>
          <TabsTrigger value="online" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <Wifi className="w-4 h-4" />
            Online
          </TabsTrigger>
          <TabsTrigger value="tutor-docs" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background">
            <Database className="w-4 h-4" />
            Tutor Docs
          </TabsTrigger>
          {ADVANCED_FEATURES_ENABLED && (
            <TabsTrigger value="rag" className="px-3 py-2 text-sm font-medium rounded-t-lg flex items-center gap-1.5 whitespace-nowrap border border-border border-b-0 data-[state=active]:bg-background data-[state=active]:border-b-background" data-testid="rag-tab">
              <ShieldCheck className="w-4 h-4" />
              RAG Knowledge
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="questions">
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Fragen verwalten</h2>
              <div className="flex items-center gap-4">
                <Select value={filterSpecialty} onValueChange={setFilterSpecialty}>
                  <SelectTrigger className="w-40" data-testid="admin-filter-specialty">
                    <SelectValue placeholder="Alle Fachgebiete" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Fachgebiete</SelectItem>
                    {SPECIALTIES.map(spec => (
                      <SelectItem key={spec.id} value={spec.id}>{spec.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterCity} onValueChange={v => { setFilterCity(v); setQuestionPage(0); }}>
                  <SelectTrigger className="w-36" data-testid="admin-filter-city">
                    <SelectValue placeholder="Alle Orte" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Orte</SelectItem>
                    {CITIES.map(city => (
                      <SelectItem key={city.id} value={city.id}>{city.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterCountry} onValueChange={v => { setFilterCountry(v); setQuestionPage(0); }}>
                  <SelectTrigger className="w-28">
                    <SelectValue placeholder="Alle Länder" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Länder</SelectItem>
                    <SelectItem value="austria">Österreich</SelectItem>
                    <SelectItem value="germany">Deutschland</SelectItem>
                    <SelectItem value="switzerland">Schweiz</SelectItem>
                  </SelectContent>
                </Select>

                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Frage suchen…"
                    value={filterSearch}
                    onChange={e => setFilterSearch(e.target.value)}
                    className="w-56 pl-8"
                  />
                </div>

                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                  <DialogTrigger asChild>
                    <Button onClick={openNewQuestion} className="gap-2" data-testid="add-question-btn">
                      <Plus className="w-4 h-4" />
                      Frage hinzufügen
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-5xl w-[95vw] max-h-[90vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
                    <DialogHeader>
                      <DialogTitle>
                        {editingQuestion ? "Frage bearbeiten" : "Neue Frage hinzufügen"}
                      </DialogTitle>
                    </DialogHeader>
                    
                    <form onSubmit={handleSubmit} className="space-y-6 mt-4">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>Fachgebiet *</Label>
                          <Select 
                            value={formData.specialty_id} 
                            onValueChange={(v) => setFormData(prev => ({ ...prev, specialty_id: v }))}
                          >
                            <SelectTrigger data-testid="form-specialty">
                              <SelectValue placeholder="Fachgebiet wählen" />
                            </SelectTrigger>
                            <SelectContent>
                              {SPECIALTIES.map(spec => (
                                <SelectItem key={spec.id} value={spec.id}>{spec.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Jahr *</Label>
                          <Select 
                            value={formData.year.toString()} 
                            onValueChange={(v) => setFormData(prev => ({ ...prev, year: parseInt(v) }))}
                          >
                            <SelectTrigger data-testid="form-year">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {YEARS.map(year => (
                                <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Stadt *</Label>
                          <Select 
                            value={formData.exam_location || "vienna"} 
                            onValueChange={(v) => setFormData(prev => ({ ...prev, exam_location: v }))}
                          >
                            <SelectTrigger data-testid="form-city">
                              <SelectValue placeholder="Stadt wählen" />
                            </SelectTrigger>
                            <SelectContent>
                              {CITIES.map(city => (
                                <SelectItem key={city.id} value={city.id}>{city.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Land</Label>
                          <Select 
                            value={formData.country || "none"} 
                            onValueChange={(v) => setFormData(prev => ({ ...prev, country: v === "none" ? "" : v }))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Land wählen" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">—</SelectItem>
                              <SelectItem value="austria">Österreich</SelectItem>
                              <SelectItem value="germany">Deutschland</SelectItem>
                              <SelectItem value="switzerland">Schweiz</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Fragetyp Dropdown */}
                      <div className="space-y-2">
                        <Label>Fragetyp *</Label>
                        <select
                          className="w-full border border-input rounded-md p-2 bg-background text-foreground"
                          value={formData.question_type || "single_choice"}
                          onChange={(e) => setFormData(prev => ({ ...prev, question_type: e.target.value }))}
                          data-testid="form-question-type"
                        >
                          <option value="single_choice">Single Choice (eine richtige Antwort)</option>
                          <option value="multi_select">Multi Select (mehrere richtige Antworten)</option>
                          <option value="drag_drop">Drag & Drop</option>
                          <option value="kategorisierung">Kategorisierung</option>
                          <option value="luckentext">Lückentext</option>
                        </select>
                      </div>

                      {/* Status toggle (only when editing) */}
                      {editingQuestion && (
                        <div className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border">
                          <div className="flex items-center gap-2">
                            {formData.status === 'draft'
                              ? <X className="w-4 h-4 text-amber-500" />
                              : <Upload className="w-4 h-4 text-emerald-500" />
                            }
                            <Label className="cursor-pointer" onClick={() => setFormData(prev => ({ ...prev, status: prev.status === 'draft' ? 'published' : 'draft' }))}>
                              {formData.status === 'draft' ? 'Entwurf — Nicht für Benutzer sichtbar' : 'Veröffentlicht — Für alle Benutzer sichtbar'}
                            </Label>
                          </div>
                          <Switch
                            checked={formData.status !== 'draft'}
                            onCheckedChange={(v) => setFormData(prev => ({ ...prev, status: v ? 'published' : 'draft' }))}
                          />
                        </div>
                      )}

                      <div className="space-y-2">
                        <Label>Fragetext *</Label>
                        <Textarea
                          value={formData.question_text_de}
                          onChange={(e) => setFormData(prev => ({ ...prev, question_text_de: e.target.value }))}
                          placeholder="Geben Sie den Fragetext ein"
                          rows={3}
                          data-testid="form-question-text"
                        />
                      </div>

                      {/* Image Upload */}
                      <div className="space-y-2">
                        <Label>Bild (optional)</Label>
                        <div className="flex items-center gap-4">
                          <label className="flex items-center gap-2 px-4 py-2 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors">
                            <Upload className="w-4 h-4" />
                            <span>Bild hochladen</span>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={handleImageUpload}
                              className="hidden"
                              data-testid="form-image-upload"
                            />
                          </label>
                          {formData.image_base64 && (
                            <div className="relative">
                              <img src={formData.image_base64} alt="" className="h-16 rounded-lg" />
                              <button
                                type="button"
                                onClick={() => setFormData(prev => ({ ...prev, image_base64: "" }))}
                                className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* ✅ Choices - only show for single_choice and multi_select */}
                      {(formData.question_type === "single_choice" || formData.question_type === "multi_select" || !formData.question_type) && (
                        <div className="space-y-4">
                          <Label>Antwortmöglichkeiten (richtige Antworten markieren)</Label>
                          {formData.choices.map((choice, index) => (
                            <div key={index} className="flex items-center gap-3">
                              <Switch
                                checked={choice.is_correct}
                                onCheckedChange={(v) => updateChoice(index, "is_correct", v)}
                                data-testid={`form-choice-correct-${index}`}
                              />
                              <span className="w-6 text-center font-medium text-muted-foreground">
                                {String.fromCharCode(65 + index)}
                              </span>
                              <Input
                                value={choice.text_de}
                                onChange={(e) => updateChoice(index, "text_de", e.target.value)}
                                placeholder={`Antwort ${String.fromCharCode(65 + index)}`}
                                className="flex-1"
                                data-testid={`form-choice-text-${index}`}
                              />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* ✅ NEW: QuestionTypeFields for drag_drop, kategorisierung, luckentext */}
                      <QuestionTypeFields
                        questionType={formData.question_type}
                        formData={formData}
                        setFormData={setFormData}
                      />

                      <div className="space-y-2">
                        <Label>Erklärung (optional)</Label>
                        <Textarea
                          value={formData.explanation_de}
                          onChange={(e) => setFormData(prev => ({ ...prev, explanation_de: e.target.value }))}
                          placeholder="Geben Sie eine Erklärung zur richtigen Antwort ein"
                          rows={3}
                          data-testid="form-explanation"
                        />
                      </div>

                      {allTags.length > 0 && (
                        <div className="space-y-2" data-testid="form-tags-section">
                          <Label className="flex items-center gap-1.5">
                            <Tag className="w-3.5 h-3.5" />
                            Tags
                          </Label>
                          <div className="flex flex-wrap gap-2">
                            {allTags.map(tag => {
                              const selected = (formData.tags || []).includes(tag.id);
                              return (
                                <button key={tag.id} type="button" data-testid={`form-tag-${tag.id}`}
                                  onClick={() => setFormData(prev => ({
                                    ...prev,
                                    tags: selected
                                      ? (prev.tags || []).filter(t => t !== tag.id)
                                      : [...(prev.tags || []), tag.id]
                                  }))}
                                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                                    selected ? "ring-1 ring-current border-current" : "border-border text-muted-foreground hover:border-current"
                                  }`}
                                  style={{ color: selected ? tag.color : undefined }}>
                                  <span className="w-2 h-2 rounded-full" style={{ background: tag.color }} />
                                  {tag.name}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      <div className="flex justify-between gap-3 pt-4">
                        {editingQuestion ? (
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={() => {
                              if (window.confirm("Frage wirklich löschen?")) {
                                deleteQuestion(editingQuestion.id);
                                setDialogOpen(false);
                              }
                            }}
                            data-testid="form-delete-btn"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Löschen
                          </Button>
                        ) : <div />}
                        <div className="flex gap-3">
                          <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                            Abbrechen
                          </Button>
                          <Button type="submit" disabled={submitting} data-testid="form-submit-btn">
                            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                            {editingQuestion ? "Aktualisieren" : "Hinzufügen"}
                          </Button>
                        </div>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            {selectedQuestions.length > 0 && (
              <div className="flex items-center justify-between flex-wrap gap-3 p-3 mb-4 bg-blue-500/10 border border-blue-500/20 rounded-xl" data-testid="bulk-actions-bar">
                <span className="text-sm font-medium">
                  {selectedQuestions.length} Frage(n) ausgewählt
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  <Select onValueChange={async (city) => {
                    try {
                      const headers = { Authorization: `Bearer ${token}` };
                      await axios.post(`${API}/admin/questions/bulk-update-city`, { question_ids: selectedQuestions, exam_location: city }, { headers });
                      toast.success(`${selectedQuestions.length} Fragen -> ${getCityLabel(city)}`);
                      setSelectedQuestions([]);
                      fetchQuestions();
                    } catch { toast.error("Fehler beim Aktualisieren"); }
                  }}>
                    <SelectTrigger className="w-[160px] h-8" data-testid="bulk-city-select">
                      <SelectValue placeholder="Stadt ändern" />
                    </SelectTrigger>
                    <SelectContent>
                      {CITIES.map(city => (
                        <SelectItem key={city.id} value={city.id}>{city.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Button variant="outline" size="sm" className="gap-2 text-emerald-500 border-emerald-500/30" onClick={async () => {
                    try {
                      const headers = { Authorization: `Bearer ${token}` };
                      await axios.post(`${API}/admin/questions/bulk-status`, { question_ids: selectedQuestions, status: "published" }, { headers });
                      toast.success(`${selectedQuestions.length} Fragen veröffentlicht`);
                      setSelectedQuestions([]);
                      fetchQuestions();
                    } catch { toast.error("Fehler"); }
                  }}>
                    <Upload className="w-3.5 h-3.5" /> Veröffentlichen
                  </Button>
                  <Button variant="outline" size="sm" className="gap-2 text-amber-500 border-amber-500/30" onClick={async () => {
                    try {
                      const headers = { Authorization: `Bearer ${token}` };
                      await axios.post(`${API}/admin/questions/bulk-status`, { question_ids: selectedQuestions, status: "draft" }, { headers });
                      toast.success(`${selectedQuestions.length} Fragen als Entwurf gespeichert`);
                      setSelectedQuestions([]);
                      fetchQuestions();
                    } catch { toast.error("Fehler"); }
                  }}>
                    <X className="w-3.5 h-3.5" /> Entwurf
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm" className="gap-2" disabled={bulkDeleting} data-testid="bulk-delete-btn">
                        {bulkDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        Löschen
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>{selectedQuestions.length} Fragen löschen</AlertDialogTitle>
                        <AlertDialogDescription>
                          Sind Sie sicher, dass Sie {selectedQuestions.length} Fragen löschen möchten?
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                        <AlertDialogAction onClick={bulkDeleteQuestions} className="bg-red-500 hover:bg-red-600">
                          {selectedQuestions.length} Fragen löschen
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox
                        checked={questions.length > 0 && selectedQuestions.length === questions.length}
                        onCheckedChange={toggleSelectAll}
                        data-testid="select-all-checkbox"
                      />
                    </TableHead>
                    <TableHead>Frage</TableHead>
                    <TableHead>Fachgebiet</TableHead>
                    <TableHead>Ort</TableHead>
                    <TableHead>Land</TableHead>
                    <TableHead>Jahr</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Antworten</TableHead>
                    <TableHead className="w-24">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {questions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        Keine Fragen vorhanden
                      </TableCell>
                    </TableRow>
                  ) : (
                    questions.map((question, index) => {
                      const countryBadge = getCountryBadge(question.country);
                      return (
                      <TableRow key={question.id} data-testid={`question-row-${index}`} className={selectedQuestions.includes(question.id) ? "bg-red-500/5" : ""}>
                        <TableCell>
                          <Checkbox
                            checked={selectedQuestions.includes(question.id)}
                            onCheckedChange={() => toggleSelectQuestion(question.id)}
                            data-testid={`select-question-${index}`}
                          />
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {question.question_text_de || question.question_text}
                        </TableCell>
                        <TableCell>
                          {SPECIALTIES.find(s => s.id === question.specialty_id)?.name || question.specialty_id}
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${question.exam_location === 'vienna' ? 'bg-blue-500/20 text-blue-400' : question.exam_location === 'innsbruck' ? 'bg-emerald-500/20 text-emerald-400' : question.exam_location === 'hamburg' ? 'bg-yellow-500/15 text-yellow-600' : 'bg-gray-500/20 text-gray-400'}`}>
                            {getCityLabel(question.exam_location)}
                          </span>
                        </TableCell>
                        <TableCell>
                          {countryBadge ? (
                            <span className={`inline-flex min-w-8 justify-center px-2 py-0.5 rounded text-xs font-semibold border ${countryBadge.className}`}>
                              {countryBadge.label}
                            </span>
                          ) : <span className="text-muted-foreground">—</span>}
                        </TableCell>
                        <TableCell>{question.year}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                              question.status === 'draft'
                                ? 'bg-amber-500/15 text-amber-500 border border-amber-500/20'
                                : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/20'
                            }`}>
                              {question.status === 'draft' ? 'Entwurf' : 'Veröffentlicht'}
                            </span>
                            <button
                              onClick={async () => {
                                try {
                                  const headers = { Authorization: `Bearer ${token}` };
                                  const res = await axios.put(`${API}/admin/questions/${question.id}/status`, {}, { headers });
                                  toast.success(res.data.status === 'published' ? 'Veröffentlicht' : 'Als Entwurf gespeichert');
                                  fetchQuestions();
                                } catch { toast.error("Fehler beim Ändern des Status"); }
                              }}
                              className="ml-1 p-1 rounded hover:bg-muted transition-colors"
                              title={question.status === 'draft' ? 'Veröffentlichen' : 'Als Entwurf speichern'}
                            >
                              {question.status === 'draft' ? <Upload className="w-3 h-3" /> : <X className="w-3 h-3" />}
                            </button>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-emerald-500">
                            {question.choices?.filter(c => c.is_correct).length || 0}
                          </span>
                          /{question.choices?.length || 0}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button variant="ghost" size="icon" onClick={() => editQuestion(question)} data-testid={`edit-question-${index}`}>
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-400" data-testid={`delete-question-${index}`}>
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Frage löschen</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Sind Sie sicher, dass Sie diese Frage löschen möchten?
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => deleteQuestion(question.id)} className="bg-red-500 hover:bg-red-600">
                                    Löschen
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                    })
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <Button variant="outline" size="sm" onClick={() => setQuestionPage(p => Math.max(0, p - 1))} disabled={questionPage === 0} data-testid="prev-page-btn">
                Zurück
              </Button>
              <span className="text-sm text-muted-foreground">
                Seite {questionPage + 1} · {questions.length} Ergebnisse
              </span>
              <Button variant="outline" size="sm" onClick={() => setQuestionPage(p => p + 1)} disabled={questions.length < PAGE_SIZE} data-testid="next-page-btn">
                Weiter
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="users">
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Benutzer verwalten</h2>
              <span className="text-sm text-muted-foreground">{users.length} Benutzer</span>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Benutzer</TableHead>
                    <TableHead>E-Mail</TableHead>
                    <TableHead>Anmeldung</TableHead>
                    <TableHead>Registriert</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-center">Notebook</TableHead>
                    <TableHead className="text-center">Analyzer</TableHead>
                    <TableHead className="text-center">Podcast</TableHead>
                    <TableHead className="text-center">KI</TableHead>
                    <TableHead className="w-24">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user, index) => (
                    <TableRow key={user.id} data-testid={`user-row-${index}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          {user.picture ? (
                            <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
                          ) : (
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                              <Users className="w-4 h-4 text-primary" />
                            </div>
                          )}
                          <span className="font-medium">{user.name}</span>
                        </div>
                      </TableCell>
                      <TableCell><div className="flex items-center gap-2 text-sm"><Mail className="w-4 h-4 text-muted-foreground" /><span>{user.email}</span></div></TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium ${user.auth_provider === 'google' ? 'bg-blue-500/10 text-blue-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                          {user.auth_provider === 'google' ? 'Google' : 'E-Mail'}
                        </span>
                      </TableCell>
                      <TableCell><div className="flex items-center gap-2 text-sm text-muted-foreground"><Calendar className="w-4 h-4" />{new Date(user.created_at).toLocaleDateString('de-DE')}</div></TableCell>
                      <TableCell>{user.is_admin ? <span className="flex items-center gap-1 text-amber-500 text-sm"><Shield className="w-4 h-4" />Admin</span> : <span className="text-sm text-muted-foreground">Benutzer</span>}</TableCell>
                      <TableCell className="text-center">
                        {user.is_admin ? <span className="text-xs text-amber-500">Immer</span> : <Switch checked={!!user.notebook_enabled} onCheckedChange={() => toggleNotebook(user.id)} data-testid={`notebook-toggle-${index}`} />}
                      </TableCell>
                      <TableCell className="text-center">
                        {user.is_admin ? <span className="text-xs text-amber-500">Immer</span> : <Switch checked={!!user.analyzer_enabled} onCheckedChange={() => toggleAnalyzer(user.id)} data-testid={`analyzer-toggle-${index}`} />}
                      </TableCell>
                      <TableCell className="text-center">
                        {user.is_admin ? <span className="text-xs text-amber-500">Immer</span> : <Switch checked={!!user.podcast_enabled} onCheckedChange={() => togglePodcast(user.id)} data-testid={`podcast-toggle-${index}`} />}
                      </TableCell>
                      <TableCell className="text-center">
                        {user.is_admin ? <span className="text-xs text-amber-500">Immer</span> : <Switch checked={!!user.ai_enabled} onCheckedChange={() => toggleAI(user.id)} data-testid={`ai-toggle-${index}`} />}
                      </TableCell>
                      <TableCell>
                        {!user.is_admin && (
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-400" data-testid={`delete-user-${index}`}><Trash2 className="w-4 h-4" /></Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Benutzer löschen</AlertDialogTitle>
                                <AlertDialogDescription>Sind Sie sicher, dass Sie "{user.name}" löschen möchten?</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                                <AlertDialogAction onClick={() => deleteUser(user.id)} className="bg-red-500 hover:bg-red-600">Löschen</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="leaderboard">
          <div className="glass-card rounded-2xl p-6">
            <h2 className="text-xl font-semibold flex items-center gap-2 mb-6">
              <Trophy className="w-5 h-5 text-amber-500" />
              Benutzer-Rangliste
            </h2>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Benutzer</TableHead>
                    <TableHead className="text-center">Fragen</TableHead>
                    <TableHead className="text-center">Richtig</TableHead>
                    <TableHead className="text-center">Falsch</TableHead>
                    <TableHead className="text-center">Genauigkeit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaderboard.map((user, index) => (
                    <TableRow key={user.id} data-testid={`leaderboard-row-${index}`}>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center"><Users className="w-4 h-4 text-primary" /></div>
                          <div><p className="font-medium">{user.name}</p><p className="text-xs text-muted-foreground">{user.email}</p></div>
                        </div>
                      </TableCell>
                      <TableCell className="text-center font-medium">{user.total_questions}</TableCell>
                      <TableCell className="text-center text-emerald-500 font-medium">{user.correct_answers}</TableCell>
                      <TableCell className="text-center text-red-500 font-medium">{user.wrong_answers}</TableCell>
                      <TableCell className="text-center"><span className="text-sm font-medium">{Math.round(user.accuracy || 0)}%</span></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="export">
          <div className="glass-card rounded-2xl p-6 space-y-6">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Download className="w-5 h-5 text-primary" />
              Fragen exportieren
            </h2>

            {exportCatsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
              </div>
            ) : exportCats ? (
              <>
                {/* Subject filter */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Fachgebiet</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                    <button
                      onClick={() => setExportSubject("all")}
                      className={`text-left px-3 py-2.5 rounded-xl border text-sm transition-all ${
                        exportSubject === "all"
                          ? "border-amber-500/60 bg-amber-500/10 text-amber-300"
                          : "border-border text-muted-foreground hover:border-amber-500/30 hover:text-foreground"
                      }`}
                    >
                      <div className="font-medium">Alle Fachgebiete</div>
                      <div className="text-xs opacity-70">{exportCats.total.toLocaleString()} Fragen</div>
                    </button>
                    {exportCats.subjects.map(s => (
                      <button
                        key={s.id}
                        onClick={() => setExportSubject(s.id)}
                        className={`text-left px-3 py-2.5 rounded-xl border text-sm transition-all ${
                          exportSubject === s.id
                            ? "border-amber-500/60 bg-amber-500/10 text-amber-300"
                            : "border-border text-muted-foreground hover:border-amber-500/30 hover:text-foreground"
                        }`}
                      >
                        <div className="font-medium">{s.name}</div>
                        <div className="text-xs opacity-70">{s.count.toLocaleString()} Fragen</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* University filter */}
                {exportCats.universities.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Standort</h3>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setExportUniversity("all")}
                        className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                          exportUniversity === "all"
                            ? "border-primary/60 bg-primary/10 text-primary"
                            : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
                        }`}
                      >
                        Alle Standorte
                      </button>
                      {exportCats.universities.map(u => (
                        <button
                          key={u.id}
                          onClick={() => setExportUniversity(u.id)}
                          className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                            exportUniversity === u.id
                              ? "border-primary/60 bg-primary/10 text-primary"
                              : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
                          }`}
                        >
                          {u.name}
                          <span className="ml-1.5 text-xs opacity-60">({u.count.toLocaleString()})</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Preview + export */}
                <div className="flex items-center justify-between pt-4 border-t border-border flex-wrap gap-4">
                  <div>
                    {(() => {
                      const previewCount =
                        exportSubject === "all" && exportUniversity === "all" ? exportCats.total :
                        exportSubject !== "all" && exportUniversity === "all" ? (exportCats.subjects.find(s => s.id === exportSubject)?.count ?? 0) :
                        exportSubject === "all" && exportUniversity !== "all" ? (exportCats.universities.find(u => u.id === exportUniversity)?.count ?? 0) :
                        null;
                      return (
                        <div className="text-sm font-medium">
                          {previewCount !== null ? (
                            <><span className="text-2xl font-bold text-amber-400">{previewCount.toLocaleString()}</span>{" "}Fragen ausgewählt</>
                          ) : (
                            <span className="text-base font-medium">Auswahl: Gefiltert</span>
                          )}
                        </div>
                      );
                    })()}
                    <div className="text-xs text-muted-foreground mt-1">
                      {exportSubject === "all" ? "Alle Fachgebiete" : exportCats.subjects.find(s => s.id === exportSubject)?.name}
                      {" · "}
                      {exportUniversity === "all" ? "Alle Standorte" : (exportCats.universities.find(u => u.id === exportUniversity)?.name ?? exportUniversity)}
                    </div>
                  </div>
                  <Button
                    onClick={downloadExportPDF}
                    disabled={exportDownloading}
                    className="gap-2 bg-amber-600 hover:bg-amber-500 text-white min-w-[160px]"
                  >
                    {exportDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    PDF exportieren
                  </Button>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground text-sm py-8 text-center">Kategorien konnten nicht geladen werden.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="import">
          <ImportQuestionsTab token={token} onImportComplete={() => { fetchData(); fetchQuestions(); }} />
        </TabsContent>

        <TabsContent value="duplicates">
          <div className="space-y-4">
            {/* Header */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h2 className="text-xl font-semibold">Duplikate finden</h2>
                  <p className="text-sm text-muted-foreground mt-1">Doppelte Fragen erkennen, zusammenführen oder löschen</p>
                </div>
                <div className="flex items-center gap-3">
                  <Select value={dupeFilter} onValueChange={v => { setDupeFilter(v); if (duplicates) fetchDuplicates(); }}>
                    <SelectTrigger className="w-40"><SelectValue placeholder="Alle" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Alle Fachgebiete</SelectItem>
                      {(allSpecialties.length ? allSpecialties : []).map(f => <SelectItem key={f.id} value={f.id}>{f.name || f.name_de}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button onClick={smartMergeDupes} disabled={!duplicates?.groups?.length || merging} className="gap-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700">
                    {merging ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Smart Merge
                  </Button>
                  <Button onClick={fetchDuplicates} disabled={loadingDupes} className="gap-2">
                    {loadingDupes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                    Scannen
                  </Button>
                </div>
              </div>
            </div>

            {/* Stats */}
            {duplicates && (
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-amber-600">{duplicates.total_duplicate_groups || 0}</div>
                  <div className="text-sm text-amber-700 mt-1">Duplikat-Gruppen</div>
                </div>
                <div className="bg-rose-50 border border-rose-100 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-rose-600">{duplicates.total_extra_copies || 0}</div>
                  <div className="text-sm text-rose-700 mt-1">Zusätzliche Kopien</div>
                </div>
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-emerald-600">{duplicates.groups?.length || 0}</div>
                  <div className="text-sm text-emerald-700 mt-1">Angezeigt</div>
                </div>
              </div>
            )}

            {/* Merge Result */}
            {mergeResult && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
                <p className="text-emerald-800 font-medium">
                  ✅ {mergeResult.merged_groups} Gruppen zusammengeführt, {mergeResult.deleted_count || mergeResult.deleted_questions} Kopien gelöscht
                </p>
                <Button variant="ghost" size="sm" onClick={() => setMergeResult(null)}><X className="w-4 h-4" /></Button>
              </div>
            )}

            {/* Auto-select + Bulk Delete */}
            {duplicates?.groups?.length > 0 && (
              <div className="bg-gray-100 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Checkbox id="auto-select" checked={selectedDupes.length > 0} onCheckedChange={() => autoSelectDupes()} />
                  <label htmlFor="auto-select" className="text-sm font-medium cursor-pointer">Kopien automatisch markieren</label>
                </div>
                {selectedDupes.length > 0 && (
                  <Button variant="destructive" size="sm" onClick={bulkDeleteDupes} disabled={bulkDeleting} className="gap-2">
                    {bulkDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    {selectedDupes.length} Kopien löschen
                  </Button>
                )}
              </div>
            )}

            {/* Groups List */}
            {loadingDupes ? (
              <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
            ) : !duplicates ? (
              <div className="glass-card rounded-2xl p-12 text-center text-muted-foreground">
                <Copy className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Klicken Sie auf "Scannen" um Duplikate zu finden</p>
              </div>
            ) : duplicates.groups?.length === 0 ? (
              <div className="glass-card rounded-2xl p-12 text-center text-muted-foreground">
                <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Keine Duplikate gefunden</p>
              </div>
            ) : (
              <div className="space-y-3">
                {duplicates.groups.map((group, gi) => (
                  <div key={group._id || gi} className="glass-card rounded-xl p-4 hover:border-blue-500/20 transition">
                    <div className="flex items-start gap-4">
                      <Button variant="ghost" size="icon" className="w-8 h-8 rounded-full shrink-0" onClick={() => setExpandedGroup(expandedGroup === (group._id || gi) ? null : (group._id || gi))}>
                        <Play className="w-3 h-3 text-muted-foreground" fill="currentColor" />
                      </Button>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-amber-100 text-amber-700 text-xs font-semibold shrink-0 mt-1">{group.count || group.questions?.length}x</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-foreground truncate">{group._id || group.questions?.[0]?.question_text_de || group.questions?.[0]?.question_text}</p>
                      </div>
                    </div>
                    {expandedGroup === (group._id || gi) && group.questions && (
                      <div className="mt-4 pl-12 space-y-2 border-t pt-4">
                        {group.questions.map((q, qi) => (
                          <div key={q.id || qi} className="flex items-center gap-3 p-2 rounded-lg bg-muted/30">
                            <Checkbox checked={selectedDupes.includes(q.id)} onCheckedChange={() => {
                              setSelectedDupes(prev => prev.includes(q.id) ? prev.filter(id => id !== q.id) : [...prev, q.id]);
                            }} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-foreground">{q.question_text_de || q.question_text}</p>
                              <p className="text-xs text-muted-foreground mt-1">{q.specialty_id} · {q.year} · {q.exam_location}</p>
                            </div>
                            {qi === 0 && <span className="text-xs text-emerald-600 font-medium shrink-0">Original</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="batch-generator">
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold">Batch Generator</h2>
                <p className="text-sm text-muted-foreground mt-1">KI erstellt mehrere Fragen aus einem Text oder PDF</p>
              </div>
            </div>

            {/* Source Type */}
            <div className="flex gap-2 mb-6">
              <button onClick={() => setBatchSource("text")} className={`px-4 py-2 rounded-full text-sm font-medium transition ${batchSource === "text" ? "bg-amber-100 text-amber-700 border border-amber-200" : "text-muted-foreground hover:bg-muted border"}`}>Rohtext / Thema</button>
              <button onClick={() => setBatchSource("notebook")} className={`px-4 py-2 rounded-full text-sm font-medium transition ${batchSource === "notebook" ? "bg-amber-100 text-amber-700 border border-amber-200" : "text-muted-foreground hover:bg-muted border"}`}>PDF-Notebook</button>
            </div>

            {/* Text Input */}
            {batchSource === "text" ? (
              <div className="space-y-3 mb-6">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Thema (optional)</label>
                  <Input value={batchTopic} onChange={e => setBatchTopic(e.target.value)} placeholder="z.B. Schluckstörungen, Larynxkarzinom..." />
                </div>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Rohtext / Lerninhalte</label>
                  <Textarea value={batchText} onChange={e => setBatchText(e.target.value)} rows={6} placeholder="Füge den Lerninhalt ein..." className="resize-none" />
                  <p className="text-xs text-muted-foreground mt-1">{batchText.length} Zeichen</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3 mb-6">
                <div className="bg-amber-50/50 border border-amber-100 rounded-xl p-4">
                  <label className="text-sm font-medium mb-2 block">Notebook auswählen</label>
                  <select value={batchNotebook} onChange={e => setBatchNotebook(e.target.value)} className="w-full px-4 py-2.5 bg-white border rounded-lg text-sm">
                    <option value="">PDF-Notebook wählen</option>
                    {notebooks.map(nb => <option key={nb.id} value={nb.id}>{nb.title} ({nb.page_count || '?'} Seiten)</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Oder neues Notebook hochladen</label>
                  <div className="flex gap-2">
                    <Input value={notebookTitle} onChange={e => setNotebookTitle(e.target.value)} placeholder="Titel" className="w-64" />
                    <Input type="file" accept=".txt,.pdf" onChange={async e => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      if (file.name.endsWith('.pdf')) {
                        try {
                          const formData = new FormData();
                          formData.append('file', file);
                          const headers = { Authorization: `Bearer ${token}` };
                          const res = await axios.post(`${API}/admin/batch-generator/extract-pdf`, formData, { headers, timeout: 30000 });
                          setNotebookTitle(file.name.replace(/\.[^/.]+$/, ""));
                          setBatchText(res.data.text);
                          setBatchSource("text");
                          toast.success(`"${file.name}" extrahiert (${res.data.pages} Seiten, ${res.data.chars} Zeichen)`);
                        } catch (err) {
                          toast.error(_safeErr(err, "PDF-Extraktion fehlgeschlagen"));
                        }
                      } else {
                        const text = await file.text();
                        setNotebookTitle(file.name.replace(/\.[^/.]+$/, ""));
                        setBatchText(text);
                        setBatchSource("text");
                        toast.success(`"${file.name}" geladen (${text.length} Zeichen)`);
                      }
                    }} className="flex-1" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Unterstützt .txt und .pdf</p>
                </div>
              </div>
            )}

            {/* Fragen-Mix */}
            <div className="bg-muted/30 rounded-xl p-5 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Fragen-Mix</h3>
                <span className={`text-sm font-bold ${batchTotal > 30 ? "text-red-600" : batchTotal > 24 ? "text-amber-600" : "text-green-600"}`}>Gesamt: {batchTotal} / 30</span>
              </div>
              <div className="grid grid-cols-5 gap-3">
                {[
                  {key:"mcq", label:"MCQ"},
                  {key:"multi_select", label:"Multi-Select"},
                  {key:"drag_drop", label:"Drag & Drop"},
                  {key:"kategorisierung", label:"Kategorisierung"},
                  {key:"lueckentext", label:"Lückentext"},
                ].map(({key, label}) => (
                  <div key={key}>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">{label}</label>
                    <input type="number" value={batchMix[key]} onChange={e => setBatchMix({...batchMix, [key]: Math.max(0, Math.min(30, parseInt(e.target.value) || 0))})} min={0} max={30} className="w-full px-3 py-2 bg-white border rounded-lg text-sm text-center font-semibold" />
                  </div>
                ))}
              </div>
            </div>

            {/* Meta Fields */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Fachgebiet</label>
                <select value={batchFach} onChange={e => setBatchFach(e.target.value)} className="w-full px-4 py-2.5 bg-white border rounded-lg text-sm">
                  {(allSpecialties.length ? allSpecialties : [{id:"surgery",name:"Chirurgie"},{id:"internal",name:"Innere Medizin"}]).map(f => <option key={f.id} value={f.id}>{f.name || f.name_de}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Jahr</label>
                <Input type="number" value={batchYear} onChange={e => setBatchYear(parseInt(e.target.value) || 2024)} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Stadt</label>
                <select value={batchCity} onChange={e => setBatchCity(e.target.value)} className="w-full px-4 py-2.5 bg-white border rounded-lg text-sm">
                  {[{v:"wien",l:"Wien"},{v:"graz",l:"Graz"},{v:"innsbruck",l:"Innsbruck"},{v:"linz",l:"Linz"},{v:"salzburg",l:"Salzburg"},{v:"ai_generated",l:"🤖 KI Fragen"}].map(c => <option key={c.v} value={c.v}>{c.l}</option>)}
                </select>
              </div>
            </div>

            {/* Progress */}
            {batchGenerating && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                <p className="text-sm font-medium text-amber-900 mb-2">Generiert {batchTotal} Fragen...</p>
                <div className="w-full bg-amber-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-gradient-to-r from-amber-400 to-amber-600 h-full w-2/3 rounded-full animate-pulse" />
                </div>
              </div>
            )}

            {/* Error */}
            {batchError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <p className="text-sm text-red-800">❌ {batchError}</p>
                <Button variant="ghost" size="sm" onClick={() => setBatchError(null)}><X className="w-4 h-4" /></Button>
              </div>
            )}

            {/* Results */}
            {batchResult && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <p className="text-sm text-emerald-800 font-medium">
                  ✅ {batchResult.generated} von {batchResult.requested} Fragen erfolgreich generiert!
                </p>
                <Button variant="ghost" size="sm" onClick={() => { setBatchResult(null); fetchQuestions(); fetchData(); }}><X className="w-4 h-4" /></Button>
              </div>
            )}

            {/* Generate Button */}
            <div className="flex justify-end">
              <Button onClick={handleBatchGenerate} disabled={batchGenerating || batchTotal === 0 || batchTotal > 30 || (batchSource === "text" && !batchText)} className="gap-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700">
                <Sparkles className="w-4 h-4" />
                {batchGenerating ? "Generiert..." : `${batchTotal} Fragen generieren`}
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="reports">
          <AdminReportsTab token={token} />
        </TabsContent>

        <TabsContent value="kp-reports">
          <div className="space-y-6">
            {/* Seed */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  <h2 className="text-xl font-semibold">KP Protokolle</h2>
                </div>
                <Button variant="default" size="sm" onClick={seedKpReports} disabled={seeding} className="gap-2">
                  {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {seeding ? "Wird importiert..." : "Seed Daten importieren"}
                </Button>
              </div>
              {seedResult && (
                <div className={`p-3 rounded-lg text-sm ${seedResult.error ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                  {seedResult.message}
                </div>
              )}
              <p className="text-sm text-muted-foreground mt-2">
                Importiert die 3 Beispiel-Protokolle in die Datenbank. Bereits vorhandene werden übersprungen.
              </p>
            </div>

            {/* JSON Import */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Upload className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold">JSON Import</h2>
              </div>
              <div className="space-y-4">
                <div>
                  <Label>Protokolle als JSON einfügen</Label>
                  <Textarea
                    className="font-mono text-sm mt-1 min-h-[300px]"
                    placeholder='{"reports": [{"state": "Niedersachsen", "year": 2022, "main_case": "..."}]}'
                    value={kpJsonText}
                    onChange={(e) => setKpJsonText(e.target.value)}
                  />
                </div>
                {kpImportResult && (
                  <div className={`p-3 rounded-lg text-sm ${kpImportResult.error ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                    {kpImportResult.message}
                  </div>
                )}
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => { setKpJsonText(""); setKpImportResult(null); }}>
                    Zurücksetzen
                  </Button>
                  <Button onClick={importKpReportsJson} disabled={kpImporting || !kpJsonText.trim()} className="gap-2">
                    {kpImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                    {kpImporting ? "Importiert..." : "JSON importieren"}
                  </Button>
                </div>
              </div>
            </div>

            {/* Bulk Import JSON from File */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Upload className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold">Bulk Import JSON</h2>
              </div>
              <div className="space-y-4">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-primary/30 rounded-2xl cursor-pointer hover:border-primary/60 hover:bg-primary/5 transition-all">
                  <Upload className="w-8 h-8 text-primary/50 mb-2" />
                  <span className="text-sm font-medium text-primary">
                    {kpBulkFile ? kpBulkFile.name : "JSON-Datei auswählen (.json)"}
                  </span>
                  <input
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files[0];
                      if (!f) return;
                      if (!f.name.endsWith('.json')) {
                        toast.error("Nur JSON-Dateien sind erlaubt");
                        return;
                      }
                      setKpBulkFile(f);
                      setKpBulkResult(null);
                    }}
                  />
                </label>
                {kpBulkResult && (
                  <div className={`p-3 rounded-lg text-sm ${kpBulkResult.error ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                    {kpBulkResult.message}
                  </div>
                )}
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => { setKpBulkFile(null); setKpBulkResult(null); }}>
                    Zurücksetzen
                  </Button>
                  <Button onClick={handleKpBulkImport} disabled={kpBulkImporting || !kpBulkFile} className="gap-2">
                    {kpBulkImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                    {kpBulkImporting ? "Importiert..." : "📥 Bulk Import JSON"}
                  </Button>
                </div>
              </div>
            </div>

            {/* Format Reference */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold">JSON Format</h2>
              </div>
              <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
{`{
  "reports": [
    {
      "state": "Niedersachsen",
      "year": 2022,
      "date": "2022-01-26",
      "main_case": "Divertikulitis",
      "passed": "1/3",
      "author": "Dr. Parvin",
      "difficulty": "mittel",
      "topics_asked": ["Divertikulitis", "Sepsis"],
      "questions_highlighted": ["qSOFA", "CRUB 65"],
      "examiner_notes": "Anmerkungen zum Prüfer...",
      "full_text": "Ausführlicher Bericht..."
    }
  ]
}`}
              </pre>
              <p className="text-xs text-muted-foreground mt-2">
                Pflichtfelder: <code>state</code>, <code>main_case</code>. 
                Alternative Feldnamen: <code>topics</code>/<code>themen</code>, <code>highlights</code>/<code>fragen</code>,
                <code>notes</code>/<code>notizen</code>, <code>text</code>/<code>bericht</code>, <code>protocol_id</code>.
                Array-Name: <code>reports</code> oder <code>protokolle</code>.
              </p>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="masterclass">
          <MasterclassAdminTab token={token} />
        </TabsContent>

        <TabsContent value="access-requests">
          <AdminAccessRequestsTab token={token} />
        </TabsContent>

        <TabsContent value="tags">
          <AdminTagsTab token={token} />
        </TabsContent>

        <TabsContent value="podcast">
          <AdminPodcastTab token={token} />
        </TabsContent>

        <TabsContent value="online">
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Wifi className="w-5 h-5 text-emerald-500" />
                <h2 className="text-xl font-semibold">Online-Status</h2>
              </div>
              <Button variant="outline" size="sm" onClick={fetchData} className="gap-1">
                <Activity className="w-3.5 h-3.5" />
                Aktualisieren
              </Button>
            </div>

            <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
              {onlineUsers.length === 0 ? (
                <div className="col-span-full text-center py-12 text-muted-foreground">
                  <WifiOff className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  Keine Aktivitätsdaten vorhanden
                </div>
              ) : (
                [...onlineUsers].sort((a, b) => b.is_online - a.is_online).map((u, i) => (
                  <div
                    key={u.user_id || i}
                    className={`rounded-xl p-4 flex flex-col gap-1.5 transition-shadow cursor-default ${
                      u.is_online ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-muted/30 border border-border/60'
                    }`}
                    onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'}
                    onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
                  >
                    <div className="flex items-center gap-2">
                      {u.is_online
                        ? <Wifi className="w-4 h-4 text-emerald-500" />
                        : <WifiOff className="w-4 h-4 text-muted-foreground" />
                      }
                      <span className="font-semibold text-base">
                        {u.name || '?'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground m-0">
                      {u.email || '?'}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="tutor-docs">
          <TutorDocsAdminTab token={token} />
        </TabsContent>

        {ADVANCED_FEATURES_ENABLED && (
          <TabsContent value="rag">
            <AdminRagTab token={token} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
