import { useState, useEffect, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity,
  ArrowRight, BookOpen, Clock, CheckCircle,
  Target, Shield, FileText, Bot, Layers, Pill,
} from "lucide-react";
import { toast } from "sonner";

const iconMap = {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity, Pill,
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
  const [fetchError, setFetchError] = useState(null);
  const { user, token } = useAuth();
  const [requestingAccess, setRequestingAccess] = useState(false);

  const loadHomepageData = useCallback(() => {
    setFetchError(null);
    setLoading(false);

    axios.get(`${API}/specialties`)
      .then(res => setSpecialties(res.data))
      .catch(() => {});

    axios.get(`${API}/exam-types`)
      .then(res => {
        setExamTypes(res.data);
        const exams = Array.isArray(res.data) ? res.data : [];
        const defaultExam = exams.find(e => e.question_count > 0) || exams[0];
        setSelectedExam(prev => prev || defaultExam?.id || null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => { loadHomepageData(); }, [loadHomepageData]);

  const requestAdvancedAccess = async () => {
    if (!token) { toast.error("Bitte melden Sie sich an"); return; }
    setRequestingAccess(true);
    try {
      await axios.post(`${API}/access-requests`,
        { feature_pack: "advanced_features" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Anfrage gesendet");
    } catch (err) {
      const detail = err.response?.data?.detail || "Fehler beim Senden";
      if (detail && detail.includes("ausstehende Anfrage")) {
        toast.success("Anfrage bereits gesendet");
      } else {
        toast.error(detail);
      }
    } finally {
      setRequestingAccess(false);
    }
  };

  // Memoize filtered specialties to avoid recalculation on unrelated re-renders
  const filteredSpecialties = useMemo(() => {
    return specialties.filter(s => {
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
  }, [specialties, examTypes, selectedExam]);

  const totalQ = useMemo(() => filteredSpecialties.reduce((sum, sp) => sum + (sp.question_count || 0), 0), [filteredSpecialties]);
  const totalAvailableQuestions = useMemo(() => specialties.reduce((sum, sp) => sum + (sp.question_count || 0), 0), [specialties]);
  const activeSpecialtyCount = useMemo(() => specialties.filter(sp => (sp.question_count || 0) > 0).length, [specialties]);

  const displayNumber = useCallback((value) => {
    if (loading) return "...";
    return value > 0 ? value.toLocaleString("de-DE") : "Live";
  }, [loading]);

  return (
    <div style={{ background: '#06081a', color: '#e8e0d0' }}>
      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 1: HERO ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <section className="relative min-h-[100vh] flex items-center overflow-hidden bg-premium-dark" data-testid="hero-section">

        {/* Content */}
        <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 py-20 w-full relative z-10">
          <div className="max-w-xl lg:max-w-lg">
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border mb-10 sm:mb-12"
              style={{ borderColor: 'rgba(201,168,76,0.18)', background: 'rgba(201,168,76,0.04)' }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#c9a84c', boxShadow: '0 0 6px rgba(201,168,76,0.4)' }} />
              <span className="text-xs font-medium tracking-[0.22em] uppercase" style={{ color: '#c9a84c' }}>Medizinische Exzellenz</span>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold leading-[1.05] mb-6 sm:mb-7 hero-title-mobile"
              data-testid="hero-title"
              style={{ fontFamily: "'Playfair Display', serif", letterSpacing: '-0.02em' }}>
              <span className="text-white">Prep</span>
              <span className="ml-3 sm:ml-4" style={{ color: '#c9a84c' }}>Academy</span>
            </h1>

            <p className="text-base sm:text-lg tracking-[0.18em] uppercase font-light mb-6"
              style={{ color: 'rgba(232,224,208,0.45)' }}>Klar. Pr├ñzise. KI-gest├╝tzt.</p>

            <p className="text-white/55 text-base sm:text-lg leading-relaxed mb-10 max-w-lg">
              Medizinische Pr├╝fungsvorbereitung f├╝r ├ûsterreich und Deutschland: echte Fragen, KI-Erkl├ñrungen, Analyzer, PDF-Notebook und 30 Tage Testphase.
            </p>

            <div className="flex flex-wrap gap-3 mb-10">
              {["30 Tage kostenlos testen", "Medical Analyzer", "PDF Notebook"].map((item) => (
                <span key={item} className="px-4 py-2 rounded-full border text-xs tracking-[0.12em] uppercase font-medium"
                  style={{ borderColor: 'rgba(201,168,76,0.14)', background: 'rgba(201,168,76,0.03)', color: 'rgba(232,224,208,0.5)' }}>
                  {item}
                </span>
              ))}
            </div>

            {!user ? (
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/guest-quiz">
                  <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow"
                    style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="hero-guest-btn">
                    Kostenlos testen
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="lg" variant="outline" className="gap-2 px-8 h-14 text-base font-semibold rounded-none tracking-wider uppercase border-[#c9a84c]/30 text-[#c9a84c] hover:bg-[#c9a84c]/10" data-testid="hero-register-btn">
                    Konto erstellen
                  </Button>
                </Link>
              </div>
            ) : (
              <Link to="/dashboard">
                <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow"
                  style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                  Zum Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.25), rgba(201,168,76,0.12), transparent)' }} />
      </section>

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ EXAM TYPE SELECTOR ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <section className="relative z-20 -mt-8 pb-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6">
            <p className="text-xs tracking-[0.2em] uppercase text-white/30">Pr├╝fung / Exam</p>
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
                    {exam.icon === 'flag_at' && '­ƒçª­ƒç╣'}
                    {exam.icon === 'mountain' && '­ƒÅö´©Å'}
                    {exam.icon === 'building' && '­ƒÅÖ´©Å'}
                    {exam.icon === 'pill' && '­ƒÆè'}
                  </div>
                  <h3 className={`font-semibold text-sm sm:text-base mb-1 ${isActive ? 'text-[#c9a84c]' : 'text-white/80'}`}>
                    {exam.name}
                    {isActive && <span className="ml-2 text-[#c9a84c]">Ô£ô</span>}
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

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 2: LERNEN ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="01" text="Lernen" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Wie du lernst:<br />
            <span style={{ color: '#c9a84c' }}>strukturiert, klar, Schritt f├╝r Schritt</span>
          </h2>
          <p className="text-white/40 text-base sm:text-lg leading-relaxed max-w-xl mb-16">
            W├ñhle dein Fachgebiet, beantworte originale Pr├╝fungsfragen und vertiefe mit KI-Erkl├ñrungen ÔÇö in deinem Tempo, mit direktem Feedback.
          </p>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8">
            {[
              { num: "01", icon: BookOpen, title: "Fachgebiet w├ñhlen", desc: "MedAT, ├ûSDK oder deutsche Pr├╝fungsordnung ÔÇö w├ñhle deine Pr├╝fung und starte mit passgenauen Fragen." },
              { num: "02", icon: Activity, title: "Fragen beantworten", desc: "Originalgetreue Pr├╝fungsfragen mit sofortiger Auswertung. Jede Antwort z├ñhlt f├╝r deinen Fortschritt." },
              { num: "03", icon: Bot, title: "KI-Erkl├ñrungen", desc: "Verstehe jede Frage mit detaillierten KI-generierten Erkl├ñrungen ÔÇö als Text oder Audio." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <span style={{ color: '#c9a84c' }}>Ôùå</span>
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

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 3: DASHBOARD ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="02" text="Dashboard" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Dein<br />
            <span style={{ color: '#c9a84c' }}>digitaler Lernkompass</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 mt-12">
            {[
              { icon: Shield, title: "Datenschutz & Sicherheit", desc: "Deine Daten bleiben vertraulich. Keine Werbung, kein Tracking. Fokussiertes Lernen in einer gesch├╝tzten Umgebung." },
              { icon: Layers, title: "Klare Lernstruktur", desc: "Fachgebiete, Pr├╝fungsorte und Lernwerkzeuge bleiben schnell auffindbar." },
              { icon: Target, title: "Fortschritt im Blick", desc: "Statistiken und Lernziele zeigen, wo du sicher bist und wo Wiederholung lohnt." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={i} className={`card-premium-alt p-6 section-enter-delay-${i + 1}`}>
                  <Icon className="w-6 h-6 mb-4" style={{ color: '#c9a84c' }} />
                  <h3 className="text-white font-semibold mb-2">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Dashboard mockup card */}
          <div className="mt-16 card-premium p-8 gold-border-top">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-xs font-mono tracking-widest" style={{ color: '#c9a84c' }}>PREP ACADEMY</span>
              <span style={{ color: '#c9a84c' }}>Ôùå</span>
              <span className="text-xs text-white/30">DASHBOARD</span>
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold text-white">{displayNumber(totalAvailableQuestions || totalQ)}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fragen Gesamt</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold text-white">{displayNumber(activeSpecialtyCount || (Array.isArray(filteredSpecialties) ? filteredSpecialties.filter(s => s.question_count > 0).length : 0))}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fachgebiete</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.08)' }}>
                <div className="text-4xl font-bold" style={{ color: '#c9a84c' }}>AI</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">KI-Erkl├ñrungen</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 4: KI / AI ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="03" text="K├╝nstliche Intelligenz" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            KI-Werkzeuge f├╝r<br />
            <span style={{ color: '#c9a84c' }}>Fragen, Bilder und PDFs</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 mt-16">
            {[
              { num: "01", icon: Bot, title: "KI-Erkl├ñrungen", desc: "Direkte Erkl├ñrungen zu Pr├╝fungsfragen, damit du nicht nur klickst, sondern verstehst." },
              { num: "02", icon: Activity, title: "Medical Analyzer", desc: "Analyse medizinischer Bilder mit mehrstufigem KI-Fallback f├╝r sichere Einsch├ñtzungen." },
              { num: "03", icon: FileText, title: "PDF Notebook", desc: "Aus Skripten und PDFs entstehen Lernkarten, Zusammenfassungen, Audio und MindMaps." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <span style={{ color: '#c9a84c' }}>Ôùå</span>
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

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 5: FACHGEBIETE (Specialties) ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="04" text="Fachgebiete" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 leading-tight heading-premium">
            Medizinische<br />
            <span style={{ color: '#c9a84c' }}>Fachgebiete</span>
          </h2>

          {fetchError ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-white/40">Verbindungsfehler ÔÇö Fachgebiete konnten nicht geladen werden</p>
              <button onClick={loadHomepageData} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium text-white/60 hover:text-white hover:border-white/20 transition-all" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                Erneut versuchen
              </button>
            </div>
          ) : specialties.length === 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => <div key={i} className="min-h-[116px] rounded-xl animate-pulse" style={{ background: 'rgba(201,168,76,0.03)' }} />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSpecialties.map((specialty, index) => {
                const IconComponent = iconMap[specialty.icon] || BookOpen;
                const exam = examTypes.find(e => e.id === selectedExam);
                const locParam = exam?.location ? `?exam_location=${exam.location}` : '';
                return (
                  <Link key={specialty.id} to={user ? `/specialty/${specialty.id}${locParam}` : "/login"} data-testid={`specialty-card-${specialty.id}`}>
                    <div className="card-premium p-5 group cursor-pointer">
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
                  <p className="text-white/30 text-sm">Noch keine Fragen f├╝r diese Pr├╝fung vorhanden</p>
                </div>
              )}
            </div>
          )}

          {/* Exam Simulation CTA */}
          {user && (
            <Link to="/exam-simulation" className="block mt-12">
              <div className="card-premium card-raised p-6 sm:p-8 group cursor-pointer flex items-center justify-between" data-testid="exam-simulation-cta">
                <div className="flex items-center gap-5">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.08)' }}>
                    <Clock className="w-7 h-7" style={{ color: '#c9a84c' }} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Pr├╝fungssimulation</h3>
                    <p className="text-white/30 text-sm">250 Fragen ┬À 4 Stunden ┬À 60% zum Bestehen</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-white/20 group-hover:text-white/60 transition-colors" />
              </div>
            </Link>
          )}
        </div>
      </section>

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 6: MODULE ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="05" text="Module" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 heading-premium">
            Mehr als ein Quiz:<br />
            <span style={{ color: '#c9a84c' }}>ein medizinischer Lernraum</span>
          </h2>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: "01", title: "Quiz", desc: "Fachbezogene Pr├╝fungsvorbereitung mit echten medizinischen Fragen." },
              { step: "02", title: "Analyzer", desc: "Medizinische Bildanalyse als zus├ñtzliches Werkzeug f├╝r klinisches Denken." },
              { step: "03", title: "Notebook", desc: "PDFs in strukturierte Lernkarten, Zusammenfassungen und Audio verwandeln." },
              { step: "04", title: "Podcast", desc: "T├ñgliche Wiederholung als kompakte medizinische Audio-Lerneinheit." },
            ].map((item, i) => (
              <div key={item.step} className={`card-premium p-6 section-enter-delay-${i + 1}`}>
                <div className="text-5xl font-bold mb-4" style={{ color: 'rgba(201,168,76,0.08)' }}>{item.step}</div>
                <h3 className="font-semibold text-white mb-2 uppercase text-sm tracking-wider">{item.title}</h3>
                <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 6.5: ZUGANG ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter" id="pricing">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-5xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="06" text="Zugang" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Medizinisches Lernen<br />
            <span style={{ color: '#c9a84c' }}>kostenlos f├╝r alle</span>
          </h2>
          <p className="text-white/40 mb-16 max-w-xl">Registrieren Sie sich kostenlos und starten Sie sofort. Neue Nutzer erhalten 30 Tage Testphase f├╝r die erweiterten Lernfunktionen; danach werden Zug├ñnge gezielt freigeschaltet.</p>

          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {/* Free for all */}
            <div className="card-premium p-8">
              <div className="text-xs font-mono tracking-widest text-white/30 uppercase mb-4">F├╝r alle</div>
              <div className="text-4xl font-bold text-white mb-1">Kostenlos</div>
              <p className="text-sm text-white/30 mb-8">Nach Registrierung sofort verf├╝gbar</p>
              <ul className="space-y-3 mb-8">
                {[
                  "Study Mode frei nutzbar",
                  "30 Tage Testphase f├╝r Lernfunktionen",
                  "Fortschrittsstatistiken",
                  "T├ñgliche Lernziele",
                  "Dunkelmodus & mobile Ansicht",
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
                    Kostenlos registrieren
                  </button>
                </Link>
              ) : (
                <Link to="/dashboard" className="block">
                  <button className="w-full py-3 rounded-xl border text-sm font-semibold text-white/40 cursor-default" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                    Bereits registriert Ô£ô
                  </button>
                </Link>
              )}
            </div>

            {/* Admin-gated */}
            <div className="card-premium p-8 gold-border-top">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs font-mono tracking-widest uppercase" style={{ color: '#c9a84c' }}>Erweiterte Funktionen</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">Auf Anfrage</div>
              <p className="text-sm text-white/30 mb-8">Freischaltung durch Administrator</p>
              <ul className="space-y-3 mb-8">
                {[
                  "Medizinische Bildanalyse (Analyzer)",
                  "Notebook ÔÇö PDF zu Lernkarten & Audio",
                  "T├ñglicher Medizin-Podcast",
                  "Hierarchische Wissensvernetzung",
                  "Audio-Zusammenfassungen & MindMaps",
                ].map(f => (
                  <li key={f} className="flex items-center gap-3 text-sm text-white/70">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#c9a84c' }} />
                    {f}
                  </li>
                ))}
              </ul>
              <button onClick={requestAdvancedAccess} disabled={requestingAccess}
                className="w-full py-3 rounded-xl text-sm font-semibold transition-all hover:-translate-y-0.5 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
                {requestingAccess ? "Wird gesendetÔÇª" : "Zugang anfragen"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ SECTION 7: FAZIT / CTA ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 bg-premium-dark" />
        <div className="absolute inset-0 section-glow-center" />
        <div className="absolute top-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.1), transparent)' }} />
        <div className="max-w-4xl mx-auto px-6 sm:px-10 lg:px-16 text-center relative z-10">
          <div className="flex items-center justify-center gap-2 mb-8">
            <span style={{ color: '#c9a84c' }}>Ôùå</span>
            <span className="text-xs tracking-[0.2em] uppercase text-white/30">Fazit ÔÇö Ihre professionelle Zukunft</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Ihre berufliche<br />
            <span style={{ color: '#c9a84c' }}>Zukunft beginnt hier</span>
          </h2>

          <p className="text-white/40 text-lg leading-relaxed mb-12 max-w-2xl mx-auto">
            Prep Academy ist Ihr strategischer Partner f├╝r den Erfolg in der ├Âsterreichischen Medizinwelt. Nutzen Sie die fortschrittlichste Technologie f├╝r Ihre medizinische Karriere.
          </p>

          <div className="flex items-center justify-center gap-8 mb-12 text-xs tracking-[0.2em] uppercase text-white/20">
            <span>Partnerschaft</span>
            <span>Wettbewerbsvorteil</span>
            <span>Excellence</span>
          </div>

          {!user ? (
            <Link to="/register">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="cta-register-btn">
                Jetzt Starten
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          ) : (
            <Link to="/dashboard">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
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


