import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  Heart, 
  Trash2, 
  ArrowLeft,
  BookOpen,
  Loader2,
  Play,
  ArrowRight,
  Check,
  X,
  Trophy,
  RotateCcw,
  Sparkles,
  MessageCircle
} from "lucide-react";
import AIChat from "@/components/AIChat";

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState([]);
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
  const { token } = useAuth();

  const currentQuestion = favorites[currentIndex];

  useEffect(() => {
    fetchFavorites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchFavorites = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/favorites`, { headers });
      const rawData = Array.isArray(response.data) ? response.data : [];
      setFavorites(rawData.map(q => ({
        ...q,
        choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
        question_text: q.question_text || q.question_text_de || "",
      })));
    } catch (error) {
      console.error("Failed to fetch favorites:", error);
      toast.error("Fehler beim Laden der Favoriten");
    } finally {
      setLoading(false);
    }
  };

  const removeFavorite = async (questionId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/favorites/${questionId}`, { headers });
      setFavorites(prev => prev.filter(q => q.id !== questionId));
      toast.success("Aus Favoriten entfernt");
    } catch (error) {
      console.error("Failed to remove favorite:", error);
      toast.error("Fehler beim Entfernen");
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
    if (currentIndex < favorites.length - 1) {
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
          <h2 className="text-3xl font-bold mb-4" data-testid="favorites-quiz-complete">Favoriten Quiz beendet!</h2>
          <div className="text-6xl font-bold text-primary mb-2" data-testid="favorites-quiz-score">
            {percentage}%
          </div>
          <p className="text-xl text-muted-foreground mb-8">
            {score.correct} von {score.total} richtig
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Button onClick={restartQuiz} variant="outline" className="gap-2" data-testid="favorites-restart-btn">
              <RotateCcw className="w-4 h-4" />
              Quiz wiederholen
            </Button>
            <Button onClick={exitQuiz} className="gap-2" data-testid="favorites-exit-btn">
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
              Frage {currentIndex + 1} von {favorites.length}
            </span>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-primary">
                {score.correct}/{score.total} richtig
              </span>
              <Button variant="ghost" size="sm" onClick={exitQuiz} className="gap-1" data-testid="exit-quiz-btn">
                <X className="w-4 h-4" />
                Beenden
              </Button>
            </div>
          </div>
          <Progress value={((currentIndex + 1) / favorites.length) * 100} className="h-2" />
        </div>

        {/* Question Card */}
        <div className="glass-card rounded-2xl p-6 md:p-8 mb-6">
          <div className="flex items-center gap-3 mb-6">
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

          <h2 className="text-xl font-semibold mb-6" data-testid="favorites-question-text">
            {currentQuestion?.question_text_de || currentQuestion?.question_text}
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
                data-testid={`favorites-choice-${index}`}
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
                <p className="font-medium">{choice.text_de || choice.text}</p>
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
              data-testid="favorites-submit-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Antwort bestätigen
            </Button>
          ) : (
            <Button 
              onClick={nextQuestion} 
              size="lg" 
              className="w-full sm:w-auto gap-2"
              data-testid="favorites-next-btn"
            >
              {currentIndex < favorites.length - 1 ? "Nächste Frage" : "Quiz beenden"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}

          <Button
            variant="outline"
            onClick={() => setAiChatOpen(true)}
            className="w-full sm:w-auto gap-2 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/30"
            data-testid="favorites-ai-btn"
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
          <div className="p-3 rounded-xl bg-red-500/10">
            <Heart className="w-6 h-6 text-red-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="favorites-title">Favoriten</h1>
            <p className="text-muted-foreground">{favorites.length} gespeicherte Fragen</p>
          </div>
        </div>
        <Link to="/">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Zurück
          </Button>
        </Link>
      </div>

      {/* Start Quiz Button */}
      {favorites.length > 0 && (
        <div className="mb-6">
          <Button 
            onClick={startQuiz} 
            size="lg" 
            className="w-full gap-2"
            data-testid="start-favorites-quiz-btn"
          >
            <Play className="w-5 h-5" />
            Favoriten Quiz starten ({favorites.length} Fragen)
          </Button>
        </div>
      )}

      {/* Favorites List */}
      {favorites.length === 0 ? (
        <div className="empty-state glass-card rounded-2xl">
          <Heart className="w-16 h-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold mt-4">Keine Favoriten</h2>
          <p className="text-muted-foreground">Fügen Sie Fragen zu Ihren Favoriten hinzu, um sie später zu wiederholen</p>
          <Link to="/">
            <Button className="mt-6">Fragen durchsuchen</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {favorites.map((question, index) => (
            <div 
              key={question.id} 
              className="glass-card rounded-xl p-6 hover:border-primary/30 transition-colors"
              data-testid={`favorite-item-${index}`}
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
                  </div>
                  <p className="text-foreground mb-2">{question.question_text_de || question.question_text}</p>
                  
                  <div className="mt-4 space-y-2">
                    {question.choices?.slice(0, 3).map((choice, i) => (
                      <div 
                        key={choice.id}
                        className={`text-sm px-3 py-2 rounded-lg ${
                          choice.is_correct 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : "bg-muted/50 text-muted-foreground"
                        }`}
                      >
                        {String.fromCharCode(65 + i)}. {choice.text_de || choice.text}
                      </div>
                    ))}
                    {question.choices?.length > 3 && (
                      <p className="text-xs text-muted-foreground">
                        +{question.choices.length - 3} weitere Antworten
                      </p>
                    )}
                  </div>
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFavorite(question.id)}
                  className="text-red-500 hover:text-red-400 hover:bg-red-500/10"
                  data-testid={`remove-favorite-${index}`}
                >
                  <Trash2 className="w-5 h-5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
