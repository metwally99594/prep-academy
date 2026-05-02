import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  Search,
  ArrowLeft,
  Loader2,
  ArrowRight,
  Check,
  X,
  Trophy,
  RotateCcw,
  Sparkles,
  MessageCircle,
  Heart
} from "lucide-react";
import AIChat from "@/components/AIChat";

export default function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const navigate = useNavigate();
  const { token } = useAuth();

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quizMode, setQuizMode] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedChoices, setSelectedChoices] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [quizCompleted, setQuizCompleted] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [aiChatOpen, setAiChatOpen] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);

  const currentQuestion = questions[currentIndex];

  useEffect(() => {
    if (query) {
      fetchSearchResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, token]);

  useEffect(() => {
    if (currentQuestion && token) {
      checkFavorite();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentQuestion, token]);

  const fetchSearchResults = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(
        `${API}/questions/search/text?q=${encodeURIComponent(query)}&limit=50`,
        { headers }
      );
      const rawData = Array.isArray(response.data) ? response.data : [];
      setQuestions(rawData.map(q => ({
        ...q,
        choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
        question_text: q.question_text || q.question_text_de || "",
      })));
    } catch (error) {
      console.error("Search failed:", error);
      toast.error("Fehler bei der Suche");
    } finally {
      setLoading(false);
    }
  };

  const checkFavorite = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/favorites/check/${currentQuestion.id}`, { headers });
      setIsFavorite(response.data.is_favorite);
    } catch (error) {
      console.error("Failed to check favorite:", error);
    }
  };

  const toggleFavorite = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      if (isFavorite) {
        await axios.delete(`${API}/favorites/${currentQuestion.id}`, { headers });
        toast.success("Aus Favoriten entfernt");
      } else {
        await axios.post(`${API}/favorites`, { question_id: currentQuestion.id }, { headers });
        toast.success("Zu Favoriten hinzugefügt");
      }
      setIsFavorite(!isFavorite);
    } catch (error) {
      console.error("Failed to toggle favorite:", error);
      toast.error("Fehler beim Aktualisieren der Favoriten");
    }
  };

  const startQuiz = () => {
    setQuizMode(true);
    setCurrentIndex(0);
    setSelectedChoices([]);
    setShowResult(false);
    setResult(null);
    setQuizCompleted(false);
    setScore({ correct: 0, total: 0 });
  };

  const toggleChoice = (choiceId) => {
    if (showResult) return;
    const correctCount = currentQuestion?.choices?.filter(c => c.is_correct === true).length || 1;
    
    if (correctCount === 1) {
      setSelectedChoices([choiceId]);
    } else {
      setSelectedChoices(prev => 
        prev.includes(choiceId)
          ? prev.filter(id => id !== choiceId)
          : [...prev, choiceId]
      );
    }
  };

  const submitAnswer = async () => {
    if (selectedChoices.length === 0) {
      toast.error("Bitte wählen Sie mindestens eine Antwort");
      return;
    }

    setSubmitting(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.post(
        `${API}/questions/${currentQuestion.id}/answer`,
        { question_id: currentQuestion.id, selected_choice_ids: selectedChoices },
        { headers }
      );
      setResult(response.data);
      setShowResult(true);
      setScore(prev => ({
        correct: prev.correct + (response.data.is_correct ? 1 : 0),
        total: prev.total + 1
      }));
      
      if (response.data.is_correct) {
        toast.success("Richtig!");
      } else {
        toast.error("Falsch");
      }
    } catch (error) {
      console.error("Failed to submit answer:", error);
      toast.error("Fehler beim Senden der Antwort");
    } finally {
      setSubmitting(false);
    }
  };

  const nextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setSelectedChoices([]);
      setShowResult(false);
      setResult(null);
    } else {
      setQuizCompleted(true);
    }
  };

  const restartQuiz = () => {
    setCurrentIndex(0);
    setSelectedChoices([]);
    setShowResult(false);
    setResult(null);
    setQuizCompleted(false);
    setScore({ correct: 0, total: 0 });
  };

  const exitQuiz = () => {
    setQuizMode(false);
    setCurrentIndex(0);
    setSelectedChoices([]);
    setShowResult(false);
    setResult(null);
    setQuizCompleted(false);
    setScore({ correct: 0, total: 0 });
  };

  const getChoiceClass = useCallback((choice) => {
    if (!showResult) {
      return selectedChoices.includes(choice.id) ? "selected" : "";
    }
    if (result?.correct_choice_ids?.includes(choice.id)) {
      return "correct";
    }
    if (selectedChoices.includes(choice.id) && !result?.correct_choice_ids?.includes(choice.id)) {
      return "incorrect";
    }
    return "";
  }, [showResult, selectedChoices, result]);

  const highlightKeyword = (text) => {
    if (!query || !text) return text;
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) => 
      regex.test(part) ? <mark key={i} className="bg-primary/30 text-primary px-1 rounded">{part}</mark> : part
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Quiz Completed View
  if (quizMode && quizCompleted) {
    const percentage = Math.round((score.correct / score.total) * 100);
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="glass-card rounded-2xl p-8 text-center">
          <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-6">
            <Trophy className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-3xl font-bold mb-4" data-testid="search-quiz-complete">Suche Quiz beendet!</h2>
          <div className="text-6xl font-bold text-primary mb-2" data-testid="search-quiz-score">
            {percentage}%
          </div>
          <p className="text-xl text-muted-foreground mb-4">
            {score.correct} von {score.total} richtig
          </p>
          <p className="text-sm text-muted-foreground mb-8">
            Suchbegriff: "{query}"
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Button onClick={restartQuiz} variant="outline" className="gap-2" data-testid="search-restart-btn">
              <RotateCcw className="w-4 h-4" />
              Quiz wiederholen
            </Button>
            <Button onClick={exitQuiz} className="gap-2" data-testid="search-exit-btn">
              <ArrowLeft className="w-4 h-4" />
              Zurück zur Liste
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Quiz Mode View
  if (quizMode && currentQuestion) {
    const correctCount = currentQuestion?.choices?.filter(c => c.is_correct === true).length || 1;
    
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">
              Frage {currentIndex + 1} von {questions.length}
            </span>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-primary">
                {score.correct}/{score.total} richtig
              </span>
              <Button variant="ghost" size="sm" onClick={exitQuiz} className="gap-1" data-testid="exit-search-quiz-btn">
                <X className="w-4 h-4" />
                Beenden
              </Button>
            </div>
          </div>
          <Progress value={((currentIndex + 1) / questions.length) * 100} className="h-2" />
        </div>

        {/* Question Card */}
        <div className="glass-card rounded-2xl p-6 md:p-8 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="px-3 py-1 bg-blue-500/10 text-blue-500 text-sm rounded-lg font-medium flex items-center gap-1">
                <Search className="w-3 h-3" />
                Suchergebnis
              </span>
              <span className="px-3 py-1 bg-primary/10 text-primary text-sm rounded-lg font-medium">
                {currentQuestion?.year}
              </span>
              <span className="px-3 py-1 bg-muted text-muted-foreground text-sm rounded-lg">
                {currentQuestion?.specialty_id}
              </span>
              {correctCount > 1 && (
                <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-sm rounded-lg font-medium">
                  {correctCount} richtige Antworten
                </span>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleFavorite}
              className={isFavorite ? "text-red-500" : "text-muted-foreground"}
              data-testid="search-favorite-btn"
            >
              <Heart className={`w-5 h-5 ${isFavorite ? "fill-current" : ""}`} />
            </Button>
          </div>

          <h2 className="text-xl font-semibold mb-6" data-testid="search-question-text">
            {highlightKeyword(currentQuestion?.question_text_de || currentQuestion?.question_text)}
          </h2>

          {currentQuestion?.image_base64 && (
            <div className="mb-6">
              <img
                src={currentQuestion.image_base64}
                alt="Question"
                className="question-image mx-auto rounded-lg max-h-64 object-contain"
              />
            </div>
          )}

          <div className="space-y-3">
            {(currentQuestion?.choices || []).map((choice, index) => (
              <button
                key={choice.id}
                onClick={() => toggleChoice(choice.id)}
                disabled={showResult}
                className={`choice-btn w-full text-left p-4 rounded-xl flex items-center gap-4 ${getChoiceClass(choice)}`}
                data-testid={`search-choice-${index}`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium flex-shrink-0 ${
                  getChoiceClass(choice) === "correct" 
                    ? "bg-green-500 text-white"
                    : getChoiceClass(choice) === "incorrect"
                    ? "bg-red-500 text-white"
                    : selectedChoices.includes(choice.id)
                    ? "bg-primary text-white"
                    : "bg-muted text-muted-foreground"
                }`}>
                  {getChoiceClass(choice) === "correct" ? (
                    <Check className="w-4 h-4" />
                  ) : getChoiceClass(choice) === "incorrect" ? (
                    <X className="w-4 h-4" />
                  ) : (
                    String.fromCharCode(65 + index)
                  )}
                </div>
                <p className="font-medium">{highlightKeyword(choice.text_de || choice.text)}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {!showResult ? (
            <Button 
              onClick={submitAnswer} 
              size="lg" 
              className="w-full sm:w-auto gap-2"
              disabled={submitting || selectedChoices.length === 0}
              data-testid="search-submit-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Antwort bestätigen
            </Button>
          ) : (
            <Button 
              onClick={nextQuestion} 
              size="lg" 
              className="w-full sm:w-auto gap-2"
              data-testid="search-next-btn"
            >
              {currentIndex < questions.length - 1 ? "Nächste Frage" : "Quiz beenden"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}

          <Button
            variant="outline"
            onClick={() => setAiChatOpen(true)}
            className="w-full sm:w-auto gap-2 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/30"
            data-testid="search-ai-btn"
          >
            <MessageCircle className="w-4 h-4" />
            KI fragen
          </Button>
        </div>

        {showResult && result?.explanation && (
          <div className="mt-6 glass-card rounded-xl p-6">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              Erklärung
            </h3>
            <p className="text-muted-foreground leading-relaxed">{result.explanation}</p>
          </div>
        )}

        <AIChat 
          question={currentQuestion}
          isOpen={aiChatOpen}
          onClose={() => setAiChatOpen(false)}
        />
      </div>
    );
  }

  // List View (Default)
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-blue-500/10">
            <Search className="w-6 h-6 text-blue-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="search-results-title">Suchergebnisse</h1>
            <p className="text-muted-foreground">
              {questions.length} Fragen für "{query}"
            </p>
          </div>
        </div>
        <Button variant="ghost" className="gap-2" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4" />
          Zurück
        </Button>
      </div>

      {/* Start Quiz Button */}
      {questions.length > 0 && (
        <div className="mb-6">
          <Button 
            onClick={startQuiz} 
            size="lg" 
            className="w-full gap-2 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600"
            data-testid="start-search-quiz-btn"
          >
            <Search className="w-5 h-5" />
            Quiz starten ({questions.length} Fragen)
          </Button>
        </div>
      )}

      {/* Search Results List */}
      {questions.length === 0 ? (
        <div className="empty-state glass-card rounded-2xl">
          <Search className="w-16 h-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold mt-4">Keine Ergebnisse</h2>
          <p className="text-muted-foreground">Keine Fragen für "{query}" gefunden</p>
          <Button className="mt-6" onClick={() => navigate("/")}>
            Zurück zur Startseite
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {questions.map((question, index) => (
            <div 
              key={question.id} 
              className="glass-card rounded-xl p-6 hover:border-blue-500/30 transition-colors cursor-pointer border-l-4 border-l-blue-500"
              onClick={() => {
                setCurrentIndex(index);
                startQuiz();
              }}
              data-testid={`search-result-item-${index}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-lg font-medium">
                      {question.year}
                    </span>
                    <span className="px-2 py-1 bg-muted text-muted-foreground text-xs rounded-lg">
                      {question.specialty_id}
                    </span>
                    {question.exam_location && (
                      <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-xs rounded-lg">
                        {question.exam_location === "vienna" ? "Wien" : "Innsbruck"}
                      </span>
                    )}
                  </div>
                  <p className="text-foreground mb-4 text-lg">
                    {highlightKeyword(question.question_text_de || question.question_text)}
                  </p>
                  
                  {/* Show all choices */}
                  <div className="mt-4 space-y-2">
                    {question.choices?.map((choice, i) => (
                      <div 
                        key={choice.id}
                        className={`text-sm px-3 py-2 rounded-lg ${
                          choice.is_correct 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : "bg-muted/50 text-muted-foreground"
                        }`}
                      >
                        {String.fromCharCode(65 + i)}. {highlightKeyword(choice.text_de || choice.text)}
                        {choice.is_correct && <span className="ml-2">✓</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
