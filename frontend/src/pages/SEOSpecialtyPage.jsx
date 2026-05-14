import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { BookOpen, Users, Calendar, ArrowRight, CheckCircle2, GraduationCap, UserPlus } from "lucide-react";

export default function SEOSpecialtyPage() {
  const { specialtyId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/seo/specialty/${specialtyId}`)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [specialtyId]);

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin w-8 h-8 border-2 border-[#3b82f6] border-t-transparent rounded-full" /></div>;
  if (!data) return <div className="text-center py-20 text-muted-foreground">Fachgebiet nicht gefunden</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8" data-testid="seo-specialty-page">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="text-4xl mb-3">{data.icon}</div>
        <h1 className="text-3xl sm:text-4xl font-bold mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
          {data.name_de} <span style={{ color: '#3b82f6' }}>Prüfungsfragen</span>
        </h1>
        <p className="text-muted-foreground">Bereite dich optimal auf die medizinische Prüfung vor</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-10">
        <div className="p-5 rounded-xl border border-border/30 text-center" style={{ background: 'rgba(59, 130, 246, 0.03)' }}>
          <BookOpen className="w-6 h-6 mx-auto mb-2" style={{ color: '#3b82f6' }} />
          <div className="text-2xl font-bold">{data.total_questions}</div>
          <div className="text-xs text-muted-foreground">Fragen</div>
        </div>
        <div className="p-5 rounded-xl border border-border/30 text-center" style={{ background: 'rgba(59, 130, 246, 0.03)' }}>
          <Users className="w-6 h-6 mx-auto mb-2" style={{ color: '#3b82f6' }} />
          <div className="text-2xl font-bold">{data.active_users}</div>
          <div className="text-xs text-muted-foreground">Aktive Nutzer</div>
        </div>
        <div className="p-5 rounded-xl border border-border/30 text-center" style={{ background: 'rgba(59, 130, 246, 0.03)' }}>
          <Calendar className="w-6 h-6 mx-auto mb-2" style={{ color: '#3b82f6' }} />
          <div className="text-2xl font-bold">{data.years?.length || 0}</div>
          <div className="text-xs text-muted-foreground">Prüfungsjahre</div>
        </div>
      </div>

      {/* Sample Questions */}
      <div className="mb-10">
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "'Playfair Display', serif" }}>
          Beispielfragen aus <span style={{ color: '#3b82f6' }}>{data.name_de}</span>
        </h2>
        <div className="space-y-4">
          {data.sample_questions?.map((q, i) => (
            <div key={q.id || i} className="p-5 rounded-xl border border-border/30" style={{ background: 'rgba(59, 130, 246, 0.02)' }}>
              <p className="font-medium text-sm mb-3">{q.question_text_de || q.question_text}</p>
              <div className="space-y-2">
                {(q.choices || []).map((c, j) => (
                  <div key={j} className={`flex items-center gap-2 p-2 rounded-lg text-sm ${c.is_correct ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-muted/20'}`}>
                    {c.is_correct && <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
                    <span className={c.is_correct ? 'text-emerald-400' : 'text-muted-foreground'}>{c.text_de || c.text}</span>
                  </div>
                ))}
              </div>
              {q.explanation_de && (
                <p className="mt-3 text-xs text-muted-foreground bg-muted/10 p-2 rounded-lg">{q.explanation_de}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Year distribution */}
      {data.years?.length > 0 && (
        <div className="mb-10">
          <h3 className="font-semibold mb-3">Verfügbare Prüfungsjahre</h3>
          <div className="flex flex-wrap gap-2">
            {data.years.map(y => (
              <span key={y.year} className="px-3 py-1.5 rounded-full text-xs font-mono" style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }}>
                {y.year} ({y.count} Fragen)
              </span>
            ))}
          </div>
        </div>
      )}

      {/* CTA */}
      <div className="p-8 rounded-2xl text-center" style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(59, 130, 246, 0.03))', border: '1px solid rgba(59,130,246,0.2)' }}>
        <GraduationCap className="w-10 h-10 mx-auto mb-3" style={{ color: '#3b82f6' }} />
        <h3 className="text-lg font-bold mb-2">Bereit für die Prüfung?</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Registriere dich kostenlos und erhalte Zugang zu allen {data.total_questions} {data.name_de}-Fragen
        </p>
        <div className="flex gap-3 justify-center">
          <Link to="/register">
            <Button className="gap-2" style={{ background: 'linear-gradient(135deg, #3b82f6, #60a5fa)', color: '#06081a' }} data-testid="seo-register-btn">
              <UserPlus className="w-4 h-4" /> Kostenlos registrieren
            </Button>
          </Link>
          <Link to="/guest-quiz">
            <Button variant="outline" className="gap-2" data-testid="seo-try-btn">
              Kostenlos testen <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
