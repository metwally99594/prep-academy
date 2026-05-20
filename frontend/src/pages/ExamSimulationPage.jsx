import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import {
  Clock,
  Trophy,
  BookOpen,
  Play,
  ChevronLeft,
  ChevronRight,
  Flag,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  RotateCcw,
  Home,
  MapPin,
  Grid3X3,
  ListChecks,
  X,
} from "lucide-react";

// Exam structure - Austrian medical exam format
const EXAM_STRUCTURE = [
  { id: "internal", name: "Innere Medizin", questions: 30 },
  { id: "surgery", name: "Chirurgie", questions: 30 },
  { id: "pediatrics", name: "Pädiatrie", questions: 30 },
  { id: "neurology", name: "Neurologie", questions: 25 },
  { id: "dermatology", name: "Dermatologie", questions: 25 },
  { id: "obgyn", name: "Gynäkologie", questions: 25 },
  { id: "emergency", name: "Notfallmedizin", questions: 25 },
  { id: "ent", name: "HNO", questions: 20 },
  { id: "psychiatry", name: "Psychiatrie", questions: 20 },
  { id: "ophthalmology", name: "Augenheilkunde", questions: 20 },
];

const TOTAL_QUESTIONS = 250;
const EXAM_TIME_MINUTES = 240; // 4 hours
const PASS_PERCENTAGE = 60;

const CITIES = [
  { id: "vienna", name: "Wien", icon: "🏛️" },
  { id: "innsbruck", name: "Innsbruck", icon: "🏔️" },
];

