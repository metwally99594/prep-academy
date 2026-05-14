import { useState, useEffect, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity,
  ArrowRight, BookOpen, Clock, CheckCircle,
  Target, Shield, FileText, Bot, Layers, Pill,
  Dna, Plus, Microscope, Stethoscope,
} from "lucide-react";
import { toast } from "sonner";

const iconMap = {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity, Pill,
};

/* Splash */
const SplashOverlay = ({ onDone }) => {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 80);
    const t2 = setTimeout(() => setPhase(2), 1000);
    const t3 = setTimeout(() => onDone(), 1600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center transition-all duration-500 ${phase >= 2 ? "opacity-0 pointer-events-none" : "opacity-100"}`} style={{ background: "linear-gradient(135deg, #06081a 0%, #0a1128 40%, #06081a 100%)" }} data-testid="splash-overlay">
      <div className="text-center relative">
        <div className={`transition-all duration-600 ${phase >= 1 ? "opacity-100 scale-100" : "opacity-0 scale-75"}`}>
          <img src="/logo-elite.png" alt="Prep Academy" className="w-44 h-44 mx-auto object-contain" style={{ filter: "drop-shadow(0 0 40px rgba(59,130,246,0.25))" }} />
        </div>
      </div>
    </div>
  );
};

/* Section label */
const SectionLabel = ({ number, text }) => (
  <div className="flex items-center gap-3 mb-6">
    <span className="text-xs font-mono tracking-widest text-primary">{number}</span>
    <div className="w-12 h-px bg-primary/30" />
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
    <div style={{ background: '#06081a', color: '#d4d4d8' }}>
      {!user && showSplash && <SplashOverlay onDone={handleSplashDone} />}

      {/* SECTION */}
      <section className="relative min-h-[100vh] flex items-center overflow-hidden hero-medical" style={{ background: '#0a1628' }} data-testid="hero-section">

        {/* SECTION */}
        <div className="absolute inset-0 pointer-events-none z-[0] medical-pattern" aria-hidden="true" />
        <div className="absolute inset-0 pointer-events-none z-[1] hero-overlays" aria-hidden="true" />
        <div className="floating-icons-container" aria-hidden="true">
          <div className="floating-icon dna"><Dna /></div>
          <div className="floating-icon heart"><Heart /></div>
          <div className="floating-icon cross"><Plus /></div>
          <div className="floating-icon microscope"><Microscope /></div>
          <div className="floating-icon pulse"><Activity /></div>
          <div className="floating-icon brain"><Brain /></div>
          <div className="floating-icon pill"><Pill /></div>
          <div className="floating-icon stethoscope"><Stethoscope /></div>
        </div>
        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[44%] h-[72%] max-h-[650px] pointer-events-none z-[2] hidden md:block" aria-hidden="true">
          <svg viewBox="0 0 500 600" className="w-full h-full" fill="none">
            <circle cx="280" cy="300" r="220" stroke="rgba(59,130,246,0.07)" strokeWidth="0.5" />
            <circle cx="280" cy="300" r="185" stroke="rgba(59,130,246,0.05)" strokeWidth="0.4" strokeDasharray="3 5" />
            <circle cx="280" cy="300" r="150" stroke="rgba(59,130,246,0.08)" strokeWidth="0.5" />
            <circle cx="280" cy="300" r="115" stroke="rgba(59,130,246,0.05)" strokeWidth="0.35" strokeDasharray="2 4" />
            <circle cx="280" cy="300" r="80" stroke="rgba(59,130,246,0.07)" strokeWidth="0.4" />
            <circle cx="280" cy="300" r="45" stroke="rgba(59,130,246,0.06)" strokeWidth="0.3" strokeDasharray="2 3" />
            <line x1="60" y1="300" x2="500" y2="300" stroke="rgba(59,130,246,0.04)" strokeWidth="0.3" />
            <line x1="280" y1="80" x2="280" y2="520" stroke="rgba(59,130,246,0.04)" strokeWidth="0.3" />
            <line x1="130" y1="150" x2="430" y2="450" stroke="rgba(59,130,246,0.03)" strokeWidth="0.25" strokeDasharray="3 5" />
            <line x1="430" y1="150" x2="130" y2="450" stroke="rgba(59,130,246,0.03)" strokeWidth="0.25" strokeDasharray="3 5" />
            <g stroke="rgba(59,130,246,0.25)" strokeWidth="0.7" fill="none">
              <path d="M270 200 C245 185 200 195 195 240 C190 270 195 295 205 315 C210 330 225 345 240 355 C255 365 265 370 275 375 C295 380 315 375 330 360 C350 340 365 310 360 270 C355 230 330 205 305 200 C290 197 280 205 270 200Z" />
              <path d="M275 200 C270 235 280 270 275 305 C270 335 280 355 275 375" strokeWidth="0.5" />
              <path d="M245 220 C235 230 230 245 235 255" strokeWidth="0.4" />
              <path d="M240 270 C228 285 232 300 242 310" strokeWidth="0.4" />
              <path d="M248 325 C238 335 242 348 252 355" strokeWidth="0.4" />
              <path d="M335 220 C345 230 350 245 345 255" strokeWidth="0.4" />
              <path d="M340 270 C352 285 348 300 338 310" strokeWidth="0.4" />
              <path d="M332 325 C342 335 338 348 328 355" strokeWidth="0.4" />
              <path d="M268 375 C265 395 265 415 270 435" strokeWidth="0.4" />
              <path d="M282 375 C285 395 285 415 280 435" strokeWidth="0.4" />
            </g>
            <g fill="rgba(96,165,250,0.5)">
              <circle cx="280" cy="180" r="2" /><circle cx="200" cy="215" r="1.8" /><circle cx="360" cy="215" r="1.8" />
              <circle cx="195" cy="285" r="1.5" /><circle cx="365" cy="285" r="1.5" /><circle cx="210" cy="345" r="1.8" />
              <circle cx="350" cy="345" r="1.8" /><circle cx="240" cy="365" r="2" /><circle cx="320" cy="360" r="2" />
              <circle cx="275" cy="380" r="1.8" /><circle cx="270" cy="435" r="1.5" /><circle cx="280" cy="435" r="1.5" />
            </g>
            <circle cx="280" cy="300" r="2.5" fill="rgba(96,165,250,0.6)" />
            <circle cx="280" cy="300" r="5" fill="rgba(96,165,250,0.15)" />
            <g stroke="rgba(59,130,246,0.10)" strokeWidth="0.6">
              <line x1="280" y1="80" x2="280" y2="90" /><line x1="500" y1="300" x2="490" y2="300" />
              <line x1="280" y1="520" x2="280" y2="510" /><line x1="60" y1="300" x2="70" y2="300" />
              <line x1="436" y1="144" x2="429" y2="151" /><line x1="124" y1="456" x2="131" y2="449" />
              <line x1="436" y1="456" x2="429" y2="449" /><line x1="124" y1="144" x2="131" y2="151" />
            </g>
            <g fill="rgba(59,130,246,0.15)">
              <circle cx="280" cy="78" r="1.2" /><circle cx="502" cy="300" r="1.2" />
              <circle cx="280" cy="522" r="1.2" /><circle cx="58" cy="300" r="1.2" />
              <circle cx="131" cy="151" r="1" /><circle cx="429" cy="151" r="1" />
              <circle cx="131" cy="449" r="1" /><circle cx="429" cy="449" r="1" />
            </g>
          </svg>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 py-20 w-full relative z-10">
          <div className="max-w-xl lg:max-w-lg">
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border mb-10 sm:mb-12"
              style={{ borderColor: 'rgba(255,255,255,0.25)', background: 'rgba(255,255,255,0.08)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-white/80" style={{ boxShadow: '0 0 6px rgba(255,255,255,0.5)' }} />
              <span className="text-xs font-medium tracking-[0.22em] uppercase text-white/80">Medizinische Exzellenz</span>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold leading-[1.05] mb-6 sm:mb-7 hero-title-mobile"
              data-testid="hero-title"
              style={{ fontFamily: "'Playfair Display', serif", letterSpacing: '-0.02em' }}>
              <span className="text-white">Prep</span>
              <span className="ml-3 sm:ml-4 text-[#c9a84c]">Academy</span>
            </h1>

            <p className="text-base sm:text-lg tracking-[0.18em] uppercase font-light mb-6 text-white/65">KLAR. PRÄZISE. KI-GESTÜTZT.</p>

            <p className="text-white/55 text-base sm:text-lg leading-relaxed mb-10 max-w-lg">
              Medizinische Prüfungsvorbereitung für Österreich und Deutschland: echte Fragen, KI-Erklärungen, Analyzer, PDF-Notebook und 30 Tage Testphase.
            </p>

            <div className="flex flex-wrap gap-3 mb-10">
              {["30 Tage kostenlos testen", "Medical Analyzer", "PDF Notebook"].map((item) => (
                <span key={item} className="px-4 py-2 rounded-full border text-xs tracking-[0.12em] uppercase font-medium"
                  style={{ borderColor: 'rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.6)' }}>
                  {item}
                </span>
              ))}
            </div>

            {!user ? (
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/guest-quiz">
                  <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold rounded-xl bg-white hover:bg-white/95 transition-all hover:-translate-y-0.5 border-0" style={{ color: '#1e40af' }} data-testid="hero-guest-btn">
                    Kostenlos testen
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="lg" variant="outline" className="gap-2 px-8 h-14 text-base font-semibold rounded-xl border-white/40 text-white hover:bg-white/10 hover:text-white" data-testid="hero-register-btn">
                    Konto erstellen
                  </Button>
                </Link>
              </div>
            ) : (
              <Link to="/dashboard">
                <Button size="lg" className="gap-2 px-10 h-14 text-base font-semibold rounded-xl bg-white hover:bg-white/95 transition-all hover:-translate-y-0.5 border-0" style={{ color: '#1e40af' }}>
                  Zum Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-px pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), rgba(255,255,255,0.1), transparent)' }} />
      </section>

      {/* SECTION */}
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
                    isActive ? 'border-primary/40 -translate-y-1' : 'border-white/[0.06] hover:border-white/[0.12] hover:-translate-y-0.5'
                  }`}
                  style={{
                    background: isActive ? 'hsl(var(--primary) / 0.08)' : 'rgba(255,255,255,0.03)',
                    boxShadow: isActive ? '0 8px 32px hsl(var(--primary) / 0.15)' : 'none',
                  }}
                >
                  {isActive && <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-xl bg-primary" />}
                  <div className="text-xl mb-2">
                    {exam.icon === 'flag_at' && '🇦🇹'}
                    {exam.icon === 'mountain' && '🏔️'}
                    {exam.icon === 'building' && '🏛️'}
                    {exam.icon === 'pill' && '💊'}
                  </div>
                  <h3 className={`font-semibold text-sm sm:text-base mb-1 ${isActive ? 'text-primary' : 'text-white/80'}`}>
                    {exam.name}
                    {isActive && <span className="ml-2 text-primary">?</span>}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-white/30 leading-snug mb-2 line-clamp-2">{exam.subtitle}</p>
                  <p className="text-xs font-mono" style={{ color: isActive ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.25)' }}>
                    {exam.question_count.toLocaleString('de-DE')} Fragen
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="01" text="Lernen" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Wie du lernst:<br />
            <span className="text-gradient-blue">strukturiert, klar, Schritt für Schritt</span>
          </h2>
          <p className="text-white/40 text-base sm:text-lg leading-relaxed max-w-xl mb-16">
            Wähle dein Fachgebiet, beantworte originale Prüfungsfragen und vertiefe mit KI-Erklärungen — in deinem Tempo, mit direktem Feedback.
          </p>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8">
            {[
              { num: "01", icon: BookOpen, title: "Fachgebiet wählen", desc: "MedAT, ÖSDK oder deutsche Prüfungsordnung — wähle deine Prüfung und starte mit passgenauen Fragen." },
              { num: "02", icon: Activity, title: "Fragen beantworten", desc: "Originalgetreue Prüfungsfragen mit sofortiger Auswertung. Jede Antwort zählt für deinen Fortschritt." },
              { num: "03", icon: Bot, title: "KI-Erklärungen", desc: "Verstehe jede Frage mit detaillierten KI-generierten Erklärungen — als Text oder Audio." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <span className="text-primary">◆</span>
                    <span className="text-xs font-mono" style={{ color: 'hsl(var(--primary))' }}>{item.num}</span>
                  </div>
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6" style={{ background: 'hsl(var(--primary) / 0.06)', border: '1px solid hsl(var(--primary) / 0.1)' }}>
                    <Icon className="w-7 h-7" style={{ color: 'hsl(var(--primary))' }} />
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-3">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="02" text="Dashboard" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Dein<br />
            <span className="text-gradient-blue">digitaler Lernkompass</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 mt-12">
            {[
              { icon: Shield, title: "Datenschutz & Sicherheit", desc: "Deine Daten bleiben vertraulich. Keine Werbung, kein Tracking. Fokussiertes Lernen in einer geschützten Umgebung." },
              { icon: Layers, title: "Klare Lernstruktur", desc: "Fachgebiete, Prüfungsorte und Lernwerkzeuge bleiben schnell auffindbar." },
              { icon: Target, title: "Fortschritt im Blick", desc: "Statistiken und Lernziele zeigen, wo du sicher bist und wo Wiederholung lohnt." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={i} className={`card-premium-alt p-6 section-enter-delay-${i + 1}`}>
                  <Icon className="w-6 h-6 mb-4" style={{ color: 'hsl(var(--primary))' }} />
                  <h3 className="text-white font-semibold mb-2">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>

          {/* SECTION */}
          <div className="mt-16 card-premium p-8 gold-border-top">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-xs font-mono tracking-widest" style={{ color: 'hsl(var(--primary))' }}>PREP ACADEMY</span>
              <span className="text-primary">◆</span>
              <span className="text-xs text-white/30">DASHBOARD</span>
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center p-6 rounded-xl" style={{ background: 'hsl(var(--primary) / 0.04)', border: '1px solid hsl(var(--primary) / 0.08)' }}>
                <div className="text-4xl font-bold text-white">{displayNumber(totalAvailableQuestions || totalQ)}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fragen Gesamt</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'hsl(var(--primary) / 0.04)', border: '1px solid hsl(var(--primary) / 0.08)' }}>
                <div className="text-4xl font-bold text-white">{displayNumber(activeSpecialtyCount || (Array.isArray(filteredSpecialties) ? filteredSpecialties.filter(s => s.question_count > 0).length : 0))}</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">Fachgebiete</div>
              </div>
              <div className="text-center p-6 rounded-xl" style={{ background: 'hsl(var(--primary) / 0.04)', border: '1px solid hsl(var(--primary) / 0.08)' }}>
                <div className="text-4xl font-bold" style={{ color: 'hsl(var(--primary))' }}>AI</div>
                <div className="text-xs text-white/30 mt-1 tracking-wider uppercase">KI-Erklärungen</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="03" text="Künstliche Intelligenz" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            KI-Werkzeuge für<br />
            <span className="text-gradient-blue">Fragen, Bilder und PDFs</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 mt-16">
            {[
              { num: "01", icon: Bot, title: "KI-Erklärungen", desc: "Direkte Erklärungen zu Prüfungsfragen, damit du nicht nur klickst, sondern verstehst." },
              { num: "02", icon: Activity, title: "Medical Analyzer", desc: "Analyse medizinischer Bilder mit mehrstufigem KI-Fallback für sichere Einschätzungen." },
              { num: "03", icon: FileText, title: "PDF Notebook", desc: "Aus Skripten und PDFs entstehen Lernkarten, Zusammenfassungen, Audio und MindMaps." },
            ].map((item, i) => {
              const Icon = item.icon;
              return (
                <div key={item.num} className={`card-premium p-8 section-enter-delay-${i + 1}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <span className="text-primary">◆</span>
                    <span className="text-xs font-mono" style={{ color: 'hsl(var(--primary))' }}>{item.num}</span>
                  </div>
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6" style={{ background: 'hsl(var(--primary) / 0.06)', border: '1px solid hsl(var(--primary) / 0.1)' }}>
                    <Icon className="w-7 h-7" style={{ color: 'hsl(var(--primary))' }} />
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-3">{item.title}</h3>
                  <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="04" text="Fachgebiete" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 leading-tight heading-premium">
            Medizinische<br />
            <span className="text-gradient-blue">Fachgebiete</span>
          </h2>

          {fetchError ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-white/40">Verbindungsfehler — Fachgebiete konnten nicht geladen werden</p>
              <button onClick={loadHomepageData} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium text-white/60 hover:text-white hover:border-white/20 transition-all" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                Erneut versuchen
              </button>
            </div>
          ) : specialties.length === 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => <div key={i} className="min-h-[116px] rounded-xl animate-pulse" style={{ background: 'hsl(var(--primary) / 0.03)' }} />)}
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
                        <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'hsl(var(--primary) / 0.06)' }}>
                          <IconComponent className="w-6 h-6" style={{ color: 'hsl(var(--primary))' }} />
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

          {/* SECTION */}
          {user && (
            <Link to="/exam-simulation" className="block mt-12">
              <div className="card-premium card-raised p-6 sm:p-8 group cursor-pointer flex items-center justify-between" data-testid="exam-simulation-cta">
                <div className="flex items-center gap-5">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: 'hsl(var(--primary) / 0.08)' }}>
                    <Clock className="w-7 h-7" style={{ color: 'hsl(var(--primary))' }} />
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

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 section-premium" />
        <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="05" text="Module" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-16 heading-premium">
            Mehr als ein Quiz:<br />
            <span className="text-gradient-blue">ein medizinischer Lernraum</span>
          </h2>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: "01", title: "Quiz", desc: "Fachbezogene Prüfungsvorbereitung mit echten medizinischen Fragen." },
              { step: "02", title: "Analyzer", desc: "Medizinische Bildanalyse als zusätzliches Werkzeug für klinisches Denken." },
              { step: "03", title: "Notebook", desc: "PDFs in strukturierte Lernkarten, Zusammenfassungen und Audio verwandeln." },
              { step: "04", title: "Podcast", desc: "Tägliche Wiederholung als kompakte medizinische Audio-Lerneinheit." },
            ].map((item, i) => (
              <div key={item.step} className={`card-premium p-6 section-enter-delay-${i + 1}`}>
                <div className="text-5xl font-bold mb-4" style={{ color: 'hsl(var(--primary) / 0.08)' }}>{item.step}</div>
                <h3 className="font-semibold text-white mb-2 uppercase text-sm tracking-wider">{item.title}</h3>
                <p className="text-white/35 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter" id="pricing">
        <div className="absolute inset-0 section-premium-alt" />
        <div className="max-w-5xl mx-auto px-6 sm:px-10 lg:px-16 relative z-10">
          <SectionLabel number="06" text="Zugang" />
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Medizinisches Lernen<br />
            <span className="text-gradient-blue">kostenlos für alle</span>
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
                    <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'hsl(var(--primary))' }} />
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
                <span className="text-xs font-mono tracking-widest uppercase" style={{ color: 'hsl(var(--primary))' }}>Erweiterte Funktionen</span>
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
                    <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'hsl(var(--primary))' }} />
                    {f}
                  </li>
                ))}
              </ul>
              <button onClick={requestAdvancedAccess} disabled={requestingAccess}
                className="w-full py-3 rounded-xl text-sm font-semibold transition-all hover:-translate-y-0.5 disabled:opacity-50 btn-medical">
                {requestingAccess ? "Wird gesendet..." : "Zugang anfragen"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION */}
      <div className="section-divider" />
      <section className="section-spacing relative section-enter">
        <div className="absolute inset-0 bg-premium-dark" />
        <div className="absolute inset-0 section-glow-center" />
        <div className="absolute top-0 left-0 w-full h-px" style={{ background: 'linear-gradient(90deg, transparent, hsl(var(--primary) / 0.1), transparent)' }} />
        <div className="max-w-4xl mx-auto px-6 sm:px-10 lg:px-16 text-center relative z-10">
          <div className="flex items-center justify-center gap-2 mb-8">
            <span className="text-primary">◆</span>
            <span className="text-xs tracking-[0.2em] uppercase text-white/30">Fazit — Ihre professionelle Zukunft</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 heading-premium">
            Ihre berufliche<br />
            <span className="text-gradient-blue">Zukunft beginnt hier</span>
          </h2>

          <p className="text-white/40 text-lg leading-relaxed mb-12 max-w-2xl mx-auto">
            Prep Academy ist Ihr strategischer Partner für den Erfolg in der Österreichischen Medizinwelt. Nutzen Sie die fortschrittlichste Technologie für Ihre medizinische Karriere.
          </p>

          <div className="flex items-center justify-center gap-8 mb-12 text-xs tracking-[0.2em] uppercase text-white/20">
            <span>Partnerschaft</span>
            <span>Wettbewerbsvorteil</span>
            <span>Excellence</span>
          </div>

          {!user ? (
            <Link to="/register">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-medical" data-testid="cta-register-btn">
                Jetzt Starten
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          ) : (
            <Link to="/dashboard">
              <Button size="lg" className="gap-3 px-12 h-14 text-base font-semibold border-0 rounded-none tracking-wider uppercase btn-medical">
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
