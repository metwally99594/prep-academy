import { useState, useEffect, useCallback } from "react";
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
  const [fetchError, setFetchError] = useState(null);
  const { user, token } = useAuth();
  const [requestingAccess, setRequestingAccess] = useState(false);
  const [showSplash, setShowSplash] = useState(() => !sessionStorage.getItem("splashSeen"));
  const handleSplashDone = useCallback(() => { setShowSplash(false); sessionStorage.setItem("splashSeen", "1"); }, []);

  const loadHomepageData = useCallback(() => {
    setLoading(true);
    setFetchError(null);
    Promise.all([
      axios.get(`${API}/specialties`),
      axios.get(`${API}/exam-types`),
    ]).then(([specRes, examRes]) => {
      const specs = Array.isArray(specRes.data) ? specRes.data : [];
      const exams = Array.isArray(examRes.data) ? examRes.data : [];
      if (process.env.NODE_ENV === "development") {
        if (!Array.isArray(specRes.data)) console.warn("[HomePage] /specialties returned non-array", specRes.data);
        if (!Array.isArray(examRes.data)) console.warn("[HomePage] /exam-types returned non-array", examRes.data);
      }
      setSpecialties(specs);
      setExamTypes(exams);
      const defaultExam = exams.find(e => e.question_count > 0) || exams[0];
      setSelectedExam(defaultExam?.id || null);
    }).catch(err => {
      if (process.env.NODE_ENV === "development") console.error("[HomePage] bootstrap failed", err);
      setFetchError(err?.message || "Fehler beim Laden");
    }).finally(() => setLoading(false));
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
      toast.error(detail);
    } finally {
      setRequestingAccess(false);
    }
  };

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
  const totalAvailableQuestions = specialties.reduce((sum, sp) => sum + (sp.question_count || 0), 0);
  const activeSpecialtyCount = specialties.filter(sp => (sp.question_count || 0) > 0).length;
  const displayNumber = (value) => {
    if (loading) return "...";
    return value > 0 ? value.toLocaleString("de-DE") : "Live";
  };

  return (
    <div style={{ background: '#06081a', color: '#e8e0d0' }}>
      {showSplash && <SplashOverlay onDone={handleSplashDone} />}

      {/* ═══════ SECTION 1: HERO ═══════ */}
      <section className="relative min-h-[100vh] flex items-center overflow-hidden bg-premium-dark" data-testid="hero-section">
        <div className="absolute inset-0 hero-glow" />
        <div className="absolute inset-0 vignette-overlay" />
        <div className="absolute top-4 left-[20%] w-[35%] h-px light-streak" />
        <div className="absolute top-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.15), transparent)' }} />
        <div className="absolute bottom-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.15), transparent)' }} />

        <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 60% 40% at 80% 50%, rgba(30,64,175,0.06) 0%, transparent 70%)' }} />

        {/* SVG wireframe — right side */}
        <div className="hero-wireframe" aria-hidden="true">
          <svg viewBox="0 0 500 600" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
            <g opacity="0.15" stroke="rgba(201,168,76,0.3)" strokeWidth="0.5">
              <circle cx="250" cy="300" r="180" />
              <circle cx="250" cy="300" r="120" />
              <circle cx="250" cy="300" r="60" />
              <line x1="250" y1="120" x2="250" y2="480" />
              <line x1="70" y1="300" x2="430" y2="300" />
              <ellipse cx="250" cy="300" rx="200" ry="240" strokeDasharray="4 4" />
            </g>
            <g opacity="0.08" stroke="rgba(255,255,255,0.15)" strokeWidth="0.3">
              <path d="M250 120 L280 180 L320 200 L350 260 L400 280" />
              <path d="M250 480 L220 420 L180 400 L150 340 L100 320" />
              <path d="M70 300 L130 280 L160 240 L200 220 L250 200" />
              <path d="M430 300 L370 320 L340 360 L300 380 L250 400" />
            </g>
            <g opacity="0.06" fill="rgba(201,168,76,0.4)">
              <circle cx="250" cy="300" r="3" />
              <circle cx="250" cy="180" r="2" />
              <circle cx="250" cy="420" r="2" />
              <circle cx="160" cy="300" r="2" />
              <circle cx="340" cy="300" r="2" />
              <circle cx="190" cy="230" r="1.5" />
              <circle cx="310" cy="370" r="1.5" />
              <circle cx="310" cy="230" r="1.5" />
              <circle cx="190" cy="370" r="1.5" />
            </g>
            <g opacity="0.04" stroke="rgba(201,168,76,0.2)" strokeWidth="0.3" strokeDasharray="2 3">
              <rect x="100" y="160" width="80" height="50" rx="4" />
              <rect x="320" y="380" width="80" height="50" rx="4" />
              <rect x="140" y="400" width="60" height="40" rx="3" />
              <rect x="300" y="140" width="60" height="40" rx="3" />
            </g>
            <g opacity="0.03" stroke="rgba(30,64,175,0.3)" strokeWidth="0.5">
              <path d="M250 120 Q300 150 300 200" />
              <path d="M250 480 Q200 450 200 400" />
              <path d="M70 300 Q100 250 150 250" />
              <path d="M430 300 Q400 350 350 350" />
            </g>
          </svg>
        </div>

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
            <p className="text-lg sm:text-xl tracking-[0.15em] uppercase font-light mb-8 text-premium" style={{ opacity: 0.35 }}>Klar. Präzise. KI-gestützt.</p>

            <p className="text-white/55 text-lg sm:text-xl leading-relaxed mb-8 max-w-xl">
              Medizinische Prüfungsvorbereitung für Österreich und Deutschland: echte Fragen, KI-Erklärungen, Analyzer, PDF-Notebook und 30 Tage Testphase.
            </p>

            <div className="flex flex-wrap gap-2 mb-8 max-w-xl">
              {["30 Tage kostenlos testen", "Medical Analyzer", "PDF Notebook"].map((item) => (
                <span key={item} className="px-3 py-1.5 rounded-full border text-xs tracking-[0.12em] uppercase" style={{ borderColor: 'rgba(201,168,76,0.14)', background: 'rgba(201,168,76,0.035)', color: 'rgba(232,224,208,0.45)' }}>
                  {item}
                </span>
              ))}
            </div>

            {!user ? (
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/guest-quiz">
                  <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }} data-testid="hero-guest-btn">
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
                <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-gold-glow" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>
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

      {/* ═══════ SECTION 2: LERNEN ═══════ */}
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="01" text="Lernen" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 heading-premium">
            Fokus für deine nächste<br />
            <span style={{ color: '#c9a84c' }}>medizinische Prüfung</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 mt-16">
            {[
              { num: "01", icon: "◆", title: "Prüfungsfragen", desc: "Trainiere mit medizinischen Fragen nach Fachgebiet, Stadt und Prüfungskontext." },
              { num: "02", icon: "◈", title: "KI-Erklärungen", desc: "Verstehe richtige und falsche Antworten mit klaren, medizinisch fokussierten Erklärungen." },
              { num: "03", icon: "◉", title: "30 Tage Trial", desc: "Neue Nutzer testen die Lernfunktionen 30 Tage lang, bevor Zugänge gezielt freigeschaltet werden." },
            ].map((item, i) => (
              <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-xs font-mono" style={{ color: '#c9a84c' }}>{item.num}</span>
                  <span className="text-lg" style={{ color: '#c9a84c' }}>{item.icon}</span>
                </div>
                <h3 className="font-semibold text-white mb-3 tracking-wide uppercase" style={{ fontSize: '0.85rem', letterSpacing: '0.15em' }}>{item.title}</h3>
                <p className="text-white/40 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 3: DASHBOARD / FEATURES ═══════ */}
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="02" text="Dashboard" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 heading-premium">
            Ruhiges Dashboard für<br />
            <span style={{ color: '#c9a84c' }}>lange Lernsessions</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 mt-12">
            {[
              { icon: Shield, title: "Premium Dark Mode", desc: "Eine ruhige Oberfläche für lange, konzentrierte Lernsessions." },
              { icon: Layers, title: "Klare Lernstruktur", desc: "Fachgebiete, Prüfungsorte und Lernwerkzeuge bleiben schnell auffindbar." },
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
              <span style={{ color: '#c9a84c' }}>◆</span>
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
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">KI-Erklärungen</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 4: KI / AI ═══════ */}
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="03" text="Künstliche Intelligenz" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 heading-premium">
            KI-Werkzeuge für<br />
            <span style={{ color: '#c9a84c' }}>Fragen, Bilder und PDFs</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-8 mt-16">
            {[
              { num: "01", icon: Bot, title: "KI-Erklärungen", desc: "Direkte Erklärungen zu Prüfungsfragen, damit du nicht nur klickst, sondern verstehst." },
              { num: "02", icon: Activity, title: "Medical Analyzer", desc: "Analyse medizinischer Bilder mit mehrstufigem KI-Fallback für sichere Einschätzungen." },
              { num: "03", icon: FileText, title: "PDF Notebook", desc: "Aus Skripten und PDFs entstehen Lernkarten, Zusammenfassungen, Audio und MindMaps." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
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
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="04" text="Fachgebiete" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
            Medizinische<br />
            <span style={{ color: '#c9a84c' }}>Fachgebiete</span>
          </h2>

          {fetchError && !loading ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-white/40">Verbindungsfehler — Fachgebiete konnten nicht geladen werden</p>
              <button onClick={loadHomepageData} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium text-white/60 hover:text-white hover:border-white/20 transition-all" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                Erneut versuchen
              </button>
            </div>
          ) : loading ? (
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
                  <p className="text-white/30 text-sm">Noch keine Fragen für diese Prüfung vorhanden</p>
                </div>
              )}
            </div>
          )}

          {/* Exam Simulation CTA */}
          {user && (
            <Link to="/exam-simulation" className="block mt-12">
              <div className="card-premium p-6 sm:p-8 group cursor-pointer flex items-center justify-between" data-testid="exam-simulation-cta">
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

      {/* ═══════ SECTION 6: MODULE ═══════ */}
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
              { step: "01", title: "Quiz", desc: "Fachbezogene Prüfungsvorbereitung mit echten medizinischen Fragen." },
              { step: "02", title: "Analyzer", desc: "Medizinische Bildanalyse als zusätzliches Werkzeug für klinisches Denken." },
              { step: "03", title: "Notebook", desc: "PDFs in strukturierte Lernkarten, Zusammenfassungen und Audio verwandeln." },
              { step: "04", title: "Podcast", desc: "Tägliche Wiederholung als kompakte medizinische Audio-Lerneinheit." },
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

      {/* ═══════ SECTION 6.5: ZUGANG ═══════ */}
      <section className="section-spacing relative section-enter" id="pricing">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-5xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="06" text="Zugang" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 heading-premium">
            Medizinisches Lernen<br />
            <span style={{ color: '#c9a84c' }}>kostenlos für alle</span>
          </h2>
          <p className="text-white/40 mb-16 max-w-xl">Registrieren Sie sich kostenlos und starten Sie sofort. Neue Nutzer erhalten 30 Tage Testphase für die erweiterten Lernfunktionen; danach werden Zugänge gezielt freigeschaltet.</p>

          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {/* Free for all */}
            <div className="card-premium p-8">
              <div className="text-xs font-mono tracking-widest text-white/30 uppercase mb-4">Für alle</div>
              <div className="text-4xl font-bold text-white mb-1">Kostenlos</div>
              <p className="text-sm text-white/30 mb-8">Nach Registrierung sofort verfügbar</p>
              <ul className="space-y-3 mb-8">
                {[
                  "Study Mode frei nutzbar",
                  "30 Tage Testphase für Lernfunktionen",
                  "Fortschrittsstatistiken",
                  "Tägliche Lernziele",
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
                    Bereits registriert ✓
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
                  "Notebook — PDF zu Lernkarten & Audio",
                  "Täglicher Medizin-Podcast",
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
                {requestingAccess ? "Wird gesendet…" : "Zugang anfragen"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ SECTION 7: FAZIT / CTA ═══════ */}
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 bg-premium-dark" />
        <div className="absolute inset-0 section-glow-center" />
        <div className="absolute top-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.1), transparent)' }} />
        <div className="max-w-4xl mx-auto px-6 sm:px-10 lg:px-16 text-center relative z-10">
          <div className="flex items-center justify-center gap-2 mb-8">
            <span style={{ color: '#c9a84c' }}>◆</span>
            <span className="text-xs tracking-[0.2em] uppercase text-white/30">Fazit — Ihre professionelle Zukunft</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
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
