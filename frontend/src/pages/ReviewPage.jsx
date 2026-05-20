import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  RefreshCcw, 
  Trash2, 
  ArrowLeft,
  Loader2,
  Play,
  ArrowRight,
  Check,
  X,
  Trophy,
  RotateCcw,
  Sparkles,
  MessageCircle,
  CheckCircle
} from "lucide-react";
import AIChat from "@/components/AIChat";

export default function ReviewPage() {
  const [reviewQuestions, setReviewQuestions] = useState([]);
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

  const currentQuestion = reviewQuestions[currentIndex];

  useEffect(() => {
    fetchReviewQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchReviewQuestions = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/review`, { headers });
      const rawData = Array.isArray(response.data) ? response.data : [];
      setReviewQuestions(rawData.map(q => ({
        ...q,
        choices: (Array.isArray(q.choices) && q.choices.length > 0) ? q.choices : (Array.isArray(q.choices_de) ? q.choices_de : []),
        question_text: q.question_text || q.question_text_de || "",
      })));
    } catch (error) {
      console.error("Failed to fetch review questions:", error);
      toast.error("Fehler beim Laden der Überprüfungsfragen");
    } finally {
      setLoading(false);
    }
  };

  const removeFromReview = async (questionId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/review/${questionId}`, { headers });
      setReviewQuestions(prev => prev.filter(q => q.id !== questionId));
      toast.success("Aus der Überprüfung entfernt");
    } catch (error) {
      console.error("Failed to remove from review:", error);
      toast.error("Fehler beim Entfernen");
    }
  };

  const markAsReviewed = async (questionId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API}/review/${questionId}/mark-reviewed`, {}, { headers });
      setReviewQuestions(prev => prev.filter(q => q.id !== questionId));
      toast.success("Als überprüft markiert");
    } catch (error) {
      console.error("Failed to mark as reviewed:", error);
      toast.error("Fehler beim Markieren");
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
        toast.success("Richtig! Frage wird als überprüft markiert.");
      } else {
        toast.error("Falsch - Weiter üben!");
      }
    } catch (error) {
      console.error("Failed to submit answer:", error);
      toast.error("Fehler beim Senden der Antwort");
    } finally {
      setSubmitting(false);
    }
  };

  const nextQuestion = () => {
    if (currentIndex < reviewQuestions.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setSelectedChoices([]);
      setShowResult(false);
      setResult(null);
    } else {
      setQuizCompleted(true);
    }
  };

  const restartQuiz = () => {
    fetchReviewQuestions();
    setCurrentIndex(0);
    setSelectedChoices([]);
    setShowResult(false);
    setResult(null);
    setQuizCompleted(false);
    setScore({ correct: 0, total: 0 });
  };

  const exitQuiz = () => {
    fetchReviewQuestions();
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
          <h2 className="text-3xl font-bold mb-4" data-testid="review-quiz-complete">Überprüfung abgeschlossen!</h2>
          <div className="text-6xl font-bold text-primary mb-2" data-testid="review-quiz-score">
            {percentage}%
          </div>
          <p className="text-xl text-muted-foreground mb-4">
            {score.correct} von {score.total} richtig
          </p>
          <p className="text-sm text-muted-foreground mb-8">
            Richtig beantwortete Fragen wurden automatisch als überprüft markiert.
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Button onClick={restartQuiz} variant="outline" className="gap-2" data-testid="review-restart-btn">
              <RotateCcw className="w-4 h-4" />
              Erneut überprüfen
            </Button>
            <Button onClick={exitQuiz} className="gap-2" data-testid="review-exit-btn">
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
              Frage {currentIndex + 1} von {reviewQuestions.length}
            </span>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-primary">
                {score.correct}/{score.total} richtig
              </span>
              <Button variant="ghost" size="sm" onClick={exitQuiz} className="gap-1" data-testid="exit-review-btn">
                <X className="w-4 h-4" />
                Beenden
              </Button>
            </div>
          </div>
          <Progress value={((currentIndex + 1) / reviewQuestions.length) * 100} className="h-2" />
        </div>

        {/* Question Card */}
        <div className="quiz-card mb-6">
          <div className="flex items-center gap-3 mb-6">
            <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-sm rounded-lg font-medium">
              Überprüfung
            </span>
            {currentQuestion?.year && <span className="quiz-year-badge">{currentQuestion.year}</span>}
            <span className="px-3 py-1 bg-muted text-muted-foreground text-sm rounded-lg">
              {currentQuestion?.specialty_id}
            </span>
            {correctCount > 1 && (
              <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-sm rounded-lg font-medium">
                {correctCount} richtige Antworten
              </span>
            )}
          </div>

          <h2 className="question-text" data-testid="review-question-text">
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

          <div className="answers-container">
            {(currentQuestion?.choices || []).map((choice, index) => (
              <button
                key={choice.id}
                onClick={() => toggleChoice(choice.id)}
                disabled={showResult}
                className={`answer-option ${getChoiceClass(choice)}`}
                data-testid={`review-choice-${index}`}
              >
                <div className="answer-circle">
                  {getChoiceClass(choice) === "correct" ? (
                    <Check className="w-4 h-4" />
                  ) : getChoiceClass(choice) === "incorrect" ? (
                    <X className="w-4 h-4" />
                  ) : (
                    String.fromCharCode(65 + index)
                  )}
                </div>
                <p className="answer-text">{choice.text_de || choice.text}</p>
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
              data-testid="review-submit-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Antwort bestätigen
            </Button>
          ) : (
            <Button 
              onClick={nextQuestion} 
              size="lg" 
              className="w-full sm:w-auto gap-2"
              data-testid="review-next-btn"
            >
              {currentIndex < reviewQuestions.length - 1 ? "Nächste Frage" : "Überprüfung beenden"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}

          <Button
            variant="outline"
            onClick={() => setAiChatOpen(true)}
            className="w-full sm:w-auto gap-2 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/30"
            data-testid="review-ai-btn"
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
          <div className="p-3 rounded-xl bg-amber-500/10">
            <RefreshCcw className="w-6 h-6 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="review-title">Schnelle Überprüfung</h1>
            <p className="text-muted-foreground">{reviewQuestions.length} Fragen zur Überprüfung</p>
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
      {reviewQuestions.length > 0 && (
        <div className="mb-6">
          <Button 
            onClick={startQuiz} 
            size="lg" 
            className="w-full gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
            data-testid="start-review-quiz-btn"
          >
            <Play className="w-5 h-5" />
            Überprüfung starten ({reviewQuestions.length} Fragen)
          </Button>
        </div>
      )}

      {/* Review Questions List */}
      {reviewQuestions.length === 0 ? (
        <div className="empty-state glass-card rounded-2xl">
          <CheckCircle className="w-16 h-16 text-emerald-500" />
          <h2 className="text-xl font-semibold mt-4">Alles überprüft!</h2>
          <p className="text-muted-foreground">Sie haben keine Fragen zur Überprüfung. Gut gemacht!</p>
          <Link to="/">
            <Button className="mt-6">Weiter üben</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground mb-4">
            Diese Fragen wurden falsch beantwortet. Üben Sie sie erneut!
          </p>
          {reviewQuestions.map((question, index) => (
            <div 
              key={question.id} 
              className="glass-card rounded-xl p-6 hover:border-amber-500/30 transition-colors border-l-4 border-l-amber-500"
              data-testid={`review-item-${index}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    {question.year && <span className="quiz-year-badge" style={{ fontSize: 11 }}>{question.year}</span>}
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
                
                <div className="flex flex-col gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => markAsReviewed(question.id)}
                    className="text-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/10"
                    title="Als überprüft markieren"
                    data-testid={`mark-reviewed-${index}`}
                  >
                    <CheckCircle className="w-5 h-5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeFromReview(question.id)}
                    className="text-red-500 hover:text-red-400 hover:bg-red-500/10"
                    title="Entfernen"
                    data-testid={`remove-review-${index}`}
                  >
                    <Trash2 className="w-5 h-5" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
