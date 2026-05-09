import { useState, memo } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ChevronDown, ChevronUp, Brain, BookOpen, HelpCircle, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

function InsightSection({ icon: Icon, title, children }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
        <Icon className="w-3.5 h-3.5 text-primary" />
        {title}
      </div>
      <div className="text-xs text-foreground/80 leading-relaxed pl-5">
        {children}
      </div>
    </div>
  );
}

export const AIInsightBlock = memo(function AIInsightBlock({ post }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const summary = post?.ai_summary;
  const hasSummary = typeof summary === "string" && summary.trim().length > 0;

  return (
    <div className="rounded-2xl border border-primary/15 bg-primary/3">
      {/* Collapsed header — always visible */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        aria-label="KI-Einblicke ein-/ausblenden"
      >
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="text-sm font-semibold">KI-Einblicke</span>
          {hasSummary && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
              Verfügbar
            </span>
          )}
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
          : <ChevronDown className="w-4 h-4 text-muted-foreground" />
        }
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-4 pb-4 space-y-4 border-t border-primary/10">
          {hasSummary ? (
            <>
              <InsightSection icon={Brain} title="KI-Zusammenfassung">
                {summary}
              </InsightSection>

              <InsightSection icon={BookOpen} title="Mögliche Lernkarten">
                <p className="text-muted-foreground italic">
                  Lernkarten werden automatisch aus veröffentlichten Beiträgen generiert.
                  Nutzen Sie die Lerntools-Seite, um Ihre eigenen Karten zu erstellen.
                </p>
              </InsightSection>

              <InsightSection icon={HelpCircle} title="Mögliche Prüfungsfragen">
                <p className="text-muted-foreground italic">
                  Prüfungsfragen werden von unserem Redaktionsteam aus Community-Beiträgen ausgewählt.
                </p>
              </InsightSection>
            </>
          ) : (
            <div className="py-2 text-center space-y-2">
              <Sparkles className="w-8 h-8 mx-auto text-muted-foreground/20" />
              <p className="text-xs text-muted-foreground">
                Noch keine KI-Analyse für diesen Beitrag verfügbar.
              </p>
              <p className="text-[10px] text-muted-foreground/60">
                KI-Einblicke werden schrittweise für Beiträge mit hoher Qualität aktiviert.
              </p>
            </div>
          )}

          {/* Mit KI diskutieren CTA */}
          <div className="pt-2 border-t border-primary/10">
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2 border-primary/20 text-primary hover:bg-primary/5"
              onClick={() => navigate("/analyzer")}
            >
              <MessageCircle className="w-3.5 h-3.5" />
              Mit KI diskutieren
            </Button>
          </div>
        </div>
      )}
    </div>
  );
});
