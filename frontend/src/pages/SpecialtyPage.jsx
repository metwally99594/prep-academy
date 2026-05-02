import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  ArrowLeft, 
  BookOpen, 
  Calendar,
  Play,
  Scissors, 
  Heart, 
  Baby, 
  Ambulance, 
  Eye, 
  Fingerprint, 
  Ear, 
  HeartPulse, 
  Brain,
  Star,
  Activity,
  MapPin,
  Clock,
  GraduationCap
} from "lucide-react";

const iconMap = {
  Scissors: Scissors,
  Heart: Heart,
  Baby: Baby,
  Ambulance: Ambulance,
  Eye: Eye,
  Fingerprint: Fingerprint,
  Ear: Ear,
  HeartPulse: HeartPulse,
  Brain: Brain,
  Star: Star,
  Activity: Activity,
};

export default function SpecialtyPage() {
  const { specialtyId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  
  const [specialty, setSpecialty] = useState(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [years, setYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState("all");
  const [selectedCity, setSelectedCity] = useState("all");
  const [quizMode, setQuizMode] = useState("study"); // study or exam
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        
        // Load specialty info and years in parallel
        const [specRes, yearsRes] = await Promise.all([
          axios.get(`${API}/specialties/${specialtyId}`, { headers }),
          axios.get(`${API}/questions/years/list?specialty_id=${specialtyId}`, { headers }),
        ]);
        setSpecialty(specRes.data);
        setQuestionCount(specRes.data.question_count || 0);
        setYears(yearsRes.data);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [specialtyId, token]);

  useEffect(() => {
    const updateCount = async () => {
      if (!token) return;
      if (selectedYear === "all" && selectedCity === "all") return;
      try {
        const headers = { Authorization: `Bearer ${token}` };
        let params = `specialty_id=${specialtyId}`;
        if (selectedYear !== "all") params += `&year=${selectedYear}`;
        if (selectedCity !== "all") params += `&exam_location=${selectedCity}`;
        
        const res = await axios.get(`${API}/questions/count?${params}`, { headers });
        setQuestionCount(res.data.count);
      } catch (error) {
        console.error("Failed to update count:", error);
      }
    };
    updateCount();
  }, [selectedYear, selectedCity, specialtyId, token]);

  const startQuiz = () => {
    let params = [];
    params.push(`mode=${quizMode}`);
    if (selectedYear !== "all") params.push(`year=${selectedYear}`);
    if (selectedCity !== "all") params.push(`exam_location=${selectedCity}`);
    const queryString = params.length > 0 ? `?${params.join("&")}` : "";
    navigate(`/quiz/${specialtyId}${queryString}`);
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-8">
          <div className="h-8 w-48 bg-muted rounded" />
          <div className="h-32 bg-muted rounded-2xl" />
          <div className="grid gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const IconComponent = specialty ? iconMap[specialty.icon] || BookOpen : BookOpen;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Back Button */}
      <Link to="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Zurück zur Startseite
      </Link>

      {/* Specialty Header */}
      {specialty && (
        <div className="glass-card rounded-2xl p-8 mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="p-4 rounded-2xl bg-primary/10">
                <IconComponent className="w-10 h-10 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-bold mb-1" data-testid="specialty-title">{specialty.name_de}</h1>
                <p className="text-muted-foreground">{specialty.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center px-6 py-3 bg-background/50 rounded-xl">
                <div className="text-2xl font-bold text-primary" data-testid="question-count">{questionCount}</div>
                <div className="text-sm text-muted-foreground">Fragen verfügbar</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quiz Mode Selection */}
      <div className="glass-card rounded-2xl p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Modus wählen</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Study Mode */}
          <button
            onClick={() => setQuizMode("study")}
            className={`p-4 rounded-xl border-2 transition-all text-left ${
              quizMode === "study" 
                ? "border-primary bg-primary/5" 
                : "border-border hover:border-primary/50"
            }`}
            data-testid="study-mode-btn"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className={`p-2 rounded-lg ${quizMode === "study" ? "bg-primary/20" : "bg-muted"}`}>
                <BookOpen className={`w-5 h-5 ${quizMode === "study" ? "text-primary" : "text-muted-foreground"}`} />
              </div>
              <span className="font-semibold">Study Mode</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Lerne in deinem eigenen Tempo ohne Zeitdruck. Ideal zum Üben und Verstehen.
            </p>
          </button>

          {/* Exam Mode */}
          <button
            onClick={() => setQuizMode("exam")}
            className={`p-4 rounded-xl border-2 transition-all text-left ${
              quizMode === "exam" 
                ? "border-primary bg-primary/5" 
                : "border-border hover:border-primary/50"
            }`}
            data-testid="exam-mode-btn"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className={`p-2 rounded-lg ${quizMode === "exam" ? "bg-primary/20" : "bg-muted"}`}>
                <Clock className={`w-5 h-5 ${quizMode === "exam" ? "text-primary" : "text-muted-foreground"}`} />
              </div>
              <span className="font-semibold">Exam Mode</span>
            </div>
            <p className="text-sm text-muted-foreground">
              50 Fragen mit 1 Minute pro Frage. Simuliere echte Prüfungsbedingungen.
            </p>
          </button>
        </div>
      </div>

      {/* Filters & Start */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div className="flex flex-wrap items-center gap-4">
          {/* Year Filter */}
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Jahr:</span>
          </div>
          <Select value={selectedYear} onValueChange={setSelectedYear}>
            <SelectTrigger className="w-32" data-testid="year-filter">
              <SelectValue placeholder="Alle Jahre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle Jahre</SelectItem>
              {years.map((year) => (
                <SelectItem key={year} value={year.toString()}>
                  {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* City Filter */}
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Stadt:</span>
          </div>
          <Select value={selectedCity} onValueChange={setSelectedCity}>
            <SelectTrigger className="w-36" data-testid="city-filter">
              <SelectValue placeholder="Alle Städte" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle Städte</SelectItem>
              <SelectItem value="vienna">Wien</SelectItem>
              <SelectItem value="innsbruck">Innsbruck</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button 
          onClick={startQuiz} 
          size="lg" 
          className="gap-2"
          disabled={questionCount === 0}
          data-testid="start-quiz-btn"
        >
          <Play className="w-5 h-5" />
          Quiz starten
        </Button>
      </div>

      {/* Info Section */}
      <div className="glass-card rounded-2xl p-6 text-center">
        <p className="text-muted-foreground">
          {questionCount > 0 
            ? `${questionCount} Fragen verfügbar. Wählen Sie einen Modus und starten Sie das Quiz.`
            : "Für dieses Fachgebiet wurden noch keine Fragen hinzugefügt."
          }
        </p>
      </div>
    </div>
  );
}
