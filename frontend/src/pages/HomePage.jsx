import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity,
  ArrowRight, BookOpen, Trophy, Clock, Zap, CheckCircle, BarChart3,
  Award, Target, Sparkles, Shield, FileText, Bot, TrendingUp, Layers, Pill, Crown,
} from "lucide-react";

const iconMap = {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity, Pill,
};

/* Splash */
const SplashOverlay = ({ onDone }) => {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 100);
    const t2 = setTimeout(() => setPhase(2), 1400);
    const t3 = setTimeout(() => setPhase(3), 2200);
    const t4 = setTimeout(() => onDone(), 2800);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [onDone]);

  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center transition-all duration-700 ${phase >= 3 ? "opacity-0 pointer-events-none" : "opacity-100"}`} style={{ background: "linear-gradient(135deg, #06081a 0%, #0a1128 40%, #06081a 100%)" }} data-testid="splash-overlay">
      <div className="absolute top-1/2 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.25), transparent)', transform: 'translateY(-50px)' }} />
      <div className="text-center relative">
        <div className={`transition-all duration-700 ${phase >= 1 ? "opacity-100 scale-100" : "opacity-0 scale-75"}`}>
          <img src="/logo-elite.png" alt="Prep Academy" className="w-44 h-44 mx-auto mb-6 object-contain" style={{ filter: "drop-shadow(0 0 40px rgba(201,168,76,0.25))" }} />
        </div>
        <div className={`transition-all duration-600 delay-300 ${phase >= 1 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <h1 className="text-5xl sm:text-6xl font-black tracking-tight text-white mb-3" style={{ fontFamily: "'Playfair Display', serif" }}>
            Prep<span className="ml-2" style={{ color: '#c9a84c' }}>Academy</span>
          </h1>
          <div className={`transition-all duration-500 delay-700 ${phase >= 2 ? "opacity-100" : "opacity-0"}`}>
            <p className="text-white/25 text-xs tracking-[0.4em] uppercase">Medizinische Exzellenz</p>
          </div>
        </div>
      </div>
    </div>
  );
};

/* Section label */
const SectionLabel = ({ number, text }) => (
  <div className="flex items-center gap-3 mb-6">
    <span className="text-xs font-mono tracking-widest" style={{ color: '#c9a84c' }}>{number}</span>
    <div className="w-12 h-px" style={{ background: 'rgba(201,168,76,0.3)' }} />
    <span className="text-xs tracking-[0.2em] uppercase text-white/40">{text}</span>
  </div>
);

