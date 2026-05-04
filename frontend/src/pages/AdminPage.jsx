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
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
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
  { id: "special", name: "Special" },
];

// Cities for exam location
const CITIES = [
  { id: "vienna", name: "Wien" },
  { id: "innsbruck", name: "Innsbruck" },
  { id: "andere", name: "Andere Stadt" },
];

// Years from 2009 to current year + 5
const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 2009 + 6 }, (_, i) => 2009 + i);

const emptyQuestion = {
  specialty_id: "",
  year: new Date().getFullYear(),
  exam_location: "vienna",
  question_text: "",
  question_text_de: "",
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
      <div className="mb-6 p-4 rounded-xl bg-muted/50 border border-border">
        <h3 className="font-medium mb-2 text-sm">JSON-Format:</h3>
        <pre className="text-xs text-muted-foreground overflow-x-auto">{`[
  {
    "specialty_id": "surgery",
    "question_text_de": "Was ist...?",
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
        <p className="text-xs text-muted-foreground mt-2">
          IDs: surgery, internal, ophthalmology, dermatology, ent, obgyn, neurology, emergency, pediatrics, psychiatry
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Orte: vienna, innsbruck, andere
        </p>
      </div>
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
              {result.errors?.length > 0 && (
                <div className="text-xs text-red-500 mt-2">
                  {result.errors.map((e, i) => <div key={i}>{e}</div>)}
                </div>
              )}
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
  const [exportingPDF, setExportingPDF] = useState(false);
  const [exportProgress, setExportProgress] = useState('');
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Handle ?edit=question_id from reports page
  useEffect(() => {
    const editQId = searchParams.get("edit");
    if (editQId && token) {
      const headers = { Authorization: `Bearer ${token}` };
      axios.get(`${API}/admin/questions/${editQId}`, { headers }).then(res => {
        editQuestion(res.data);
        setActiveTab("questions");
        setSearchParams({});
      }).catch(() => {
        // Fallback: find in loaded questions
        const q = questions.find(q => q.id === editQId);
        if (q) { editQuestion(q); setActiveTab("questions"); }
        setSearchParams({});
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, token]);

  useEffect(() => {
    setQuestionPage(0);
    setSelectedQuestions([]);
    fetchQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSpecialty, filterCity, token]);

  useEffect(() => {
    fetchQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionPage]);

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
      // Load first page of questions separately
      await fetchQuestions();
    } catch (error) {
      console.error("Failed to fetch admin data:", error);
      toast.error("Fehler beim Laden der Daten");
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

    const hasCorrectAnswer = formData.choices.some(c => c.is_correct);
    if (!hasCorrectAnswer) {
      toast.error("Bitte markieren Sie mindestens eine richtige Antwort");
      return;
    }

    setSubmitting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      // Use German text for both fields
      const payload = {
        ...formData,
        question_text: formData.question_text_de, // Copy German to main field
        choices: formData.choices
          .filter(c => c.text_de.trim() !== "")
          .map(c => ({
            ...c,
            text: c.text_de // Copy German to main field
          })),
        explanation: formData.explanation_de // Copy German to main field
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
    const filledChoices = question.choices || [];
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
      toast.error("Fehler beim Löschen");
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
      toast.error("Fehler beim Löschen");
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

  // Export questions to PDF
  const exportQuestionsToPDF = async (specialtyFilter = null, cityFilter = null) => {
    setExportingPDF(true);
    setExportProgress('Fragen laden...');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      let url = `${API}/admin/export/questions?`;
      if (specialtyFilter) url += `specialty_id=${specialtyFilter}&`;
      if (cityFilter) url += `exam_location=${cityFilter}&`;
      
      const response = await axios.get(url, { headers });
      const { questions: exportedQuestions, total, exported_at } = response.data;
      
      const date = new Date(exported_at).toLocaleDateString('de-DE');
      const cityLabel = cityFilter === 'vienna' ? ' - Wien' : cityFilter === 'innsbruck' ? ' - Innsbruck' : '';

      // Create hidden container for rendering
      const container = document.createElement('div');
      container.style.cssText = 'position:fixed;top:-99999px;left:0;width:800px;background:#fff;font-family:Arial,sans-serif;padding:40px;';
      document.body.appendChild(container);

      // Group questions by specialty
      const grouped = {};
      exportedQuestions.forEach((q) => {
        const specName = q.specialty_name || 'Unbekannt';
        if (!grouped[specName]) grouped[specName] = [];
        grouped[specName].push(q);
      });

      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const margin = 10;
      const usableW = pageW - margin * 2;

      // --- Header page ---
      const headerDiv = document.createElement('div');
      headerDiv.style.cssText = 'width:800px;padding:60px 40px;background:#fff;text-align:center;';
      headerDiv.innerHTML = `
        <div style="font-size:36px;font-weight:bold;color:#667eea;margin-bottom:10px;">Prep Academy</div>
        <div style="font-size:18px;color:#444;margin-bottom:30px;">Fragenexport${cityLabel} - ${date}</div>
        <div style="display:inline-block;background:#667eea;color:#fff;padding:20px 40px;border-radius:12px;">
          <div style="font-size:42px;font-weight:bold;">${total}</div>
          <div style="font-size:14px;">Fragen insgesamt</div>
        </div>
      `;
      container.appendChild(headerDiv);

      const headerCanvas = await html2canvas(headerDiv, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
      const headerImgData = headerCanvas.toDataURL('image/jpeg', 0.92);
      const headerRatio = headerCanvas.height / headerCanvas.width;
      const headerImgH = usableW * headerRatio;
      pdf.addImage(headerImgData, 'JPEG', margin, margin, usableW, headerImgH);
      container.removeChild(headerDiv);

      // --- Questions as images ---
      let globalIndex = 0;
      const specNames = Object.keys(grouped);

      for (let si = 0; si < specNames.length; si++) {
        const specName = specNames[si];
        const specQuestions = grouped[specName];

        // Specialty header
        pdf.addPage();
        const specDiv = document.createElement('div');
        specDiv.style.cssText = 'width:800px;padding:20px 40px;background:#fff;';
        specDiv.innerHTML = `<h2 style="color:#667eea;border-bottom:3px solid #667eea;padding-bottom:12px;font-size:24px;margin:0;">${specName} (${specQuestions.length} Fragen)</h2>`;
        container.appendChild(specDiv);
        const specCanvas = await html2canvas(specDiv, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
        const specImgData = specCanvas.toDataURL('image/jpeg', 0.92);
        const specRatio = specCanvas.height / specCanvas.width;
        pdf.addImage(specImgData, 'JPEG', margin, margin, usableW, usableW * specRatio);
        let yPos = margin + usableW * specRatio + 5;
        container.removeChild(specDiv);

        for (let qi = 0; qi < specQuestions.length; qi++) {
          globalIndex++;
          const q = specQuestions[qi];
          const choicesArr = (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []);
          const correctAnswers = q.correct_answers || [];

          const locName = q.exam_location === 'vienna' ? 'Wien' : q.exam_location === 'innsbruck' ? 'Innsbruck' : (q.exam_location || '');

          let choicesHTML = choicesArr.map((c, i) => {
            const isCorrect = c.is_correct || correctAnswers.includes(c.id);
            return `<div style="margin:4px 0;padding:8px 12px;background:${isCorrect ? '#dcfce7' : '#f3f4f6'};border-radius:6px;font-size:14px;">
              <strong>${String.fromCharCode(65 + i)}.</strong> ${c.text_de || c.text || ''} ${isCorrect ? '<span style="color:#16a34a;font-weight:bold;">✓</span>' : ''}
            </div>`;
          }).join('');

          const imageHTML = q.image_base64 ? `<div style="margin:10px 0;"><img src="${q.image_base64}" style="max-width:380px;max-height:280px;border-radius:8px;border:1px solid #e5e7eb;" /></div>` : '';

          const explanationHTML = (q.explanation_de || q.explanation) ? `<div style="margin-top:10px;padding:10px;background:#fef3c7;border-radius:6px;font-size:13px;"><strong>Erklärung:</strong> ${q.explanation_de || q.explanation}</div>` : '';

          const qDiv = document.createElement('div');
          qDiv.style.cssText = 'width:800px;padding:16px 40px;background:#fff;';
          qDiv.innerHTML = `
            <div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px;background:#fff;">
              <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;">
                <span style="background:#667eea;color:#fff;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;">${q.year || ''}</span>
                <span style="background:#f3f4f6;padding:3px 10px;border-radius:6px;font-size:12px;">${locName}</span>
                <span style="margin-left:auto;color:#999;font-size:12px;">Frage ${globalIndex}/${total}</span>
              </div>
              <p style="font-weight:600;margin:0 0 12px 0;font-size:15px;line-height:1.5;">${globalIndex}. ${q.question_text_de || q.question_text || ''}</p>
              ${imageHTML}
              ${choicesHTML}
              ${explanationHTML}
            </div>
          `;
          container.appendChild(qDiv);

          const qCanvas = await html2canvas(qDiv, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
          setExportProgress(`Frage ${globalIndex}/${total} wird gerendert...`);
          const qImgData = qCanvas.toDataURL('image/jpeg', 0.92);
          const qRatio = qCanvas.height / qCanvas.width;
          const qImgH = usableW * qRatio;

          // Check if fits on current page
          if (yPos + qImgH > pageH - margin) {
            pdf.addPage();
            yPos = margin;
          }
          pdf.addImage(qImgData, 'JPEG', margin, yPos, usableW, qImgH);
          yPos += qImgH + 3;
          container.removeChild(qDiv);
        }
      }

      // Footer on last page
      const footerY = pdf.internal.pageSize.getHeight() - 15;
      pdf.setFontSize(9);
      pdf.setTextColor(150);
      pdf.text('Generiert von Prep Academy - Medizinische Prüfungsvorbereitung', pageW / 2, footerY, { align: 'center' });

      // Cleanup and save
      document.body.removeChild(container);
      const fileName = `PrepAcademy_Export${cityLabel.replace(/ /g,'_')}_${date.replace(/\./g,'-')}.pdf`;
      pdf.save(fileName);

      toast.success(`${total} Fragen als PDF exportiert`);
    } catch (error) {
      console.error("Failed to export questions:", error);
      toast.error("Fehler beim Exportieren");
    } finally {
      setExportingPDF(false);
      setExportProgress('');
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
      {/* Header */}
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
        <Link to="/">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Zurück
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
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

      {/* Tabs */}
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

        {/* Questions Tab */}
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

                      {/* Choices */}
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

                      {/* Explanation */}
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

                      {/* Tags */}
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

            {/* Bulk Actions Bar */}
            {selectedQuestions.length > 0 && (
              <div className="flex items-center justify-between flex-wrap gap-3 p-3 mb-4 bg-blue-500/10 border border-blue-500/20 rounded-xl" data-testid="bulk-actions-bar">
                <span className="text-sm font-medium">
                  {selectedQuestions.length} Frage(n) ausgewählt
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Bulk City Update */}
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

                  {/* Bulk Delete */}
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
                          Sind Sie sicher, dass Sie {selectedQuestions.length} Fragen löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.
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

            {/* Questions Table */}
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
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => editQuestion(question)}
                              data-testid={`edit-question-${index}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="text-red-500 hover:text-red-400"
                                  data-testid={`delete-question-${index}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Frage löschen</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Sind Sie sicher, dass Sie diese Frage löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                                  <AlertDialogAction 
                                    onClick={() => deleteQuestion(question.id)}
                                    className="bg-red-500 hover:bg-red-600"
                                  >
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

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuestionPage(p => Math.max(0, p - 1))}
                disabled={questionPage === 0}
                data-testid="prev-page-btn"
              >
                Zurück
              </Button>
              <span className="text-sm text-muted-foreground">
                Seite {questionPage + 1} · {questions.length} Ergebnisse
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuestionPage(p => p + 1)}
                disabled={questions.length < PAGE_SIZE}
                data-testid="next-page-btn"
              >
                Weiter
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users">
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Benutzer verwalten</h2>
              <span className="text-sm text-muted-foreground">
                {users.length} Benutzer
              </span>
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
                    <TableHead className="w-24">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                        Keine Benutzer vorhanden
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((user, index) => (
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
                        <TableCell>
                          <div className="flex items-center gap-2 text-sm">
                            <Mail className="w-4 h-4 text-muted-foreground" />
                            <span>{user.email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            user.auth_provider === 'google' 
                              ? 'bg-blue-500/10 text-blue-500' 
                              : 'bg-emerald-500/10 text-emerald-500'
                          }`}>
                            {user.auth_provider === 'google' ? 'Google' : 'E-Mail'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Calendar className="w-4 h-4" />
                            {new Date(user.created_at).toLocaleDateString('de-DE')}
                          </div>
                        </TableCell>
                        <TableCell>
                          {user.is_admin ? (
                            <span className="flex items-center gap-1 text-amber-500 text-sm">
                              <Shield className="w-4 h-4" />
                              Admin
                            </span>
                          ) : (
                            <span className="text-sm text-muted-foreground">Benutzer</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {user.is_admin ? (
                            <span className="text-xs text-amber-500 flex items-center justify-center gap-1">
                              <BookOpen className="w-3.5 h-3.5" />
                              Immer
                            </span>
                          ) : (
                            <Switch
                              checked={!!user.notebook_enabled}
                              onCheckedChange={() => toggleNotebook(user.id)}
                              data-testid={`notebook-toggle-${index}`}
                            />
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {user.is_admin ? (
                            <span className="text-xs text-amber-500 flex items-center justify-center gap-1">
                              <Activity className="w-3.5 h-3.5" />
                              Immer
                            </span>
                          ) : (
                            <Switch
                              checked={!!user.analyzer_enabled}
                              onCheckedChange={() => toggleAnalyzer(user.id)}
                              data-testid={`analyzer-toggle-${index}`}
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {!user.is_admin && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="text-red-500 hover:text-red-400"
                                  data-testid={`delete-user-${index}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Benutzer löschen</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Sind Sie sicher, dass Sie den Benutzer "{user.name}" löschen möchten? Alle Daten werden gelöscht und diese Aktion kann nicht rückgängig gemacht werden.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                                  <AlertDialogAction 
                                    onClick={() => deleteUser(user.id)}
                                    className="bg-red-500 hover:bg-red-600"
                                  >
                                    Löschen
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        {/* Leaderboard Tab */}
        <TabsContent value="leaderboard">
          <div className="grid gap-6">
            {/* Online Users */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Wifi className="w-5 h-5 text-emerald-500" />
                  Online-Status
                </h2>
                <Button variant="ghost" size="sm" onClick={fetchData}>
                  Aktualisieren
                </Button>
              </div>
              
              {onlineUsers.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">
                  Keine Aktivitätsdaten vorhanden
                </p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {onlineUsers.map((activity, index) => (
                    <div 
                      key={index} 
                      className={`p-3 rounded-xl border ${
                        activity.is_online 
                          ? 'border-emerald-500/30 bg-emerald-500/5' 
                          : 'border-border bg-muted/50'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {activity.is_online ? (
                          <Wifi className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <WifiOff className="w-4 h-4 text-muted-foreground" />
                        )}
                        <span className="font-medium text-sm truncate">{activity.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 truncate">
                        {activity.email}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Leaderboard Table */}
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
                    {leaderboard.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                          Keine Daten vorhanden
                        </TableCell>
                      </TableRow>
                    ) : (
                      leaderboard.map((user, index) => (
                        <TableRow key={user.id} data-testid={`leaderboard-row-${index}`}>
                          <TableCell>
                            {index < 3 ? (
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                index === 0 ? 'bg-amber-500/20 text-amber-500' :
                                index === 1 ? 'bg-gray-400/20 text-gray-500' :
                                'bg-orange-500/20 text-orange-500'
                              }`}>
                                <Trophy className="w-4 h-4" />
                              </div>
                            ) : (
                              <span className="text-muted-foreground">{index + 1}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-3">
                              {user.picture ? (
                                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
                              ) : (
                                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                                  <Users className="w-4 h-4 text-primary" />
                                </div>
                              )}
                              <div>
                                <p className="font-medium">{user.name}</p>
                                <p className="text-xs text-muted-foreground">{user.email}</p>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-center font-medium">
                            {user.total_questions}
                          </TableCell>
                          <TableCell className="text-center text-emerald-500 font-medium">
                            {user.correct_answers}
                          </TableCell>
                          <TableCell className="text-center text-red-500 font-medium">
                            {user.wrong_answers}
                          </TableCell>
                          <TableCell className="text-center">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-primary rounded-full" 
                                  style={{ width: `${Math.min(user.accuracy || 0, 100)}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">
                                {Math.round(user.accuracy || 0)}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Export Tab */}
        <TabsContent value="export">
          <div className="glass-card rounded-2xl p-6">
            <h2 className="text-xl font-semibold flex items-center gap-2 mb-6">
              <Download className="w-5 h-5 text-primary" />
              Fragen exportieren
            </h2>
            
            <div className="grid gap-4">
              <p className="text-muted-foreground">
                Exportieren Sie Fragen als PDF zum Drucken oder Teilen.
              </p>
              
              {exportingPDF && exportProgress && (
                <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg" data-testid="export-progress">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  <span className="text-sm text-blue-700 font-medium">{exportProgress}</span>
                </div>
              )}
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Export All */}
                <Button
                  onClick={() => exportQuestionsToPDF()}
                  disabled={exportingPDF}
                  className="h-auto p-4 flex flex-col items-center gap-2"
                  data-testid="export-all-btn"
                >
                  {exportingPDF ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <Download className="w-6 h-6" />
                  )}
                  <span>Alle Fragen exportieren</span>
                  <span className="text-xs opacity-70">
                    {adminStats?.total_questions || 0} Fragen
                  </span>
                </Button>
                
                {/* Export by Specialty with City split */}
                {SPECIALTIES.map(spec => {
                  const total = adminStats?.questions_by_specialty?.[spec.id] || 0;
                  if (total === 0) return null;
                  return (
                    <div key={spec.id} className="border rounded-xl p-4 space-y-2" data-testid={`export-${spec.id}-section`}>
                      <div className="flex items-center gap-2 mb-1">
                        <FileQuestion className="w-4 h-4 text-primary" />
                        <span className="font-medium text-sm">{spec.name}</span>
                        <span className="text-xs text-muted-foreground">({total})</span>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => exportQuestionsToPDF(spec.id)}
                          disabled={exportingPDF}
                          className="text-xs h-8"
                          data-testid={`export-${spec.id}-all`}
                        >
                          Alle
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => exportQuestionsToPDF(spec.id, "vienna")}
                          disabled={exportingPDF}
                          className="text-xs h-8 border-blue-500/30 text-blue-500 hover:bg-blue-500/10"
                          data-testid={`export-${spec.id}-wien`}
                        >
                          Wien
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => exportQuestionsToPDF(spec.id, "innsbruck")}
                          disabled={exportingPDF}
                          className="text-xs h-8 border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
                          data-testid={`export-${spec.id}-innsbruck`}
                        >
                          Innsbruck
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Import Tab */}
        <TabsContent value="import">
          <ImportQuestionsTab token={token} onImportComplete={() => {
            fetchData();
            fetchQuestions();
          }} />
        </TabsContent>

        {/* Duplicates Tab */}
        <TabsContent value="duplicates">
          <div className="glass-card rounded-2xl p-6" data-testid="duplicates-section">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold">Duplikate finden</h2>
                <p className="text-sm text-muted-foreground mt-1">Doppelte Fragen erkennen und entfernen</p>
              </div>
              <div className="flex items-center gap-3">
                <Select value={dupeFilter} onValueChange={(v) => { setDupeFilter(v); }}>
                  <SelectTrigger className="w-48" data-testid="dupe-filter-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Fachgebiete</SelectItem>
                    {SPECIALTIES.map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button onClick={fetchDuplicates} disabled={loadingDupes} className="gap-2" data-testid="scan-dupes-btn">
                  {loadingDupes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                  Scannen
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="default" disabled={merging || loadingDupes} className="gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white" data-testid="smart-merge-btn">
                      {merging ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                      Smart Merge
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Smart Merge ausführen?</AlertDialogTitle>
                      <AlertDialogDescription className="space-y-2">
                        <span className="block">Für jede Duplikat-Gruppe wird automatisch:</span>
                        <span className="block">1. Die vollständigste Frage behalten (mit Erklärung, Bild, Antworten)</span>
                        <span className="block">2. Fehlende Daten aus Kopien in die beste Frage übernommen</span>
                        <span className="block">3. Alle übrigen Kopien gelöscht</span>
                        <span className="block font-medium text-amber-600 mt-2">Dieser Vorgang kann nicht rückgängig gemacht werden.</span>
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                      <AlertDialogAction onClick={smartMergeDupes} className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700">
                        Smart Merge starten
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>

            {loadingDupes && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            )}

            {duplicates && !loadingDupes && (
              <>
                {/* Merge Result */}
                {mergeResult && (
                  <div className="mb-6 p-4 bg-violet-500/10 border border-violet-500/20 rounded-xl" data-testid="merge-result">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-5 h-5 text-violet-600" />
                      <span className="font-semibold text-violet-700">Smart Merge abgeschlossen</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div className="text-center p-2 bg-violet-500/10 rounded-lg">
                        <div className="text-lg font-bold text-violet-600">{mergeResult.merged_groups}</div>
                        <div className="text-xs text-muted-foreground">Gruppen zusammengeführt</div>
                      </div>
                      <div className="text-center p-2 bg-red-500/10 rounded-lg">
                        <div className="text-lg font-bold text-red-600">{mergeResult.deleted_count}</div>
                        <div className="text-xs text-muted-foreground">Kopien gelöscht</div>
                      </div>
                    </div>
                    {mergeResult.details && mergeResult.details.length > 0 && (
                      <details className="text-sm">
                        <summary className="cursor-pointer text-violet-600 hover:underline">Details anzeigen ({mergeResult.details.length} Gruppen)</summary>
                        <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
                          {mergeResult.details.map((d, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs p-1.5 bg-background rounded">
                              <span className="text-red-500 font-mono">-{d.deleted_count}</span>
                              <span className="truncate flex-1">{d.text_preview}</span>
                              {d.merged_fields.length > 0 && (
                                <span className="px-1.5 py-0.5 bg-green-500/10 text-green-600 rounded text-[10px] whitespace-nowrap">
                                  +{d.merged_fields.join(", ")}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                )}

                {/* Summary */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-center">
                    <div className="text-2xl font-bold text-amber-600">{duplicates.total_duplicate_groups}</div>
                    <div className="text-sm text-muted-foreground">Duplikat-Gruppen</div>
                  </div>
                  <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-center">
                    <div className="text-2xl font-bold text-red-600">{duplicates.total_extra_copies}</div>
                    <div className="text-sm text-muted-foreground">Zusätzliche Kopien</div>
                  </div>
                </div>

                {duplicates.total_duplicate_groups > 0 && (
                  <>
                    {/* Action Bar */}
                    <div className="flex items-center justify-between mb-4 p-3 bg-muted/50 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Button variant="outline" size="sm" onClick={autoSelectDupes} className="gap-2" data-testid="auto-select-dupes-btn">
                          <span className={`w-4 h-4 rounded border-2 inline-flex items-center justify-center ${selectedDupes.length > 0 ? "bg-primary border-primary text-white" : "border-muted-foreground"}`}>
                            {selectedDupes.length > 0 && <span className="text-xs">✓</span>}
                          </span>
                          Kopien automatisch markieren
                        </Button>
                        <span className="text-sm text-muted-foreground">
                          {selectedDupes.length > 0 ? `${selectedDupes.length} markiert` : "Behält jeweils die erste Frage"}
                        </span>
                      </div>
                      {selectedDupes.length > 0 && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="destructive" size="sm" className="gap-2" disabled={bulkDeleting} data-testid="delete-dupes-btn">
                              {bulkDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                              {selectedDupes.length} Duplikate löschen
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>{selectedDupes.length} Duplikate löschen</AlertDialogTitle>
                              <AlertDialogDescription>
                                Sind Sie sicher? Die markierten Kopien werden gelöscht. Die erste Frage jeder Gruppe bleibt erhalten.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                              <AlertDialogAction onClick={bulkDeleteDupes} className="bg-red-500 hover:bg-red-600">
                                Löschen
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                    </div>

                    {/* Duplicate Groups */}
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                      {duplicates.groups.map((group, gi) => {
                        const isExpanded = expandedGroup === gi;
                        return (
                        <div key={gi} className="border rounded-xl overflow-hidden" data-testid={`dupe-group-${gi}`}>
                          {/* Group Header - clickable to expand */}
                          <button
                            onClick={() => setExpandedGroup(isExpanded ? null : gi)}
                            className="w-full flex items-center gap-2 p-4 hover:bg-muted/30 transition-colors text-left"
                            data-testid={`dupe-group-toggle-${gi}`}
                          >
                            <span className={`transition-transform ${isExpanded ? "rotate-90" : ""}`}>&#9654;</span>
                            <span className="px-2 py-0.5 bg-amber-500/10 text-amber-600 rounded text-xs font-medium">
                              {group.count}x
                            </span>
                            <span className="text-sm font-medium truncate flex-1">{group._id?.substring(0, 120) || "Kein Text"}</span>
                          </button>

                          {/* Expanded Review */}
                          {isExpanded && (
                            <div className="border-t p-4 space-y-3 bg-muted/10">
                              {group.questions.map((q, qi) => {
                                const isFirst = qi === 0;
                                const isSelected = selectedDupes.includes(q.id);
                                const choicesArr = (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []);
                                return (
                                  <div
                                    key={q.id}
                                    className={`p-4 rounded-xl border-2 ${
                                      isFirst ? "border-green-500/30 bg-green-500/5" : isSelected ? "border-red-500/30 bg-red-500/5" : "border-border bg-background"
                                    }`}
                                    data-testid={`dupe-item-${gi}-${qi}`}
                                  >
                                    {/* Header */}
                                    <div className="flex items-center gap-3 mb-3">
                                      {isFirst ? (
                                        <span className="px-2 py-0.5 bg-green-500/10 text-green-600 rounded text-xs font-semibold whitespace-nowrap">Original</span>
                                      ) : (
                                        <Checkbox
                                          checked={isSelected}
                                          onCheckedChange={() => setSelectedDupes(prev => prev.includes(q.id) ? prev.filter(id => id !== q.id) : [...prev, q.id])}
                                          data-testid={`dupe-check-${gi}-${qi}`}
                                        />
                                      )}
                                      <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">{q.specialty_id}</span>
                                      <span className="text-xs text-muted-foreground">{q.year || "—"}</span>
                                      <span className="text-xs text-muted-foreground">{q.exam_location || "—"}</span>
                                      <span className="text-xs text-muted-foreground font-mono ml-auto">{q.id?.substring(0, 12)}...</span>
                                    </div>

                                    {/* Full Question Text */}
                                    <p className="text-sm font-medium mb-3">{q.question_text_de || q.question_text || "Kein Text"}</p>

                                    {/* Choices */}
                                    {choicesArr.length > 0 && (
                                      <div className="space-y-1.5 mb-2">
                                        {choicesArr.map((c, ci) => (
                                          <div
                                            key={ci}
                                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${
                                              c.is_correct ? "bg-green-500/10 border border-green-500/20" : "bg-muted/50"
                                            }`}
                                          >
                                            <span className="font-bold">{String.fromCharCode(65 + ci)}.</span>
                                            <span className="flex-1">{c.text_de || c.text || ""}</span>
                                            {c.is_correct && <span className="text-green-600 font-bold">&#10003;</span>}
                                          </div>
                                        ))}
                                      </div>
                                    )}

                                    {/* Correct Answers */}
                                    {q.correct_answers && q.correct_answers.length > 0 && choicesArr.length === 0 && (
                                      <div className="text-xs text-muted-foreground">
                                        Richtig: {q.correct_answers.join(", ")}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                        );
                      })}
                    </div>
                  </>
                )}

                {duplicates.total_duplicate_groups === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    <Copy className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="font-medium">Keine Duplikate gefunden!</p>
                    <p className="text-sm">Alle Fragen sind einzigartig.</p>
                  </div>
                )}
              </>
            )}

            {!duplicates && !loadingDupes && (
              <div className="text-center py-12 text-muted-foreground">
                <Copy className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Klicken Sie auf "Scannen" um Duplikate zu finden</p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports">
          <AdminReportsTab token={token} />
        </TabsContent>

        {/* Tags Tab */}
        <TabsContent value="tags">
          <AdminTagsTab token={token} />
        </TabsContent>

        {/* Daily Podcast Tab */}
        <TabsContent value="podcast">
          <AdminPodcastTab token={token} />
        </TabsContent>

        {/* RAG Knowledge Base Tab */}
        {process.env.REACT_APP_ADVANCED === "true" && (
          <TabsContent value="rag">
            <AdminRagTab token={token} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
