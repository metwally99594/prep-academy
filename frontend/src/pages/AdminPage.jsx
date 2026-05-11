import { useState, useEffect } from "react";
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
  ShieldCheck
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
  { id: "andere", name: "Andere Stadt" },
];

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 2009 + 6 }, (_, i) => 2009 + i);

const emptyQuestion = {
  specialty_id: "",
  year: new Date().getFullYear(),
  exam_location: "vienna",
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
};

function ImportQuestionsTab({ token, onImportComplete }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileSelect = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (!f.name.endsWith('.json')) {
      toast.error("Nur JSON-Dateien sind erlaubt");
      return;
    }
    setFile(f);
    setResult(null);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        if (Array.isArray(data)) {
          const specs = {};
          data.forEach(q => {
            const sid = (q.specialty_id || q.fach || q.specialty || 'unknown').toLowerCase().trim();
            specs[sid] = (specs[sid] || 0) + 1;
          });
          setPreview({ total: data.length, specialties: specs, sample: data.slice(0, 3) });
        } else {
          toast.error("JSON muss eine Liste von Fragen sein");
          setFile(null);
        }
      } catch {
        toast.error("Ungültige JSON-Datei");
        setFile(null);
      }
    };
    reader.readAsText(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setImporting(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/admin/import-questions`, formData, { headers, timeout: 120000 });
      setResult(res.data);
      toast.success(`${res.data.imported} Fragen erfolgreich importiert!`);
      if (onImportComplete) onImportComplete();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Import fehlgeschlagen");
    } finally {
      setImporting(false);
    }
  };

  const handleClear = () => { setFile(null); setPreview(null); setResult(null); };

  return (
    <div className="glass-card rounded-2xl p-6">
      <h2 className="text-xl font-semibold mb-2">Fragen importieren</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Laden Sie eine JSON-Datei mit Fragen hoch. Doppelte Fragen werden automatisch übersprungen.
      </p>
      <details className="mb-6 rounded-xl border border-border overflow-hidden">
        <summary className="flex items-center justify-between px-4 py-3 bg-muted/40 cursor-pointer select-none hover:bg-muted/70 transition-colors">
          <span className="text-sm font-semibold">JSON-Format Dokumentation</span>
          <span className="text-xs text-muted-foreground">▾ aufklappen</span>
        </summary>

        <div className="p-4 space-y-5">

          {/* MCQ / Multi-Select */}
          <div>
            <p className="font-semibold text-sm mb-2">──── JSON-Format (MCQ / Multi-Select) ────</p>
            <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm leading-relaxed">{`[
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
    "explanation_de": "Erklärung...",
    "image_base64": "data:image/png;base64,..."
  }
]`}</pre>
          </div>

          {/* Drag & Drop */}
          <div>
            <p className="font-semibold text-sm mb-2">──── JSON-Format (Drag &amp; Drop / Kategorisierung) ────</p>
            <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm leading-relaxed">{`{
  "specialty_id": "internal",
  "question_type": "drag_drop",
  "question_text_de": "Ordnen Sie die Symptome zu.",
  "interactive_data": {
    "items": [
      {"id": "i1", "text_de": "Brustschmerz"},
      {"id": "i2", "text_de": "Schwindel beim Aufstehen"}
    ],
    "categories": [
      {"id": "cat_a", "label_de": "Kardial"},
      {"id": "cat_b", "label_de": "Harmlos"}
    ],
    "correct_mapping": {"i1": "cat_a", "i2": "cat_b"}
  },
  "year": 2025,
  "exam_location": "vienna"
}`}</pre>
          </div>

          {/* Fill in the blank */}
          <div>
            <p className="font-semibold text-sm mb-2">──── JSON-Format (Lückentext) ────</p>
            <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm leading-relaxed">{`{
  "specialty_id": "internal",
  "question_type": "fill_blank",
  "question_text_de": "Beschriften Sie die Herzkammern.",
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
  "exam_location": "vienna"
}`}</pre>
          </div>

          {/* Erlaubte Werte */}
          <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm space-y-2">
            <p className="font-semibold">──── Erlaubte Werte ────</p>
            <p>
              <span className="font-medium">Fragetypen:&nbsp;</span>
              <code className="text-xs bg-muted px-1 py-0.5 rounded">mcq</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">multi_select</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">drag_drop</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">categorize</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">fill_blank</code>
            </p>
            <p>
              <span className="font-medium">Specialty IDs:&nbsp;</span>
              <span className="text-muted-foreground text-xs">
                surgery, internal, ophthalmology, dermatology, ent, obgyn, neurology, emergency, pediatrics, psychiatry
              </span>
            </p>
            <p>
              <span className="font-medium">Orte:&nbsp;</span>
              <code className="text-xs bg-muted px-1 py-0.5 rounded">vienna</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">innsbruck</code>{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">andere</code>
            </p>
          </div>

        </div>
      </details>
      {!file ? (
        <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-primary/30 rounded-2xl cursor-pointer hover:border-primary/60 hover:bg-primary/5 transition-all" data-testid="import-dropzone">
          <Upload className="w-10 h-10 text-primary/50 mb-3" />
          <span className="text-sm font-medium text-primary">JSON-Datei auswählen</span>
          <span className="text-xs text-muted-foreground mt-1">oder hierher ziehen</span>
          <input type="file" accept=".json" className="hidden" onChange={handleFileSelect} data-testid="import-file-input" />
        </label>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-3">
              <FileQuestion className="w-8 h-8 text-primary" />
              <div>
                <div className="font-medium">{file.name}</div>
                <div className="text-sm text-muted-foreground">{(file.size / 1024).toFixed(0)} KB</div>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={handleClear} data-testid="import-clear-btn">
              <X className="w-4 h-4" />
            </Button>
          </div>
          {preview && !result && (
            <div className="p-4 rounded-xl bg-muted/50 border border-border">
              <h3 className="font-medium mb-3">Vorschau: {preview.total} Fragen</h3>
              <div className="flex flex-wrap gap-2 mb-3">
                {Object.entries(preview.specialties).map(([id, count]) => (
                  <span key={id} className="px-2 py-1 rounded-full bg-primary/10 text-xs font-medium">{id}: {count}</span>
                ))}
              </div>
              {preview.sample.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Beispiel-Fragen:</p>
                  {preview.sample.map((q, i) => (
                    <div key={i} className="text-xs p-2 rounded-lg bg-background border border-border truncate">
                      {q.question_text_de || q.question || q.frage || q.text || '(Kein Text)'}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {result && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20" data-testid="import-result">
              <h3 className="font-medium text-emerald-600 mb-2">Import abgeschlossen!</h3>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div className="text-center p-2 rounded-lg bg-background">
                  <div className="text-xl font-bold text-emerald-600">{result.imported}</div>
                  <div className="text-xs text-muted-foreground">Importiert</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-background">
                  <div className="text-xl font-bold text-amber-500">{result.skipped}</div>
                  <div className="text-xs text-muted-foreground">Übersprungen</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-background">
                  <div className="text-xl font-bold text-primary">{result.total_in_db}</div>
                  <div className="text-xs text-muted-foreground">Gesamt in DB</div>
                </div>
              </div>
            </div>
          )}
          {!result && (
            <Button onClick={handleImport} disabled={importing} className="w-full h-12 gap-2" data-testid="import-submit-btn">
              {importing ? (<><Loader2 className="w-5 h-5 animate-spin" />Importiere {preview?.total || 0} Fragen...</>) : (<><Upload className="w-5 h-5" />{preview?.total || 0} Fragen importieren</>)}
            </Button>
          )}
          {result && (
            <Button variant="outline" onClick={handleClear} className="w-full gap-2" data-testid="import-another-btn">
              <Upload className="w-4 h-4" /> Weitere Fragen importieren
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminPage() {
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
  const [allTags, setAllTags] = useState([]);
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
  }, [filterSpecialty, filterCity, token]);

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
    <div className="max-w-7xl mx-auto px-4 py-8">
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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="questions" className="gap-2">
            <FileQuestion className="w-4 h-4" />
            Fragen
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-2">
            <Users className="w-4 h-4" />
            Benutzer
          </TabsTrigger>
          <TabsTrigger value="leaderboard" className="gap-2">
            <Trophy className="w-4 h-4" />
            Rangliste
          </TabsTrigger>
          <TabsTrigger value="export" className="gap-2">
            <Download className="w-4 h-4" />
            Export
          </TabsTrigger>
          <TabsTrigger value="import" className="gap-2" data-testid="import-tab">
            <Upload className="w-4 h-4" />
            Import
          </TabsTrigger>
          <TabsTrigger value="duplicates" className="gap-2" data-testid="duplicates-tab" onClick={() => { if (!duplicates) fetchDuplicates(); }}>
            <Copy className="w-4 h-4" />
            Duplikate
          </TabsTrigger>
          <TabsTrigger value="reports" className="gap-2" data-testid="reports-tab">
            <Flag className="w-4 h-4" />
            Meldungen
          </TabsTrigger>
          <TabsTrigger value="tags" className="gap-2" data-testid="tags-tab">
            <Tag className="w-4 h-4" />
            Tags
          </TabsTrigger>
          <TabsTrigger value="podcast" className="gap-2" data-testid="podcast-tab">
            <Headphones className="w-4 h-4" />
            Daily Podcast
          </TabsTrigger>
          {process.env.REACT_APP_ADVANCED === "true" && (
            <TabsTrigger value="rag" className="gap-2" data-testid="rag-tab">
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
                    <SelectItem value="vienna">Wien</SelectItem>
                    <SelectItem value="innsbruck">Innsbruck</SelectItem>
                    <SelectItem value="andere">Andere</SelectItem>
                  </SelectContent>
                </Select>

                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                  <DialogTrigger asChild>
                    <Button onClick={openNewQuestion} className="gap-2" data-testid="add-question-btn">
                      <Plus className="w-4 h-4" />
                      Frage hinzufügen
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
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
                      </div>

                      {/* ✅ NEW: Fragetyp Dropdown */}
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
                      toast.success(`${selectedQuestions.length} Fragen → ${city === 'vienna' ? 'Wien' : city === 'innsbruck' ? 'Innsbruck' : 'Andere'}`);
                      setSelectedQuestions([]);
                      fetchQuestions();
                    } catch { toast.error("Fehler beim Aktualisieren"); }
                  }}>
                    <SelectTrigger className="w-[160px] h-8" data-testid="bulk-city-select">
                      <SelectValue placeholder="Stadt ändern" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vienna">Wien</SelectItem>
                      <SelectItem value="innsbruck">Innsbruck</SelectItem>
                      <SelectItem value="andere">Andere</SelectItem>
                    </SelectContent>
                  </Select>

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
                    <TableHead>Jahr</TableHead>
                    <TableHead>Antworten</TableHead>
                    <TableHead className="w-24">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {questions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        Keine Fragen vorhanden
                      </TableCell>
                    </TableRow>
                  ) : (
                    questions.map((question, index) => (
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
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${question.exam_location === 'vienna' ? 'bg-blue-500/20 text-blue-400' : question.exam_location === 'innsbruck' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}`}>
                            {question.exam_location === 'vienna' ? 'Wien' : question.exam_location === 'innsbruck' ? 'Innsbruck' : question.exam_location || '—'}
                          </span>
                        </TableCell>
                        <TableCell>{question.year}</TableCell>
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
                    ))
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
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Duplikate finden</h2>
              <Button onClick={fetchDuplicates} disabled={loadingDupes} className="gap-2">
                {loadingDupes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                Scannen
              </Button>
            </div>
            {!duplicates && !loadingDupes && (
              <div className="text-center py-12 text-muted-foreground">
                <Copy className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Klicken Sie auf "Scannen" um Duplikate zu finden</p>
                      </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="reports">
          <AdminReportsTab token={token} />
        </TabsContent>

        <TabsContent value="tags">
          <AdminTagsTab token={token} />
        </TabsContent>

        <TabsContent value="podcast">
          <AdminPodcastTab token={token} />
        </TabsContent>

        {process.env.REACT_APP_ADVANCED === "true" && (
          <TabsContent value="rag">
            <AdminRagTab token={token} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
