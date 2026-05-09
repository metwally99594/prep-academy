import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth, useTheme, API } from "@/App";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Stethoscope,
  User,
  LogOut,
  Heart,
  BarChart3,
  Settings,
  Menu,
  X,
  Search,
  Loader2,
  RefreshCcw,
  Edit,
  Save,
  LayoutDashboard,
  Trash2,
  ImageOff,
  Trophy,
  FileText,
  SlidersHorizontal,
  Activity,
  Crown,
  Headphones,
  Sun,
  Moon,
  Brain,
  BookOpen,
  ShieldCheck,
  FileScan,
  Lock,
  GraduationCap,
} from "lucide-react";
import { useState } from "react";
import axios from "axios";
import NotificationBell from "@/components/NotificationBell";
import TrialBanner from "@/components/TrialBanner";

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

// ── Locked feature modal ──────────────────────────────────────────
const FEATURE_KEY_MAP = {
  "PDF Notebook": "notebook",
  "Medical Analyzer": "analyzer",
  "Daily Podcast": "podcast",
};

function LockedFeatureModal({ feature, onClose, token }) {
  const [phase, setPhase] = useState("info"); // "info" | "form" | "sent"
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    const featureKey = FEATURE_KEY_MAP[feature] || feature.toLowerCase();
    setSending(true);
    try {
      await axios.post(`${API}/access-requests`,
        { feature: featureKey, user_message: msg },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPhase("sent");
    } catch (err) {
      const detail = err.response?.data?.detail || "Fehler beim Senden";
      if (detail.includes("ausstehende Anfrage")) {
        setPhase("sent");
      } else {
        toast.error(detail);
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative max-w-sm w-full rounded-2xl border p-6 shadow-2xl"
        style={{ background: '#0c1229', borderColor: 'rgba(201,168,76,0.2)' }}
        onClick={e => e.stopPropagation()}>

        {phase === "sent" ? (
          <div className="text-center">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)' }}>
              <ShieldCheck size={26} className="text-emerald-500" />
            </div>
            <h3 className="text-lg font-bold mb-2">Anfrage gesendet</h3>
            <p className="text-sm text-muted-foreground mb-5">
              Der Administrator wurde benachrichtigt und wird Ihre Anfrage für <strong className="text-foreground">{feature}</strong> bearbeiten.
            </p>
            <button onClick={onClose} className="w-full py-2.5 rounded-xl text-sm font-semibold"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
              Schließen
            </button>
          </div>
        ) : phase === "form" ? (
          <>
            <h3 className="text-lg font-bold mb-1">Zugang anfragen</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Senden Sie eine Anfrage für <strong className="text-foreground">{feature}</strong>.
            </p>
            <textarea
              className="w-full rounded-xl border bg-background/50 p-3 text-sm resize-none mb-4 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
              rows={3}
              placeholder="Optional: Warum benötigen Sie diesen Zugang?"
              value={msg}
              onChange={e => setMsg(e.target.value)}
              maxLength={500}
            />
            <button onClick={submit} disabled={sending}
              className="w-full py-2.5 rounded-xl text-sm font-semibold mb-2 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
              {sending ? "Wird gesendet…" : "Anfrage senden"}
            </button>
            <button onClick={() => setPhase("info")}
              className="w-full py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground transition-colors">
              Zurück
            </button>
          </>
        ) : (
          <div className="text-center">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.15)' }}>
              <Lock size={26} style={{ color: '#c9a84c' }} />
            </div>
            <h3 className="text-lg font-bold mb-2">Funktion gesperrt</h3>
            <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
              <strong className="text-foreground">{feature}</strong> ist nur für freigeschaltete Nutzer verfügbar.
            </p>
            <button onClick={() => setPhase("form")}
              className="w-full py-2.5 rounded-xl text-sm font-semibold mb-2"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
              Zugang anfragen
            </button>
            <button onClick={onClose}
              className="w-full py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground transition-colors">
              Schließen
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export const Layout = () => {
  const { user, token, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [lockedModal, setLockedModal] = useState(null); // feature name string or null
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [editFormData, setEditFormData] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    
    setSearching(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await axios.get(`${API}/questions/search/text?q=${encodeURIComponent(query)}&limit=20`, { headers });
      setSearchResults(response.data);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setSearching(false);
    }
  };

  const handleQuestionClick = (question) => {
    setSearchOpen(false);
    setSearchQuery("");
    setSearchResults([]);
    navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
  };

  const handleEditQuestion = (question) => {
    setEditingQuestion(question);
    setEditFormData({
      ...question,
      specialty_id: question.specialty_id || "",
      year: question.year || new Date().getFullYear(),
      exam_location: question.exam_location || "vienna",
      question_text_de: question.question_text_de || question.question_text || "",
      choices: (Array.isArray(question.choices) && question.choices.length > 0)
        ? question.choices
        : (Array.isArray(question.choices_de) ? question.choices_de : []),
      explanation_de: question.explanation_de || question.explanation || "",
    });
  };

  const handleSaveQuestion = async () => {
    if (!editFormData || !editingQuestion) return;
    
    setSaving(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.put(`${API}/questions/${editingQuestion.id}`, editFormData, { headers });
      toast.success("Frage erfolgreich aktualisiert!");
      setEditingQuestion(null);
      setEditFormData(null);
      // Refresh search results
      handleSearch(searchQuery);
    } catch (error) {
      console.error("Failed to save question:", error);
      toast.error("Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteQuestion = async () => {
    if (!editingQuestion) return;
    if (!window.confirm("Frage wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.")) return;
    
    setSaving(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/questions/${editingQuestion.id}`, { headers });
      toast.success("Frage gelöscht!");
      setEditingQuestion(null);
      setEditFormData(null);
      handleSearch(searchQuery);
    } catch (error) {
      console.error("Failed to delete question:", error);
      toast.error("Fehler beim Löschen");
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveImage = () => {
    setEditFormData(prev => ({ ...prev, image_base64: null }));
  };

  const updateChoice = (index, field, value) => {
    const newChoices = [...editFormData.choices];
    newChoices[index] = { ...newChoices[index], [field]: value };
    setEditFormData({ ...editFormData, choices: newChoices });
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.length >= 2) {
      setSearchOpen(false);
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchQuery("");
      setSearchResults([]);
    }
  };

  return (
    <div className="app-container min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-background/90 backdrop-blur-2xl border-b border-border/30" style={{ borderImage: 'linear-gradient(90deg, transparent, hsl(42 65% 52% / 0.15), transparent) 1' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group flex-shrink-0" data-testid="logo-link">
              <div className="w-12 h-12 rounded-lg overflow-hidden border border-[#c9a84c]/30 flex-shrink-0">
                <img src="/logo-elite.png" alt="Prep Academy" className="w-full h-full object-cover" />
              </div>
              <span className="text-base font-semibold hidden lg:block whitespace-nowrap">Prep Academy</span>
            </Link>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-0.5 overflow-x-auto scrollbar-none">
              {/* Search Button */}
              <Button 
                variant="ghost" 
                size="sm" 
                className="gap-1.5 px-2.5 flex-shrink-0" 
                onClick={() => setSearchOpen(true)}
                data-testid="search-nav-btn"
              >
                <Search className="w-4 h-4" />
                <span className="hidden xl:inline">Suchen</span>
              </Button>
              
              {user && (
                <>
                  <Link to="/dashboard">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="dashboard-nav-btn">
                      <LayoutDashboard className="w-4 h-4" />
                      <span className="hidden lg:inline">Dashboard</span>
                    </Button>
                  </Link>
                  <Link to="/custom-quiz">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="custom-quiz-nav-btn">
                      <SlidersHorizontal className="w-4 h-4" />
                      <span className="hidden xl:inline">Eigene Auswahl</span>
                    </Button>
                  </Link>
                  {user.analyzer_enabled || user.is_admin ? (
                    <Link to="/analyzer">
                      <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="analyzer-nav-btn">
                        <Activity className="w-4 h-4" />
                        <span className="hidden lg:inline">Analyzer</span>
                      </Button>
                    </Link>
                  ) : (
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0 opacity-50" data-testid="analyzer-nav-btn"
                      onClick={() => setLockedModal("Analyzer")}>
                      <Activity className="w-4 h-4" />
                      <span className="hidden lg:inline">Analyzer</span>
                      <Lock className="w-3 h-3 opacity-60" />
                    </Button>
                  )}
                  {process.env.REACT_APP_ADVANCED === "true" && (
                    <>
                      <Link to="/rag">
                        <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="rag-nav-btn">
                          <ShieldCheck className="w-4 h-4 text-amber-500" />
                          <span className="hidden lg:inline">RAG</span>
                        </Button>
                      </Link>
                      <Link to="/dicom">
                        <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="dicom-nav-btn">
                          <FileScan className="w-4 h-4 text-amber-500" />
                          <span className="hidden lg:inline">DICOM</span>
                        </Button>
                      </Link>
                    </>
                  )}
                  {user.podcast_enabled || user.is_admin ? (
                    <Link to="/podcast">
                      <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="podcast-nav-btn">
                        <Headphones className="w-4 h-4" />
                        <span className="hidden lg:inline">Daily</span>
                      </Button>
                    </Link>
                  ) : (
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0 opacity-50" data-testid="podcast-nav-btn"
                      onClick={() => setLockedModal("Daily Podcast")}>
                      <Headphones className="w-4 h-4" />
                      <span className="hidden lg:inline">Daily</span>
                      <Lock className="w-3 h-3 opacity-60" />
                    </Button>
                  )}
                  <Link to="/favorites">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="favorites-nav-btn">
                      <Heart className="w-4 h-4" />
                      <span className="hidden lg:inline">Favoriten</span>
                    </Button>
                  </Link>
                  <Link to="/my-notes">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="notes-nav-btn">
                      <FileText className="w-4 h-4" />
                      <span className="hidden xl:inline">Notizen</span>
                    </Button>
                  </Link>
                  <Link to="/review">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="review-nav-btn">
                      <RefreshCcw className="w-4 h-4" />
                      <span className="hidden xl:inline">Überprüfung</span>
                    </Button>
                  </Link>
                  <Link to="/stats">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="stats-nav-btn">
                      <BarChart3 className="w-4 h-4" />
                      <span className="hidden lg:inline">Statistik</span>
                    </Button>
                  </Link>
                  <Link to="/leaderboard">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="leaderboard-nav-btn">
                      <Trophy className="w-4 h-4" />
                      <span className="hidden xl:inline">Rangliste</span>
                    </Button>
                  </Link>
                  {user.notebook_enabled || user.is_admin ? (
                    <Link to="/notebook">
                      <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="notebook-nav-btn">
                        <FileText className="w-4 h-4" />
                        <span className="hidden lg:inline">Notebook</span>
                      </Button>
                    </Link>
                  ) : (
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0 opacity-50" data-testid="notebook-nav-btn"
                      onClick={() => setLockedModal("PDF Notebook")}>
                      <FileText className="w-4 h-4" />
                      <span className="hidden lg:inline">Notebook</span>
                      <Lock className="w-3 h-3 opacity-60" />
                    </Button>
                  )}
                  <Link to="/blog">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="blog-nav-btn">
                      <BookOpen className="w-4 h-4" />
                      <span className="hidden lg:inline">Blog</span>
                    </Button>
                  </Link>
                  <Link to="/lerntools">
                    <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="lerntools-nav-btn">
                      <Brain className="w-4 h-4" />
                      <span className="hidden lg:inline">Lerntools</span>
                    </Button>
                  </Link>
                  {user.is_admin && (
                    <Link to="/admin">
                      <Button variant="ghost" size="sm" className="gap-1.5 px-2.5 flex-shrink-0" data-testid="admin-nav-btn">
                        <Settings className="w-4 h-4" />
                        <span className="hidden lg:inline">Admin</span>
                      </Button>
                    </Link>
                  )}
                </>
              )}
            </nav>

            {/* User Menu */}
            <div className="flex items-center gap-1">
              {/* Dark Mode Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="hidden md:inline-flex w-9 h-9"
                data-testid="theme-toggle"
              >
                {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>
              {user && <NotificationBell />}
              {user ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="gap-2" data-testid="user-menu-trigger">
                      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                      </div>
                      <span className="hidden sm:block">{user.name}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem className="gap-2" data-testid="profile-menu-item">
                      <User className="w-4 h-4" />
                      {user.email}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout} className="gap-2 text-destructive" data-testid="logout-menu-item">
                      <LogOut className="w-4 h-4" />
                      Abmelden
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <div className="flex gap-2">
                  <Link to="/login" className="hidden sm:block">
                    <Button variant="ghost" size="sm" data-testid="login-btn">
                      Anmelden
                    </Button>
                  </Link>
                  <Link to="/register">
                    <Button size="sm" data-testid="register-btn">
                      Registrieren
                    </Button>
                  </Link>
                </div>
              )}

              {/* Mobile Menu Toggle */}
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-toggle"
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && !user && (
          <div className="md:hidden border-t border-border/50 py-4 px-4 space-y-2">
            <Button
              variant="ghost"
              className="w-full justify-start gap-2"
              onClick={toggleTheme}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              Darstellung wechseln
            </Button>
            <Link to="/guest-quiz" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <GraduationCap className="w-4 h-4" />
                Kostenlos testen
              </Button>
            </Link>
            <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <User className="w-4 h-4" />
                Anmelden
              </Button>
            </Link>
          </div>
        )}

        {mobileMenuOpen && user && (
          <div className="md:hidden border-t border-border/50 py-4 px-4 space-y-2">
            <Button
              variant="ghost"
              className="w-full justify-start gap-2"
              onClick={toggleTheme}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              Darstellung wechseln
            </Button>
            <Button 
              variant="ghost" 
              className="w-full justify-start gap-2"
              onClick={() => { setSearchOpen(true); setMobileMenuOpen(false); }}
            >
              <Search className="w-4 h-4" />
              Suchen
            </Button>
            <Link to="/favorites" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <Heart className="w-4 h-4" />
                Favoriten
              </Button>
            </Link>
            <Link to="/my-notes" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <FileText className="w-4 h-4" />
                Meine Notizen
              </Button>
            </Link>
            <Link to="/custom-quiz" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <SlidersHorizontal className="w-4 h-4" />
                Eigene Auswahl
              </Button>
            </Link>
            {user.analyzer_enabled || user.is_admin ? (
              <Link to="/analyzer" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <Activity className="w-4 h-4" />
                  Analyzer
                </Button>
              </Link>
            ) : (
              <Button variant="ghost" className="w-full justify-start gap-2 opacity-50"
                onClick={() => { setMobileMenuOpen(false); setLockedModal("Analyzer"); }}>
                <Activity className="w-4 h-4" />
                Analyzer
                <Lock className="w-3 h-3 ml-auto opacity-60" />
              </Button>
            )}
            {process.env.REACT_APP_ADVANCED === "true" && (
              <>
                <Link to="/rag" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="ghost" className="w-full justify-start gap-2" data-testid="rag-nav-mobile">
                    <ShieldCheck className="w-4 h-4 text-amber-500" />
                    Medical RAG
                  </Button>
                </Link>
                <Link to="/dicom" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="ghost" className="w-full justify-start gap-2" data-testid="dicom-nav-mobile">
                    <FileScan className="w-4 h-4 text-amber-500" />
                    DICOM Imaging
                  </Button>
                </Link>
              </>
            )}
            <Link to="/review" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <RefreshCcw className="w-4 h-4" />
                Überprüfung
              </Button>
            </Link>
            <Link to="/stats" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <BarChart3 className="w-4 h-4" />
                Statistik
              </Button>
            </Link>
            <Link to="/leaderboard" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <Trophy className="w-4 h-4" />
                Rangliste
              </Button>
            </Link>
            {user.notebook_enabled || user.is_admin ? (
              <Link to="/notebook" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <FileText className="w-4 h-4" />
                  Notebook
                </Button>
              </Link>
            ) : (
              <Button variant="ghost" className="w-full justify-start gap-2 opacity-50"
                onClick={() => { setMobileMenuOpen(false); setLockedModal("PDF Notebook"); }}>
                <FileText className="w-4 h-4" />
                Notebook
                <Lock className="w-3 h-3 ml-auto opacity-60" />
              </Button>
            )}
            <Link to="/blog" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="ghost" className="w-full justify-start gap-2">
                <BookOpen className="w-4 h-4" />
                Blog
              </Button>
            </Link>
            {user.is_admin && (
              <Link to="/admin" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <Settings className="w-4 h-4" />
                  Admin
                </Button>
              </Link>
            )}
          </div>
        )}
      </header>

      {/* Search Dialog */}
      <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search className="w-5 h-5" />
              Fragen suchen
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSearchSubmit} className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Suchbegriff, Jahr, Fachgebiet oder Stadt..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
                autoFocus
                data-testid="search-input"
              />
            </div>
            
            {searchQuery.length >= 2 && (
              <Button 
                type="submit" 
                className="w-full gap-2"
                data-testid="search-submit-btn"
              >
                <Search className="w-4 h-4" />
                Alle {searchResults.length} Ergebnisse anzeigen
              </Button>
            )}
            
            {searching && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            )}
            
            {!searching && searchQuery.length >= 2 && searchResults.length === 0 && (
              <div className="text-center py-4 text-muted-foreground">
                Keine Ergebnisse gefunden
              </div>
            )}
            
            {!searching && searchResults.length > 0 && (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                <p className="text-sm text-muted-foreground mb-2">Vorschau (erste {searchResults.length} Ergebnisse):</p>
                {searchResults.map((question, index) => (
                  <div
                    key={question.id}
                    className="p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                    data-testid={`search-result-${index}`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded font-medium">
                          {question.year}
                        </span>
                        <span className="px-2 py-0.5 bg-muted text-muted-foreground text-xs rounded">
                          {question.specialty_id}
                        </span>
                        {question.exam_location && (
                          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-xs rounded">
                            {question.exam_location === "vienna" ? "Wien" : "Innsbruck"}
                          </span>
                        )}
                      </div>
                      {user?.is_admin && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditQuestion(question);
                          }}
                          className="text-primary hover:text-primary/80 gap-1"
                          data-testid={`edit-question-${index}`}
                        >
                          <Edit className="w-4 h-4" />
                          Bearbeiten
                        </Button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleQuestionClick(question)}
                      className="w-full text-left"
                    >
                      <p className="text-sm line-clamp-2">
                        {question.question_text_de || question.question_text}
                      </p>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Question Dialog (Admin Only) */}
      <Dialog open={!!editingQuestion} onOpenChange={(open) => !open && setEditingQuestion(null)}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="w-5 h-5" />
              Frage bearbeiten
            </DialogTitle>
          </DialogHeader>
          
          {editFormData && (
            <div className="space-y-4">
              {/* Specialty, Year, City */}
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">Fachgebiet</Label>
                  <Select 
                    value={editFormData.specialty_id} 
                    onValueChange={(v) => setEditFormData({ ...editFormData, specialty_id: v })}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SPECIALTIES.map(spec => (
                        <SelectItem key={spec.id} value={spec.id}>{spec.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Jahr</Label>
                  <Input
                    type="number"
                    value={editFormData.year}
                    onChange={(e) => setEditFormData({ ...editFormData, year: parseInt(e.target.value) })}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Stadt</Label>
                  <Select 
                    value={editFormData.exam_location || "vienna"} 
                    onValueChange={(v) => setEditFormData({ ...editFormData, exam_location: v })}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vienna">Wien</SelectItem>
                      <SelectItem value="innsbruck">Innsbruck</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Question Text */}
              <div className="space-y-1">
                <Label className="text-xs">Fragetext</Label>
                <Textarea
                  value={editFormData.question_text_de}
                  onChange={(e) => setEditFormData({ ...editFormData, question_text_de: e.target.value, question_text: e.target.value })}
                  rows={3}
                  className="text-sm"
                />
              </div>

              {/* Choices */}
              <div className="space-y-2">
                <Label className="text-xs">Antworten</Label>
                {editFormData.choices.map((choice, index) => (
                  <div key={choice.id} className="flex items-center gap-2">
                    <span className="text-xs font-medium w-6">{String.fromCharCode(65 + index)}.</span>
                    <Input
                      value={choice.text_de || choice.text || ""}
                      onChange={(e) => updateChoice(index, "text_de", e.target.value)}
                      className="flex-1 h-8 text-sm"
                      placeholder={`Antwort ${String.fromCharCode(65 + index)}`}
                    />
                    <div className="flex items-center gap-1">
                      <Checkbox
                        checked={choice.is_correct || false}
                        onCheckedChange={(checked) => updateChoice(index, "is_correct", checked)}
                      />
                      <span className="text-xs text-muted-foreground">Richtig</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Explanation */}
              <div className="space-y-1">
                <Label className="text-xs">Erklärung (optional)</Label>
                <Textarea
                  value={editFormData.explanation_de || ""}
                  onChange={(e) => setEditFormData({ ...editFormData, explanation_de: e.target.value, explanation: e.target.value })}
                  rows={2}
                  className="text-sm"
                />
              </div>

              {/* Image */}
              <div className="space-y-1">
                <Label className="text-xs">Bild</Label>
                {editFormData.image_base64 ? (
                  <div className="relative inline-block">
                    <img 
                      src={editFormData.image_base64} 
                      alt="Question" 
                      className="max-h-32 rounded-lg border"
                    />
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={handleRemoveImage}
                      className="absolute -top-2 -right-2 h-7 w-7 p-0 rounded-full"
                      data-testid="remove-image-btn"
                    >
                      <ImageOff className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-primary/30 rounded-xl cursor-pointer hover:border-primary/60 hover:bg-primary/5 transition-all" data-testid="upload-image-label">
                    <ImageOff className="w-5 h-5 text-primary/40 mb-1" />
                    <span className="text-xs text-primary/60">Bild hochladen</span>
                    <input type="file" accept="image/*" className="hidden" data-testid="upload-image-input" onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (!f) return;
                      if (f.size > 5 * 1024 * 1024) { toast.error("Bild zu groß (max 5MB)"); return; }
                      const reader = new FileReader();
                      reader.onload = (ev) => setEditFormData(prev => ({ ...prev, image_base64: ev.target.result }));
                      reader.readAsDataURL(f);
                    }} />
                  </label>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex justify-between pt-2">
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDeleteQuestion}
                  disabled={saving}
                  className="gap-2"
                  data-testid="delete-question-btn"
                >
                  <Trash2 className="w-4 h-4" />
                  Löschen
                </Button>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setEditingQuestion(null)}
                  >
                    Abbrechen
                  </Button>
                  <Button
                    type="button"
                    onClick={handleSaveQuestion}
                    disabled={saving}
                    className="gap-2"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Speichern
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Locked feature modal */}
      {lockedModal && <LockedFeatureModal feature={lockedModal} onClose={() => setLockedModal(null)} token={token} />}

      {/* Trial banner */}
      <TrialBanner />

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="py-8 mt-auto" style={{ borderTop: '1px solid transparent', borderImage: 'linear-gradient(90deg, transparent, hsl(42 65% 52% / 0.15), transparent) 1' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © 2026 Mohamed Metwally — Medizinische Prüfungsvorbereitung
            </p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground/60">
              <Link to="/impressum" className="hover:text-muted-foreground transition-colors">Impressum</Link>
              <Link to="/datenschutz" className="hover:text-muted-foreground transition-colors">Datenschutz</Link>
              <Link to="/agb" className="hover:text-muted-foreground transition-colors">AGB</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