export default function HomePage() {
  const [specialties, setSpecialties] = useState([]);
  const [examTypes, setExamTypes] = useState([]);
  const [selectedExam, setSelectedExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const [showSplash, setShowSplash] = useState(() => !sessionStorage.getItem("splashSeen"));
  const handleSplashDone = useCallback(() => { setShowSplash(false); sessionStorage.setItem("splashSeen", "1"); }, []);

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/specialties`),
      axios.get(`${API}/exam-types`),
    ]).then(([specRes, examRes]) => {
      setSpecialties(specRes.data);
      setExamTypes(examRes.data);
      // Default to first exam type with questions
      const defaultExam = examRes.data.find(e => e.question_count > 0) || examRes.data[0];
      setSelectedExam(defaultExam?.id || null);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Filter specialties based on selected exam
  const filteredSpecialties = specialties.filter(s => {
    if (!selectedExam) return true;
    const exam = examTypes.find(e => e.id === selectedExam);
    if (!exam) return true;
    if (exam.specialty) return s.id === exam.specialty;
    if (exam.location) {
      const cityCount = s.city_counts?.[exam.location] || 0;
      return cityCount > 0;
    }
    return true;
  }).map(s => {
    const exam = examTypes.find(e => e.id === selectedExam);
    if (!exam) return s;
    if (exam.location) {
      return { ...s, question_count: s.city_counts?.[exam.location] || 0 };
    }
    return s;
  });

  const totalQ = filteredSpecialties.reduce((sum, sp) => sum + (sp.question_count || 0), 0);

  return (
    <div style={{ background: '#06081a', color: '#e8e0d0' }}>
      {showSplash && <SplashOverlay onDone={handleSplashDone} />}

      {/* ═══════ SECTION 1: HERO ═══════ */}
      <section className="relative min-h-[100vh] flex items-center overflow-hidden" data-testid="hero-section">
        {/* bg effects */}
        <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 80% 60% at 70% 40%, rgba(30,58,138,0.08) 0%, transparent 70%)' }} />
        <div className="absolute top-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.15), transparent)' }} />
        <div className="absolute bottom-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.15), transparent)' }} />

        <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 py-20 w-full relative z-10">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border mb-8" style={{ borderColor: 'rgba(201,168,76,0.2)', background: 'rgba(201,168,76,0.04)' }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#c9a84c' }} />
              <span className="text-xs font-medium tracking-[0.2em] uppercase" style={{ color: '#c9a84c' }}>Medizinische Exzellenz</span>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.05] mb-4" data-testid="hero-title" style={{ fontFamily: "'Playfair Display', serif" }}>
              <span className="text-white">Prep</span>
              <span className="ml-3" style={{ color: '#c9a84c' }}>Academy</span>
            </h1>
            <p className="text-lg sm:text-xl text-white/30 tracking-[0.15em] uppercase font-light mb-10">Redefining Medical Education</p>

            <p className="text-white/50 text-lg sm:text-xl leading-relaxed mb-12 max-w-xl">
              Die fortschrittlichste Plattform für medizinische Prüfungsvorbereitung in Österreich
            </p>

            {!user ? (
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/register">
                  <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="hero-register-btn">
                    Entdecken Sie Mehr
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Link to="/guest-quiz">
                  <Button size="lg" variant="outline" className="gap-2 px-8 h-14 text-base font-semibold rounded-none tracking-wider uppercase border-[#c9a84c]/30 text-[#c9a84c] hover:bg-[#c9a84c]/10" data-testid="hero-guest-btn">
                    Kostenlos testen
                  </Button>
                </Link>
              </div>
            ) : (
              <Link to="/dashboard">
                <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                  Zum Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* ═══════ EXAM TYPE SELECTOR ═══════ */}
      <section className="relative z-20 -mt-8 pb-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6">
            <p className="text-xs tracking-[0.2em] uppercase text-white/30">Prüfung / Exam</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
            {examTypes.map((exam) => {
              const isActive = selectedExam === exam.id;
              return (
                <button
                  key={exam.id}
                  onClick={() => setSelectedExam(exam.id)}
                  data-testid={`exam-type-${exam.id}`}
                  className={`relative p-4 sm:p-5 rounded-xl border text-left transition-all duration-300 group ${
                    isActive ? 'border-[#c9a84c]/40 -translate-y-1' : 'border-white/[0.06] hover:border-white/[0.12] hover:-translate-y-0.5'
                  }`}
                  style={{
                    background: isActive ? 'rgba(201,168,76,0.06)' : 'rgba(201,168,76,0.015)',
                    boxShadow: isActive ? '0 8px 32px rgba(201,168,76,0.08)' : 'none',
                  }}
                >
                  {isActive && <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-xl" style={{ background: 'linear-gradient(90deg, transparent, #c9a84c, transparent)' }} />}
                  <div className="text-xl mb-2">
                    {exam.icon === 'flag_at' && '🇦🇹'}
                    {exam.icon === 'mountain' && '🏔️'}
                    {exam.icon === 'building' && '🏙️'}
                    {exam.icon === 'pill' && '💊'}
                  </div>
                  <h3 className={`font-semibold text-sm sm:text-base mb-1 ${isActive ? 'text-[#c9a84c]' : 'text-white/80'}`}>
                    {exam.name}
                    {isActive && <span className="ml-2 text-[#c9a84c]">✓</span>}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-white/30 leading-snug mb-2 line-clamp-2">{exam.subtitle}</p>
                  <p className="text-xs font-mono" style={{ color: isActive ? '#c9a84c' : 'rgba(255,255,255,0.25)' }}>
                    {exam.question_count.toLocaleString('de-DE')} Fragen
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 2: IDENTITÄT ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #080c22 50%, #06081a 100%)' }} />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="01" text="Identität" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Erstklassige Plattform für<br />
            <span style={{ color: '#c9a84c' }}>ambitionierte Ärzte</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 mt-16">
            {[
              { num: "01", icon: "◆", title: "Transformation", desc: "Abkehr vom rein funktionalen Design hin zu einer prestigeträchtigen Lernumgebung, die den Status eines Arztes widerspiegelt." },
              { num: "02", icon: "◈", title: "Ästhetik", desc: "Eine harmonische Kombination aus Präzision und Eleganz schafft ein Gefühl von Vertrauen und medizinischer Exzellenz." },
              { num: "03", icon: "◉", title: "Zielgruppe", desc: "Speziell entwickelt für Mediziner, die höchste Ansprüche an ihre Lernumgebung stellen." },
            ].map((item) => (
              <div key={item.num} className="p-8 rounded-2xl border transition-all duration-300 hover:-translate-y-1 group" style={{ background: 'rgba(201,168,76,0.02)', borderColor: 'rgba(201,168,76,0.08)' }}>
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-xs font-mono" style={{ color: '#c9a84c' }}>{item.num}</span>
                  <span className="text-lg" style={{ color: '#c9a84c' }}>{item.icon}</span>
                </div>
                <h3 className="text-xl font-semibold text-white mb-3 tracking-wide uppercase" style={{ fontSize: '0.85rem', letterSpacing: '0.15em' }}>{item.title}</h3>
                <p className="text-white/40 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 3: DASHBOARD / FEATURES ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #0a0e24 50%, #06081a 100%)' }} />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="02" text="Dashboard" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Intelligentes Dashboard & UX:<br />
            <span style={{ color: '#c9a84c' }}>Ästhetische Perfektion</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 mt-12">
            {[
              { icon: Shield, title: "Premium Dark Mode", desc: "Reduziert die Augenbelastung bei intensiven, stundenlangen Lernsitzungen durch harmonische Farbwahl." },
              { icon: Layers, title: "Glassmorphism-Design", desc: "Moderne, halbtransparente Widgets sorgen für eine klare und ästhetisch ansprechende Informationsarchitektur." },
              { icon: Target, title: "Benutzererfahrung", desc: "Ein flüssiges Interface minimiert Ablenkungen und maximiert den Fokus auf medizinische Inhalte." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={i} className="p-6 rounded-xl border transition-all duration-300 hover:-translate-y-1" style={{ background: 'rgba(30,58,138,0.04)', borderColor: 'rgba(30,58,138,0.1)' }}>
                  <Icon className="w-6 h-6 mb-4" style={{ color: '#c9a84c' }} />
                  <h3 className="text-white font-semibold mb-2">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Dashboard mockup card */}
          <div className="mt-16 p-8 rounded-2xl border" style={{ background: 'rgba(201,168,76,0.02)', borderColor: 'rgba(201,168,76,0.08)' }}>
            <div className="flex items-center gap-3 mb-6">
              <span className="text-xs font-mono tracking-widest" style={{ color: '#c9a84c' }}>PREP ACADEMY</span>
              <span style={{ color: '#c9a84c' }}>◆</span>
              <span className="text-xs text-white/30">DASHBOARD</span>
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold text-white">{totalQ > 0 ? `${totalQ}` : '2395'}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fragen Gesamt</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold text-white">{filteredSpecialties.filter(s => s.question_count > 0).length || 0}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fachgebiete</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold" style={{ color: '#c9a84c' }}>AI</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">KI-Erklärungen</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 4: KI / AI ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #080c22 50%, #06081a 100%)' }} />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="03" text="Künstliche Intelligenz" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            KI-gestützte Analysen:<br />
            <span style={{ color: '#c9a84c' }}>Präzise Erfolgsplanung</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-8 mt-16">
            {[
              { num: "01", icon: Bot, title: "Personalisierter KI-Tutor", desc: "Maßgeschneiderte medizinische Erklärungen, die sich Ihrem Wissensstand anpassen." },
              { num: "02", icon: BarChart3, title: "Echtzeit-Statistiken", desc: "Detaillierte Visualisierung von Stärken und Schwächen durch intelligente Datenanalyse." },
              { num: "03", icon: Zap, title: "Effizienz", desc: "Automatisierte, dynamische Lernpläne, die den Lernweg optimieren und die Zeit bis zum Prüfungserfolg verkürzen." },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className="relative p-8">
                  <div className="flex items-center gap-2 mb-6">
                    <span style={{ color: '#c9a84c' }}>◆</span>
                    <span className="text-xs font-mono" style={{ color: '#c9a84c' }}>{item.num}</span>
                  </div>
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6" style={{ background: 'rgba(201,168,76,0.06)', border: '1px solid rgba(201,168,76,0.1)' }}>
                    <Icon className="w-7 h-7" style={{ color: '#c9a84c' }} />
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-3">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 5: FACHGEBIETE (Specialties) ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #0a0e24 50%, #06081a 100%)' }} />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="04" text="Fachgebiete" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Medizinische<br />
            <span style={{ color: '#c9a84c' }}>Fachgebiete</span>
          </h2>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(9)].map((_, i) => <div key={i} className="h-24 rounded-xl animate-pulse" style={{ background: 'rgba(201,168,76,0.03)' }} />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSpecialties.map((specialty, index) => {
                const IconComponent = iconMap[specialty.icon] || BookOpen;
                const exam = examTypes.find(e => e.id === selectedExam);
                const locParam = exam?.location ? `?exam_location=${exam.location}` : '';
                return (
                  <Link key={specialty.id} to={user ? `/specialty/${specialty.id}${locParam}` : "/login"} data-testid={`specialty-card-${specialty.id}`}>
                    <div className="p-5 rounded-xl border group cursor-pointer transition-all duration-300 hover:-translate-y-1" style={{ background: 'rgba(201,168,76,0.02)', borderColor: 'rgba(201,168,76,0.06)' }}>
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(201,168,76,0.06)' }}>
                          <IconComponent className="w-6 h-6" style={{ color: '#c9a84c' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-white text-sm truncate">{specialty.name_de}</h3>
                          <p className="text-xs text-white/30 font-mono">{specialty.question_count} Fragen</p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-white/10 group-hover:text-white/40 transition-colors flex-shrink-0" />
                      </div>
                    </div>
                  </Link>
                );
              })}
              {filteredSpecialties.length === 0 && !loading && (
                <div className="col-span-full text-center py-12">
                  <p className="text-white/30 text-sm">Noch keine Fragen für diese Prüfung vorhanden</p>
                </div>
              )}
            </div>
          )}

          {/* Exam Simulation CTA */}
          {user && (
            <Link to="/exam-simulation" className="block mt-12">
              <div className="p-6 sm:p-8 rounded-xl border group cursor-pointer transition-all duration-300 hover:-translate-y-1 flex items-center justify-between" style={{ background: 'rgba(201,168,76,0.03)', borderColor: 'rgba(201,168,76,0.1)' }} data-testid="exam-simulation-cta">
                <div className="flex items-center gap-5">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.08)' }}>
                    <Clock className="w-7 h-7" style={{ color: '#c9a84c' }} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Prüfungssimulation</h3>
                    <p className="text-white/30 text-sm">250 Fragen · 4 Stunden · 60% zum Bestehen</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-white/20 group-hover:text-white/60 transition-colors" />
              </div>
            </Link>
          )}
        </div>
      </section>

      {/* ═══════ SECTION 6: ROADMAP ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #080c22 50%, #06081a 100%)' }} />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="05" text="Roadmap" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Roadmap zur Transformation:<br />
            <span style={{ color: '#c9a84c' }}>Schritte zur Marktführerschaft</span>
          </h2>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: "01", title: "Rebranding", desc: "Einführung der neuen prestigeträchtigen visuellen Identität für PrepAcademy." },
              { step: "02", title: "Premium Launch", desc: "Veröffentlichung des neuen Dashboards mit voller Unterstützung für alle Module." },
              { step: "03", title: "Expansion", desc: "Etablierung als führende Plattform für medizinische Zertifizierungen in Europa." },
              { step: "04", title: "Marktführerschaft", desc: "Position als unangefochtener Standard für medizinische Ausbildung in Österreich." },
            ].map((item) => (
              <div key={item.step} className="relative p-6 rounded-xl border transition-all duration-300 hover:-translate-y-1" style={{ background: 'rgba(201,168,76,0.02)', borderColor: 'rgba(201,168,76,0.06)' }}>
                <div className="text-5xl font-bold mb-4" style={{ color: 'rgba(201,168,76,0.08)' }}>{item.step}</div>
                <h3 className="font-semibold text-white mb-2 uppercase text-sm tracking-wider">{item.title}</h3>
                <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 6.5: PRICING ═══════ */}
      <section className="py-24 sm:py-32 relative" id="pricing">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #06081a 0%, #080c22 50%, #06081a 100%)' }} />
        <div className="max-w-5xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="06" text="Preise" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Einfache, transparente<br />
            <span style={{ color: '#c9a84c' }}>Preisgestaltung</span>
          </h2>
          <p className="text-white/40 mb-16 max-w-xl">Starten Sie kostenlos. Upgraden Sie wenn Sie bereit sind.</p>

          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {/* Free */}
            <div className="p-8 rounded-2xl border" style={{ background: 'rgba(201,168,76,0.02)', borderColor: 'rgba(201,168,76,0.08)' }}>
              <div className="text-xs font-mono tracking-widest text-white/30 uppercase mb-4">Free</div>
              <div className="text-4xl font-bold text-white mb-1">€0</div>
              <p className="text-sm text-white/30 mb-8">Für immer kostenlos</p>
              <ul className="space-y-3 mb-8">
                {[
                  "5 KI-Analysen pro Tag",
                  "3 PDF-Uploads pro Tag",
                  "Unbegrenzter Quiz-Zugang",
                  "Grundlegende Statistiken",
                  "Tägliche Podcasts",
                ].map(f => (
                  <li key={f} className="flex items-center gap-3 text-sm text-white/50">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#c9a84c' }} />
                    {f}
                  </li>
                ))}
              </ul>
              {!user ? (
                <Link to="/register" className="block">
                  <button className="w-full py-3 rounded-xl border text-sm font-semibold text-white/60 hover:text-white hover:border-white/20 transition-all" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                    Kostenlos starten
                  </button>
                </Link>
              ) : (
                <Link to="/dashboard" className="block">
                  <button className="w-full py-3 rounded-xl border text-sm font-semibold text-white/40 cursor-default" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                    Aktueller Plan ✓
                  </button>
                </Link>
              )}
            </div>

            {/* Premium */}
            <div className="p-8 rounded-2xl border relative overflow-hidden" style={{ background: 'rgba(201,168,76,0.04)', borderColor: 'rgba(201,168,76,0.2)' }}>
              <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: 'linear-gradient(90deg, transparent, #c9a84c, transparent)' }} />
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs font-mono tracking-widest uppercase" style={{ color: '#c9a84c' }}>Premium</span>
                <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c' }}>Beliebt</span>
              </div>
              <div className="text-4xl font-bold text-white mb-1">€14,99<span className="text-lg text-white/30 font-normal">/Monat</span></div>
              <p className="text-sm text-white/30 mb-8">oder €69 für 6 Monate (23% sparen)</p>
              <ul className="space-y-3 mb-8">
                {[
                  "Unbegrenzte KI-Analysen",
                  "Unbegrenzte PDF-Uploads",
                  "Prioritäts-KI-Verarbeitung",
                  "Erweiterte Statistiken",
                  "Prüfungs-Simulationen",
                  "Premium AI-Modelle",
                ].map(f => (
                  <li key={f} className="flex items-center gap-3 text-sm text-white/70">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#c9a84c' }} />
                    {f}
                  </li>
                ))}
              </ul>
              <Link to={user ? "/billing" : "/register"} className="block">
                <button className="w-full py-3 rounded-xl text-sm font-semibold transition-all hover:-translate-y-0.5" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                  {user ? "Jetzt upgraden" : "Jetzt starten"}
                </button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 7: FAZIT / CTA ═══════ */}
      <section className="py-24 sm:py-32 relative">
        <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(201,168,76,0.03) 0%, transparent 70%)' }} />
        <div className="max-w-4xl mx-auto px-6 sm:px-10 lg:px-16 text-center relative z-10">
          <div className="flex items-center justify-center gap-2 mb-8">
            <span style={{ color: '#c9a84c' }}>◆</span>
            <span className="text-xs tracking-[0.2em] uppercase text-white/30">Fazit — Ihre professionelle Zukunft</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Ihre berufliche<br />
            <span style={{ color: '#c9a84c' }}>Zukunft beginnt hier</span>
          </h2>

          <p className="text-white/40 text-lg leading-relaxed mb-12 max-w-2xl mx-auto">
            Prep Academy ist Ihr strategischer Partner für den Erfolg in der österreichischen Medizinwelt. Nutzen Sie die fortschrittlichste Technologie für Ihre medizinische Karriere.
          </p>

          <div className="flex items-center justify-center gap-8 mb-12 text-xs tracking-[0.2em] uppercase text-white/20">
            <span>Partnerschaft</span>
            <span>Wettbewerbsvorteil</span>
            <span>Excellence</span>
          </div>

          {!user ? (
            <Link to="/register">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="cta-register-btn">
                Jetzt Starten
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          ) : (
            <Link to="/dashboard">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                Zum Dashboard
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}
