import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Check, Lock, BookOpen, Loader2, X, Award } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getMasterclassLevels, getMasterclassLevel, completeLevel } from "@/lib/api";

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

export default function MasterclassPage() {
  const [levels, setLevels] = useState([]);
  const [currentLevel, setCurrentLevel] = useState(1);
  const [completedCount, setCompletedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [modalLevel, setModalLevel] = useState(null);
  const [modalData, setModalData] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [completing, setCompleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getMasterclassLevels();
      setLevels(data.levels || []);
      setCurrentLevel(data.current_level || 1);
      setCompletedCount(data.completed_count || 0);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openLevel = async (lv) => {
    if (lv.is_locked) return;
    setModalLevel(lv);
    setModalData(null);
    setModalLoading(true);
    try {
      const data = await getMasterclassLevel(lv.level_number);
      setModalData(data);
    } catch {
      // silent
    } finally {
      setModalLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!modalLevel || completing) return;
    setCompleting(true);
    try {
      await completeLevel(modalLevel.level_number);
      setCompletedCount(prev => prev + 1);
      setCurrentLevel(prev => Math.max(prev, modalLevel.level_number + 1));
      setModalLevel(null);
      setModalData(null);
      await load();
    } catch {
      // silent
    } finally {
      setCompleting(false);
    }
  };

  // Group by chapter
  const chapters = [];
  for (let i = 0; i < 9; i++) {
    const chapterLevels = levels.filter(l => l.chapter === i + 1);
    if (chapterLevels.length > 0) {
      chapters.push({ chapter: i + 1, levels: chapterLevels });
    }
  }

  const percent = levels.length > 0 ? Math.round((completedCount / levels.length) * 100) : 0;

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <Link to="/de">
        <Button variant="ghost" size="sm" className="gap-1 mb-6">
          <ArrowLeft className="w-4 h-4" /> Zurück
        </Button>
      </Link>

      <h1 className="text-3xl font-bold mb-2">Masterclass</h1>
      <p className="text-muted-foreground mb-6">90 Levels — bereite dich systematisch auf die Kenntnisprüfung vor</p>

      {/* Progress bar */}
      <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-5 mb-8">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-purple-400" />
            <span className="font-semibold">Level {currentLevel} / {levels.length}</span>
          </div>
          <span className="text-sm text-muted-foreground">{completedCount} abgeschlossen — {percent}%</span>
        </div>
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${percent}%`, background: "linear-gradient(90deg, #a855f7, #7c3aed)" }}
          />
        </div>
      </div>

      {/* Chapters */}
      <div className="space-y-6">
        {chapters.map(ch => (
          <div key={ch.chapter}>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Kapitel {ch.chapter}
            </h2>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
              {ch.levels.map(lv => {
                const isCurrent = lv.is_current;
                const isLocked = lv.is_locked;
                const isCompleted = lv.is_completed;
                return (
                  <button
                    key={lv.level_number}
                    onClick={() => openLevel(lv)}
                    disabled={isLocked}
                    className={classNames(
                      "relative rounded-lg border p-2 text-center transition-all text-xs font-medium h-14 flex flex-col items-center justify-center gap-0.5",
                      isCompleted && "bg-emerald-500/15 border-emerald-500/30 text-emerald-400",
                      isCurrent && "bg-blue-500/15 border-blue-500 ring-2 ring-blue-500/40 text-blue-400",
                      isLocked && "bg-muted/30 border-border/30 text-muted-foreground/40 cursor-not-allowed",
                      !isCompleted && !isCurrent && !isLocked && "bg-card border-border/60 hover:border-primary/40 text-foreground",
                    )}
                  >
                    {isCompleted ? <Check className="w-3.5 h-3.5" /> : isLocked ? <Lock className="w-3.5 h-3.5" /> : null}
                    <span>{lv.level_number}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Level Modal */}
      {modalLevel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setModalLevel(null)}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div className="relative max-w-4xl w-full rounded-2xl border border-border/60 bg-card p-8 shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-xs text-muted-foreground">Level {modalLevel.level_number}</span>
                <h2 className="text-lg font-bold">{modalData?.title || modalLevel.title}</h2>
              </div>
              <button onClick={() => setModalLevel(null)} className="p-1 hover:bg-muted rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground leading-relaxed mb-6 whitespace-pre-wrap">
                {modalData?.content || modalLevel.description || "Inhalt folgt bald."}
              </div>
            )}

            {!modalLevel.is_completed && (
              <Button className="w-full gap-2" onClick={handleComplete} disabled={completing || modalLoading}>
                {completing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Level abgeschlossen
              </Button>
            )}
            {modalLevel.is_completed && (
              <div className="w-full py-2.5 rounded-xl text-sm font-semibold text-center bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ✅ Bereits abgeschlossen
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