export default function ExamSimulationPage() {
  const navigate = useNavigate();
  const { token } = useAuth();
  
  // Exam states
  const [stage, setStage] = useState("intro"); // intro, exam, results
  const [selectedCity, setSelectedCity] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // { questionId: [selectedChoiceIds] }
  const [flagged, setFlagged] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [showReview, setShowReview] = useState(false);
  
  // Timer
  const [timeRemaining, setTimeRemaining] = useState(EXAM_TIME_MINUTES * 60);
  const timerRef = useRef(null);
  
  // Results
  const [results, setResults] = useState(null);

  const currentQuestion = questions[currentIndex];

  // Start exam
  const startExam = async () => {
    if (!selectedCity) {
      toast.error("Bitte wählen Sie eine Stadt aus");
      return;
    }
    
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      // Fetch all exam questions in a single API call
      const response = await axios.get(
        `${API}/simulation/questions?city=${selectedCity}`,
        { headers }
      );
      
      let allQuestions = response.data;
      
      // Add specialty names and normalize choices
      const specNameMap = {};
      EXAM_STRUCTURE.forEach(s => { specNameMap[s.id] = s.name; });
      allQuestions.forEach(q => {
        q.specialty_name = specNameMap[q.specialty_id] || q.specialty_id;
        if (!q.choices || q.choices.length === 0) q.choices = q.choices_de || [];
        if (!q.question_text) q.question_text = q.question_text_de || "";
      });
      
      // Shuffle all questions
      allQuestions = allQuestions.sort(() => Math.random() - 0.5);
      
      setQuestions(allQuestions);
      setStage("exam");
      setTimeRemaining(EXAM_TIME_MINUTES * 60);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            submitExam();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      const cityName = CITIES.find(c => c.id === selectedCity)?.name || selectedCity;
      toast.success(`Prüfung ${cityName} gestartet! Viel Erfolg!`);
    } catch (error) {
      console.error("Failed to load exam:", error);
      toast.error("Fehler beim Laden der Prüfung");
    } finally {
      setLoading(false);
    }
  };

  // Select answer
  const selectAnswer = (choiceId) => {
    if (!currentQuestion) return;
    
    const questionId = currentQuestion.id;
    const currentAnswers = answers[questionId] || [];
    const correctCount = currentQuestion.choices.filter(c => c.is_correct).length;
    
    if (correctCount > 1) {
      // Multiple choice
      if (currentAnswers.includes(choiceId)) {
        setAnswers({
          ...answers,
          [questionId]: currentAnswers.filter(id => id !== choiceId)
        });
      } else {
        setAnswers({
          ...answers,
          [questionId]: [...currentAnswers, choiceId]
        });
      }
    } else {
      // Single choice
      setAnswers({
        ...answers,
        [questionId]: [choiceId]
      });
    }
  };

  // Toggle flag
  const toggleFlag = () => {
    if (!currentQuestion) return;
    const newFlagged = new Set(flagged);
    if (newFlagged.has(currentIndex)) {
      newFlagged.delete(currentIndex);
    } else {
      newFlagged.add(currentIndex);
    }
    setFlagged(newFlagged);
  };

  // Navigation
  const goToQuestion = (index) => {
    if (index >= 0 && index < questions.length) {
      setCurrentIndex(index);
    }
  };

  // Submit exam
  const submitExam = () => {
    clearInterval(timerRef.current);
    
    let correct = 0;
    let wrong = 0;
    let unanswered = 0;
    const bySpecialty = {};
    
    questions.forEach((q, idx) => {
      const userAnswer = answers[q.id] || [];
      const correctIds = q.choices.filter(c => c.is_correct).map(c => c.id);
      
      // Initialize specialty stats
      if (!bySpecialty[q.specialty_name]) {
        bySpecialty[q.specialty_name] = { total: 0, correct: 0 };
      }
      bySpecialty[q.specialty_name].total++;
      
      if (userAnswer.length === 0) {
        unanswered++;
      } else if (
        userAnswer.length === correctIds.length &&
        userAnswer.every(id => correctIds.includes(id))
      ) {
        correct++;
        bySpecialty[q.specialty_name].correct++;
      } else {
        wrong++;
      }
    });
    
    const percentage = Math.round((correct / questions.length) * 100);
    const passed = percentage >= PASS_PERCENTAGE;
    const timeUsed = EXAM_TIME_MINUTES * 60 - timeRemaining;
    
    setResults({
      correct,
      wrong,
      unanswered,
      total: questions.length,
      percentage,
      passed,
      timeUsed,
      bySpecialty
    });
    
    setStage("results");
  };

  // Format time
  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Export results to PDF
  const exportResults = () => {
    if (!results) return;
    
    const date = new Date().toLocaleDateString('de-DE');
    const time = new Date().toLocaleTimeString('de-DE');
    
    let specialtyRows = '';
    Object.entries(results.bySpecialty).forEach(([name, data]) => {
      const pct = Math.round((data.correct / data.total) * 100);
      specialtyRows += `
        <tr>
          <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">${name}</td>
          <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: center;">${data.correct}/${data.total}</td>
          <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: center; color: ${pct >= 60 ? '#22c55e' : '#ef4444'};">${pct}%</td>
        </tr>
      `;
    });
    
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Prüfungsergebnis - Prep Academy</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
          .header { text-align: center; margin-bottom: 30px; }
          .logo { font-size: 24px; font-weight: bold; color: #667eea; }
          .result-box { padding: 30px; border-radius: 12px; text-align: center; margin: 20px 0; }
          .passed { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; }
          .failed { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
          .score { font-size: 64px; font-weight: bold; }
          .stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0; }
          .stat-box { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th { background: #f5f5f5; padding: 10px; text-align: left; }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="logo">Prep Academy</div>
          <p>Prüfungssimulation - ${date} um ${time}</p>
        </div>
        
        <div class="result-box ${results.passed ? 'passed' : 'failed'}">
          <div class="score">${results.percentage}%</div>
          <p style="font-size: 24px; margin: 10px 0;">
            ${results.passed ? '✓ BESTANDEN' : '✗ NICHT BESTANDEN'}
          </p>
          <p>${results.correct} von ${results.total} richtig (Bestehensgrenze: ${PASS_PERCENTAGE}%)</p>
        </div>
        
        <div class="stats">
          <div class="stat-box">
            <div style="font-size: 24px; font-weight: bold; color: #22c55e;">${results.correct}</div>
            <div>Richtig</div>
          </div>
          <div class="stat-box">
            <div style="font-size: 24px; font-weight: bold; color: #ef4444;">${results.wrong}</div>
            <div>Falsch</div>
          </div>
          <div class="stat-box">
            <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">${results.unanswered}</div>
            <div>Unbeantwortet</div>
          </div>
        </div>
        
        <h3>Ergebnis nach Fachgebiet</h3>
        <table>
          <tr>
            <th>Fachgebiet</th>
            <th style="text-align: center;">Richtig/Gesamt</th>
            <th style="text-align: center;">Prozent</th>
          </tr>
          ${specialtyRows}
        </table>
        
        <p style="margin-top: 30px; text-align: center; color: #888;">
          Zeit: ${formatTime(results.timeUsed)} von ${formatTime(EXAM_TIME_MINUTES * 60)}
        </p>
      </body>
      </html>
    `;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.print();
  };

  // Intro Stage
  if (stage === "intro") {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Prüfungssimulation</h1>
          <p className="text-muted-foreground">
            Simuliere die echte österreichische Medizinprüfung
          </p>
        </div>

        {/* City Selection */}
        <div className="glass-card rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-primary" />
            Prüfungsort wählen
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {CITIES.map((city) => (
              <button
                key={city.id}
                onClick={() => setSelectedCity(city.id)}
                className={`p-6 rounded-xl border-2 transition-[color,background-color,border-color] text-center ${
                  selectedCity === city.id
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                }`}
                data-testid={`city-${city.id}`}
              >
                <span className="text-4xl mb-2 block">{city.icon}</span>
                <span className="text-xl font-semibold">{city.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Exam Structure */}
        <div className="glass-card rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Prüfungsstruktur - Österreich</h2>
          <div className="space-y-3">
            {EXAM_STRUCTURE.map((spec) => (
              <div key={spec.id} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                <span className="font-medium">{spec.name}</span>
                <span className="text-primary font-semibold">{spec.questions} Fragen</span>
              </div>
            ))}
            <div className="flex justify-between items-center pt-4 border-t-2 border-primary">
              <span className="text-lg font-bold">Gesamt</span>
              <span className="text-xl font-bold text-primary">{TOTAL_QUESTIONS} Fragen</span>
            </div>
          </div>
        </div>

        {/* Exam Settings */}
        <div className="glass-card rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6">Prüfungseinstellungen</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                <Clock className="w-8 h-8 text-primary" />
              </div>
              <h3 className="font-semibold">Prüfungszeit</h3>
              <p className="text-muted-foreground">4 Stunden</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                <Trophy className="w-8 h-8 text-primary" />
              </div>
              <h3 className="font-semibold">Bestehensgrenze</h3>
              <p className="text-muted-foreground">60% (150/250)</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                <BookOpen className="w-8 h-8 text-primary" />
              </div>
              <h3 className="font-semibold">Navigation</h3>
              <p className="text-muted-foreground">Vor/zurück möglich</p>
            </div>
          </div>
        </div>

        {/* Warning */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-amber-500">Wichtiger Hinweis</p>
            <p className="text-sm text-muted-foreground">
              Die Prüfung startet sofort nach dem Klicken. Stellen Sie sicher, dass Sie 4 Stunden ungestört lernen können.
            </p>
          </div>
        </div>

        {/* Start Button */}
        <div className="text-center">
          <Button 
            size="lg" 
            className="gap-2 px-8"
            onClick={startExam}
            disabled={loading || !selectedCity}
          >
            {loading ? (
              <>Prüfung wird geladen...</>
            ) : (
              <>
                <Play className="w-5 h-5" />
                {selectedCity 
                  ? `Prüfung ${CITIES.find(c => c.id === selectedCity)?.name} starten`
                  : 'Bitte Stadt wählen'
                }
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }

  // Exam Stage
  if (stage === "exam" && currentQuestion) {
    const isAnswered = (answers[currentQuestion.id] || []).length > 0;
    const isFlagged = flagged.has(currentIndex);
    const answeredCount = Object.keys(answers).filter(id => answers[id].length > 0).length;
    
    return (
      <div className="flex min-h-[calc(100vh-4rem)]" data-testid="exam-stage">
        {/* ═══ SIDEBAR - Question Grid ═══ */}
        {sidebarOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}
        <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0 md:w-0 md:overflow-hidden'} fixed md:relative top-0 left-0 h-full md:h-auto w-64 md:w-56 lg:w-60 flex-shrink-0 transition-[transform,width] duration-300 z-40 md:z-auto bg-background md:bg-transparent border-r md:border-0 border-border/30 overflow-y-auto`}>
          <div className="sticky top-20 p-3 space-y-3">
            {/* Timer in sidebar */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg font-mono text-sm ${timeRemaining < 600 ? 'bg-red-500/20 text-red-500' : 'bg-muted/50 text-foreground'}`}>
              <Clock className="w-4 h-4" />
              {formatTime(timeRemaining)}
            </div>

            {/* Progress */}
            <div className="text-xs text-muted-foreground font-mono">
              {answeredCount}/{questions.length} beantwortet
            </div>
            <Progress value={(answeredCount / questions.length) * 100} className="h-1.5" />

            {/* Specialty */}
            <div className="text-sm font-semibold" style={{ color: '#3b82f6' }}>
              {currentQuestion.specialty_name}
            </div>

            {/* Question grid */}
            <div className="flex flex-wrap gap-1.5" data-testid="sim-question-grid">
              {questions.map((q, idx) => {
                const isAnsweredQ = (answers[q.id] || []).length > 0;
                const isFlaggedQ = flagged.has(idx);
                const isCurrent = idx === currentIndex;
                let bg = 'bg-muted/50 text-muted-foreground hover:bg-muted';
                if (isAnsweredQ) bg = 'bg-emerald-500/20 text-emerald-400';
                if (isFlaggedQ) bg = 'bg-amber-500/20 text-amber-400';
                if (isCurrent) bg += ' ring-2 ring-[#3b82f6]';
                return (
                  <button key={idx} onClick={() => goToQuestion(idx)}
                    className={`w-8 h-8 rounded-md text-xs font-mono font-semibold transition-[color,background-color,box-shadow] ${bg}`}
                    data-testid={`sim-grid-btn-${idx}`}>
                    {idx + 1}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="space-y-1 text-[10px] text-muted-foreground pt-2">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-emerald-500/20" /> Beantwortet</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-amber-500/20" /> Markiert</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-muted/50" /> Offen</div>
            </div>

            {/* Submit button */}
            <Button onClick={submitExam} size="sm" className="w-full gap-2 mt-2" variant="outline" data-testid="sim-submit-sidebar-btn">
              <ListChecks className="w-4 h-4" /> Prüfung abgeben
            </Button>
          </div>
        </div>

        {/* Toggle sidebar button */}
        <button onClick={() => setSidebarOpen(!sidebarOpen)}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-30 w-6 h-16 bg-muted/80 backdrop-blur rounded-r-lg flex items-center justify-center hover:bg-muted transition-colors"
          data-testid="sim-toggle-sidebar">
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Grid3X3 className="w-4 h-4" />}
        </button>

        {/* ═══ MAIN CONTENT ═══ */}
        <div className="flex-1 max-w-4xl mx-auto px-4 py-4">
          {/* Top bar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => goToQuestion(currentIndex - 1)} disabled={currentIndex === 0}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm font-mono text-muted-foreground">
                F{currentIndex + 1} / {questions.length}
              </span>
              <Button variant="ghost" size="sm" onClick={() => goToQuestion(currentIndex + 1)} disabled={currentIndex >= questions.length - 1}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground hidden sm:inline">{currentQuestion.specialty_name}</span>
              <div className={`flex items-center gap-1 px-3 py-1 rounded-lg font-mono text-sm md:hidden ${timeRemaining < 600 ? 'bg-red-500/20 text-red-500' : 'bg-muted'}`}>
                <Clock className="w-4 h-4" />{formatTime(timeRemaining)}
              </div>
              <Button variant={isFlagged ? "default" : "outline"} size="sm" className="gap-1" onClick={toggleFlag} data-testid="sim-flag-btn">
                <Flag className={`w-4 h-4 ${isFlagged ? 'fill-current' : ''}`} />
              </Button>
            </div>
          </div>

          {/* Question Card */}
          <div className="quiz-card mb-4">
            <div className="flex items-center gap-2 mb-4">
              {currentQuestion?.year && <span className="quiz-year-badge">{currentQuestion.year}</span>}
              {currentQuestion.choices.filter(c => c.is_correct).length > 1 && (
                <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-xs rounded-lg font-medium">Mehrfachauswahl</span>
              )}
            </div>

            <p className="question-text" data-testid="sim-question-text">
              {currentQuestion.question_text_de || currentQuestion.question_text}
            </p>

            {currentQuestion.image_base64 && (
              <div className="mb-6"><img src={currentQuestion.image_base64} alt="Question" className="question-image mx-auto" /></div>
            )}

            {/* Choices */}
            <div className="answers-container">
              {(currentQuestion?.choices || []).map((choice, idx) => {
                const isSelected = (answers[currentQuestion.id] || []).includes(choice.id);
                return (
                  <button key={choice.id} onClick={() => selectAnswer(choice.id)}
                    className={`answer-option ${isSelected ? 'selected' : ''}`}
                    data-testid={`sim-choice-${idx}`}>
                    <div className="answer-circle">
                      {String.fromCharCode(65 + idx)}
                    </div>
                    <p className="answer-text">{choice.text_de || choice.text}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bottom Navigation */}
          <div className="flex items-center justify-between">
            <Button variant="outline" onClick={() => goToQuestion(currentIndex - 1)} disabled={currentIndex === 0} className="gap-2">
              <ChevronLeft className="w-4 h-4" /> Zurück
            </Button>

            {currentIndex === questions.length - 1 ? (
              <Button onClick={submitExam} className="gap-2" data-testid="sim-submit-btn">
                Prüfung abgeben <CheckCircle className="w-4 h-4" />
              </Button>
            ) : (
              <Button onClick={() => goToQuestion(currentIndex + 1)} className="gap-2">
                Weiter <ChevronRight className="w-4 h-4" />
              </Button>
            )}
          </div>

          {/* Submit early */}
          <div className="text-center mt-4">
            <Button variant="ghost" size="sm" onClick={submitExam} className="text-muted-foreground">
              Prüfung vorzeitig abgeben
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Results Stage
  if (stage === "results" && results) {
    const cityName = CITIES.find(c => c.id === selectedCity)?.name || selectedCity;
    
    // Get wrong answers for review
    const wrongAnswers = questions.map((q, idx) => {
      const userAnswer = answers[q.id] || [];
      const correctIds = q.choices.filter(c => c.is_correct).map(c => c.id);
      if (userAnswer.length > 0 && !(userAnswer.length === correctIds.length && userAnswer.every(id => correctIds.includes(id)))) {
        return { idx, question: q, userAnswer, correctIds };
      }
      return null;
    }).filter(Boolean);

    if (showReview) {
      return (
        <div className="max-w-4xl mx-auto px-4 py-8" data-testid="sim-review-screen">
          <div className="flex items-center gap-3 mb-6">
            <Button variant="outline" size="sm" onClick={() => setShowReview(false)} className="gap-2">
              <ChevronLeft className="w-4 h-4" /> Zurück
            </Button>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <X className="w-5 h-5 text-red-400" /> Falsche Antworten ({wrongAnswers.length})
            </h2>
          </div>

          {/* Grid overview */}
          <div className="glass-card rounded-2xl p-6 mb-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Grid3X3 className="w-5 h-5" /> Alle 250 Fragen</h3>
            <div className="flex flex-wrap gap-1.5">
              {questions.map((q, idx) => {
                const ua = answers[q.id] || [];
                const ci = q.choices.filter(c => c.is_correct).map(c => c.id);
                const correct = ua.length > 0 && ua.length === ci.length && ua.every(id => ci.includes(id));
                const wrong = ua.length > 0 && !correct;
                let bg = 'bg-amber-500/20 text-amber-400';
                if (correct) bg = 'bg-emerald-500/20 text-emerald-400';
                if (wrong) bg = 'bg-red-500/20 text-red-400';
                return <div key={idx} className={`w-6 h-6 rounded text-[9px] font-mono flex items-center justify-center ${bg}`}>{idx + 1}</div>;
              })}
            </div>
          </div>

          {/* Wrong answers detail */}
          <div className="space-y-4">
            {wrongAnswers.map(({ idx, question: q, userAnswer, correctIds }) => (
              <div key={idx} className="glass-card rounded-xl p-5 border-l-4 border-red-500/40">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }}>Frage {idx + 1}</span>
                  <span className="text-xs text-muted-foreground">{q.specialty_name}</span>
                  {q.year && <span className="text-xs text-muted-foreground">{q.year}</span>}
                </div>
                <p className="font-medium mb-3 text-sm">{q.question_text_de || q.question_text}</p>
                <div className="space-y-2">
                  {q.choices.map((c, ci) => {
                    const isCorrect = correctIds.includes(c.id);
                    const wasSelected = userAnswer.includes(c.id);
                    let cls = 'bg-muted/30 border-transparent';
                    if (isCorrect) cls = 'bg-emerald-500/10 border-emerald-500/30';
                    if (wasSelected && !isCorrect) cls = 'bg-red-500/10 border-red-500/30';
                    return (
                      <div key={c.id} className={`flex items-center gap-3 p-2.5 rounded-lg border text-sm ${cls}`}>
                        <span className={`w-6 h-6 rounded flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                          isCorrect ? 'bg-emerald-500 text-white' : wasSelected ? 'bg-red-500 text-white' : 'bg-muted text-muted-foreground'
                        }`}>
                          {isCorrect ? <CheckCircle className="w-3 h-3" /> : wasSelected ? <XCircle className="w-3 h-3" /> : String.fromCharCode(65 + ci)}
                        </span>
                        <span className={isCorrect ? 'font-medium' : ''}>{c.text_de || c.text}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    return (
      <div className="max-w-4xl mx-auto px-4 py-8" data-testid="sim-results">
        {/* Result Header */}
        <div className={`rounded-2xl p-8 text-center text-white mb-8 ${
          results.passed 
            ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' 
            : 'bg-gradient-to-br from-red-500 to-red-600'
        }`}>
          <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center mx-auto mb-4">
            {results.passed ? (
              <CheckCircle className="w-10 h-10" />
            ) : (
              <XCircle className="w-10 h-10" />
            )}
          </div>
          <div className="text-6xl font-bold mb-2">{results.percentage}%</div>
          <div className="text-2xl font-semibold mb-2">
            {results.passed ? 'BESTANDEN!' : 'NICHT BESTANDEN'}
          </div>
          <p className="opacity-90">
            Prüfung {cityName} - {results.correct} von {results.total} Fragen richtig beantwortet
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-500">{results.correct}</div>
            <div className="text-sm text-muted-foreground">Richtig</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-500">{results.wrong}</div>
            <div className="text-sm text-muted-foreground">Falsch</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-amber-500">{results.unanswered}</div>
            <div className="text-sm text-muted-foreground">Unbeantwortet</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-2xl font-bold">{formatTime(results.timeUsed)}</div>
            <div className="text-sm text-muted-foreground">Zeit gebraucht</div>
          </div>
        </div>

        {/* Results by Specialty */}
        <div className="glass-card rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Ergebnis nach Fachgebiet</h2>
          <div className="space-y-3">
            {Object.entries(results.bySpecialty).map(([name, data]) => {
              const pct = Math.round((data.correct / data.total) * 100);
              return (
                <div key={name} className="flex items-center gap-4">
                  <span className="w-32 font-medium truncate">{name}</span>
                  <Progress value={pct} className="flex-1 h-3" />
                  <span className={`w-20 text-right font-semibold ${
                    pct >= 60 ? 'text-emerald-500' : 'text-red-500'
                  }`}>
                    {data.correct}/{data.total} ({pct}%)
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap justify-center gap-4">
          {wrongAnswers.length > 0 && (
            <Button onClick={() => setShowReview(true)} className="gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="sim-review-wrong-btn">
              <XCircle className="w-4 h-4" /> {wrongAnswers.length} Fehler anzeigen
            </Button>
          )}
          <Button variant="outline" onClick={exportResults} className="gap-2">
            <Download className="w-4 h-4" /> Als PDF exportieren
          </Button>
          <Button variant="outline" onClick={() => {
            setStage("intro");
            setQuestions([]);
            setAnswers({});
            setFlagged(new Set());
            setResults(null);
            setSelectedCity(null);
          }} className="gap-2">
            <RotateCcw className="w-4 h-4" />
            Neue Prüfung
          </Button>
          <Button onClick={() => navigate("/")} className="gap-2">
            <Home className="w-4 h-4" />
            Zur Startseite
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
