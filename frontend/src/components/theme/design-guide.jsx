/* ════════════════════════════════════════════════════════════════════
   PREP ACADEMY — REFINED COMPONENTS EXAMPLES
   ════════════════════════════════════════════════════════════════════
   
   ده ملف React JSX يوضح ازاي تستخدم الكلاسات الجديدة في:
   - Hero Section
   - Specialty Cards
   - AI Tool Cards
   - Quiz Choices
   - Stats Display
   - Buttons
   - Badges
   
   مش لازم تستبدل ملفاتك الكاملة — استخدم ده كمرجع لتعديل
   src/pages/HomePage.jsx و src/pages/QuizPage.jsx
   
   ════════════════════════════════════════════════════════════════════ */

import { ArrowRight, Activity, Brain, Heart, Stethoscope, FileText, Headphones, Sparkles, Award, Users } from "lucide-react";


/* ═══════════════════════════════════════════════════════════════
   1. HERO SECTION — القسم الرئيسي
   ═══════════════════════════════════════════════════════════════ */

export function HeroSection() {
    return (
        <section className="hero-medical-refined relative min-h-screen flex items-center overflow-hidden" data-testid="hero-section">

            {/* الخلفية — gradient + radial glow + النجوم (كله من CSS) */}

            <div className="container mx-auto px-6 lg:px-12 py-20 relative z-10">
                <div className="grid lg:grid-cols-2 gap-12 items-center">

                    {/* العمود الشمال: المحتوى */}
                    <div className="space-y-6">

                        {/* Section Label — التسمية الصغيرة */}
                        <div className="section-label-refined">
                            <span className="label-number">01</span>
                            <span className="label-line" />
                            <span className="label-text">Medizinische Exzellenz</span>
                        </div>

                        {/* Pill Badge */}
                        <div className="inline-flex items-center gap-2 px-4 py-2 border border-[hsl(var(--gold)/0.5)] rounded-full bg-[hsl(var(--gold)/0.05)]">
                            <span className="badge-dot text-[hsl(var(--gold))]" />
                            <span className="text-xs font-bold text-[hsl(var(--gold))] tracking-widest">
                                KI-GESTÜTZTE PRÜFUNGSVORBEREITUNG
                            </span>
                        </div>

                        {/* العنوان الرئيسي */}
                        <h1 className="font-serif text-5xl lg:text-7xl font-bold leading-tight tracking-tight">
                            <span className="text-foreground">Prep </span>
                            <span className="text-gradient-gold-refined">Academy</span>
                        </h1>

                        {/* العنوان الفرعي */}
                        <p className="text-sm tracking-[0.3em] uppercase text-muted-foreground font-medium">
                            Klar. Präzise. KI-gestützt.
                        </p>

                        {/* الوصف */}
                        <p className="text-base lg:text-lg text-muted-foreground leading-relaxed max-w-xl">
                            Medizinische Prüfungsvorbereitung für Österreich und Deutschland:
                            echte Fragen, KI-Erklärungen, DICOM Analyzer und 30 Tage kostenlose Testphase.
                        </p>

                        {/* CTA Buttons */}
                        <div className="flex flex-wrap gap-3 pt-4">

                            {/* الزر الذهبي الأساسي */}
                            <button className="btn-gold px-7 py-3.5 inline-flex items-center gap-2 text-sm">
                                <span>Zum Dashboard</span>
                                <ArrowRight className="w-4 h-4 rtl:rotate-180" />
                            </button>

                            {/* الزر الـ outline */}
                            <button className="btn-gold-outline px-7 py-3.5 inline-flex items-center gap-2 text-sm">
                                <Sparkles className="w-4 h-4" />
                                <span>30 Tage testen</span>
                            </button>
                        </div>

                        {/* Stats Strip */}
                        <div className="flex items-center pt-8 mt-4 border-t border-border">
                            <div className="flex items-baseline flex-col">
                                <span className="stat-number-refined">2.8K+</span>
                                <span className="stat-label-refined">Fragen</span>
                            </div>
                            <div className="stat-divider" />
                            <div className="flex items-baseline flex-col">
                                <span className="stat-number-refined">42</span>
                                <span className="stat-label-refined">Fächer</span>
                            </div>
                            <div className="stat-divider" />
                            <div className="flex items-baseline flex-col">
                                <span className="stat-number-refined">98%</span>
                                <span className="stat-label-refined">Erfolg</span>
                            </div>
                            <div className="stat-divider" />
                            <div className="flex items-baseline flex-col">
                                <span className="stat-number-refined">5</span>
                                <span className="stat-label-refined">Sprachen</span>
                            </div>
                        </div>
                    </div>

                    {/* العمود اليمين: الـ visual — الدماغ + الفلوتنج كاردز */}
                    <div className="relative hidden lg:block">

                        {/* SVG الدماغ مع glow */}
                        <div className="relative glow-orb-blue w-[500px] h-[500px] mx-auto">
                            {/* هنا SVG الدماغ الموجود عندك بالفعل */}
                            <svg viewBox="0 0 500 500" className="w-full h-full" fill="none">
                                {/* ... محتوى SVG الموجود ... */}
                            </svg>
                        </div>

                        {/* Float Card 1 — AI Chat */}
                        <div className="float-card float-delay-1 absolute top-8 -right-4">
                            <div className="float-icon-wrap info">
                                <Brain className="w-4 h-4" />
                            </div>
                            <div>
                                <div className="float-title">AI Chat</div>
                                <div className="float-subtitle">DeepSeek V3.1</div>
                            </div>
                        </div>

                        {/* Float Card 2 — DICOM */}
                        <div className="float-card float-delay-2 absolute bottom-12 left-0">
                            <div className="float-icon-wrap success">
                                <Activity className="w-4 h-4" />
                            </div>
                            <div>
                                <div className="float-title">DICOM Analyzer</div>
                                <div className="float-subtitle">CT / MR / X-Ray</div>
                            </div>
                        </div>

                        {/* Float Card 3 — RAG */}
                        <div className="float-card float-delay-3 absolute top-1/2 -left-8">
                            <div className="float-icon-wrap">
                                <Sparkles className="w-4 h-4" />
                            </div>
                            <div>
                                <div className="float-title">RAG + KI</div>
                                <div className="float-subtitle">Quellenangaben</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Scroll Indicator */}
            <div className="scroll-indicator">
                <span>Mehr entdecken</span>
                <div className="scroll-line" />
            </div>
        </section>
    );
}


/* ═══════════════════════════════════════════════════════════════
   2. SPECIALTIES GRID — كروت التخصصات
   ═══════════════════════════════════════════════════════════════ */

export function SpecialtiesSection() {
    const specialties = [
        { name: "Kardiologie", desc: "Herz-Kreislauf-System", count: 128, icon: Heart, featured: false },
        { name: "Neurologie", desc: "Gehirn + Nerven", count: 256, icon: Brain, featured: true },
        { name: "Innere Medizin", desc: "Allgemeine Medizin", count: 312, icon: Stethoscope, featured: false },
        { name: "Chirurgie", desc: "Operative Medizin", count: 203, icon: Activity, featured: false },
    ];

    return (
        <section className="py-24 bg-background">
            <div className="container mx-auto px-6 lg:px-12">

                {/* Section Header */}
                <div className="mb-16">
                    <div className="section-label-refined mb-4">
                        <span className="label-number">02</span>
                        <span className="label-line" />
                        <span className="label-text">Fachgebiete</span>
                    </div>
                    <h2 className="font-serif text-4xl lg:text-5xl font-bold">
                        <span>42 medizinische </span>
                        <span className="text-gradient-gold-refined">Fachgebiete</span>
                    </h2>
                    <p className="mt-4 text-muted-foreground max-w-2xl">
                        Von Anatomie bis Onkologie — alle Prüfungsthemen in einer Plattform.
                    </p>
                </div>

                {/* Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {specialties.map((s) => {
                        const Icon = s.icon;
                        return (
                            <article key={s.name} className={`specialty-card-refined ${s.featured ? "border-[hsl(var(--gold)/0.5)]" : ""}`}>
                                <div className="specialty-icon">
                                    <Icon className="w-5 h-5" />
                                </div>
                                <h3 className="specialty-name">{s.name}</h3>
                                <p className="specialty-desc">{s.desc}</p>
                                <div className="specialty-footer">
                                    <span className="specialty-count">{s.count} MCQs</span>
                                    <ArrowRight className="specialty-arrow w-4 h-4 rtl:rotate-180" />
                                </div>
                            </article>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}


/* ═══════════════════════════════════════════════════════════════
   3. AI TOOLS SECTION — قسم الأدوات الذكية
   ═══════════════════════════════════════════════════════════════ */

export function AIToolsSection() {
    return (
        <section className="py-24 bg-background">
            <div className="container mx-auto px-6 lg:px-12">

                <div className="mb-12">
                    <div className="section-label-refined mb-4">
                        <span className="label-number">03</span>
                        <span className="label-line" />
                        <span className="label-text">KI-Tools</span>
                    </div>
                    <h2 className="font-serif text-3xl lg:text-4xl font-bold">
                        <span>Lerntools mit </span>
                        <span className="text-gradient-gold-refined">künstlicher Intelligenz</span>
                    </h2>
                </div>

                <div className="grid md:grid-cols-3 gap-6">

                    {/* Tool 1: DICOM */}
                    <article className="ai-tool-card">
                        <div className="tool-icon-wrap icon-info">
                            <FileText className="w-6 h-6" />
                        </div>
                        <h3 className="tool-title">DICOM Analyzer</h3>
                        <p className="tool-description">
                            CT, MR, X-Ray — automatische Befunderstellung in 43s mit
                            RAG-basierter Quellenüberprüfung.
                        </p>
                        <div className="tool-footer">
                            <span className="badge-info">Open Source</span>
                            <ArrowRight className="w-4 h-4 text-[hsl(var(--info))] rtl:rotate-180" />
                        </div>
                    </article>

                    {/* Tool 2: AI Chat — Featured */}
                    <article className="ai-tool-card featured">
                        <div className="tool-badge">
                            <span className="badge-gold">NEU</span>
                        </div>
                        <div className="tool-icon-wrap icon-gold">
                            <Brain className="w-6 h-6" />
                        </div>
                        <h3 className="tool-title">AI Chat (RAG)</h3>
                        <p className="tool-description">
                            DeepSeek V3.1 — medizinische Fragen mit Quellenangaben aus
                            S3-Leitlinien und PubMed.
                        </p>
                        <div className="tool-footer">
                            <span className="badge-gold">Premium</span>
                            <ArrowRight className="w-4 h-4 text-[hsl(var(--gold))] rtl:rotate-180" />
                        </div>
                    </article>

                    {/* Tool 3: Podcast */}
                    <article className="ai-tool-card">
                        <div className="tool-icon-wrap icon-success">
                            <Headphones className="w-6 h-6" />
                        </div>
                        <h3 className="tool-title">Daily Podcast</h3>
                        <p className="tool-description">
                            5-Minuten Folgen täglich. Edge TTS in 5 Sprachen mit
                            2-Speaker Format.
                        </p>
                        <div className="tool-footer">
                            <span className="badge-success">Kostenlos</span>
                            <ArrowRight className="w-4 h-4 text-[hsl(var(--success))] rtl:rotate-180" />
                        </div>
                    </article>
                </div>
            </div>
        </section>
    );
}


/* ═══════════════════════════════════════════════════════════════
   4. QUIZ PAGE — صفحة الأسئلة المحسّنة
   ═══════════════════════════════════════════════════════════════ */

export function QuizQuestionRefined({ question, selected, setSelected, correctAnswer, showResult }) {

    const getChoiceClass = (choiceId) => {
        if (showResult) {
            if (choiceId === correctAnswer) return "choice-refined correct";
            if (choiceId === selected && choiceId !== correctAnswer) return "choice-refined incorrect";
            return "choice-refined";
        }
        return `choice-refined ${selected === choiceId ? "selected" : ""}`;
    };

    return (
        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">

            {/* Header — العنوان + المؤقت */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="text-xs font-mono text-[hsl(var(--gold))] tracking-widest mb-1">
                        FRAGE 12 / 50
                    </div>
                    <h1 className="font-serif text-xl font-bold">
                        Kardiologie — MCQ Training
                    </h1>
                </div>

                <div className="timer-pill">
                    <div>
                        <div className="timer-label">Zeit verbleibend</div>
                        <div className="timer-value">12:34</div>
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="progress-refined">
                <div className="progress-fill" style={{ width: "24%" }} />
            </div>

            {/* Question Card */}
            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                <div className="flex gap-2 flex-wrap">
                    <span className="badge-gold-soft">Schwer</span>
                    <span className="badge-info">Kardiologie</span>
                    <span className="px-2.5 py-1 text-xs rounded-full border border-border text-muted-foreground">
                        EKG-Befundung
                    </span>
                </div>

                <h2 className="font-serif text-lg leading-relaxed text-foreground">
                    {question.text || "Ein 65-jähriger Patient präsentiert sich mit akuten retrosternalen Schmerzen seit 30 Minuten. Das EKG zeigt ST-Hebungen in V1\u2013V4. Welche Therapie ist sofort indiziert?"}
                </h2>

                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Sparkles className="w-3 h-3 text-[hsl(var(--info))]" />
                    <span>KI-Erklärung verfügbar nach Antwort</span>
                </div>
            </div>

            {/* Choices */}
            <div className="space-y-3">
                {["A", "B", "C", "D"].map((letter, idx) => (
                    <button
                        key={letter}
                        className={getChoiceClass(letter)}
                        onClick={() => setSelected(letter)}
                        disabled={showResult}
                    >
                        <span className="choice-letter">{letter}</span>
                        <span className="text-sm flex-1 text-start">
                            {idx === 0 && "Sofortige Lyse-Therapie mit rt-PA, falls keine Kontraindikationen"}
                            {idx === 1 && "Primäre PCI innerhalb 90 Minuten + Antikoagulation"}
                            {idx === 2 && "Konservative Therapie mit ASS, Heparin und Beta-Blocker"}
                            {idx === 3 && "Sofortige Koronarangiographie ohne weitere Vorbereitung"}
                        </span>
                    </button>
                ))}
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
                <button className="btn-gold px-8 py-3 inline-flex items-center gap-2" disabled={!selected}>
                    <span>Antwort prüfen</span>
                    <ArrowRight className="w-4 h-4 rtl:rotate-180" />
                </button>
            </div>
        </div>
    );
}


/* ═══════════════════════════════════════════════════════════════
   5. DICOM URGENCY BANNER — تنبيه عاجل في تقارير DICOM
   ═══════════════════════════════════════════════════════════════ */

export function UrgencyBanner({ level, reason }) {
    const config = {
        high:   { class: "urgency-high",   icon: "\u{1F525}", label: "Hohe Dringlichkeit" },
        medium: { class: "urgency-medium", icon: "\u26A0\uFE0F", label: "Mittlere Dringlichkeit" },
        low:    { class: "urgency-low",    icon: "\u2713",  label: "Niedrige Dringlichkeit" },
    }[level];

    return (
        <div className={`urgency-banner ${config.class}`}>
            <div className="urgency-icon">{config.icon}</div>
            <div className="flex-1">
                <div className="font-bold text-sm">{config.label}</div>
                <div className="text-xs opacity-80 mt-0.5">{reason}</div>
            </div>
        </div>
    );
}


/* ═══════════════════════════════════════════════════════════════
   6. NAV BAR — شريط التنقل المحسّن
   ═══════════════════════════════════════════════════════════════ */

export function NavBarRefined({ activeRoute }) {
    return (
        <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
            <div className="container mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">

                {/* Logo */}
                <a href="/" className="logo-refined">
                    <div className="logo-mark">P</div>
                    <div className="logo-text-wrap">
                        <span className="logo-name">Prep</span>
                        <span className="logo-subtitle">Academy</span>
                    </div>
                </a>

                {/* Links */}
                <div className="hidden md:flex items-center gap-8">
                    <a className={`nav-link-refined ${activeRoute === "/" ? "active" : ""}`} href="/">
                        Dashboard
                    </a>
                    <a className={`nav-link-refined ${activeRoute === "/quiz" ? "active" : ""}`} href="/quiz">
                        Quiz
                    </a>
                    <a className={`nav-link-refined ${activeRoute === "/analyzer" ? "active" : ""}`} href="/analyzer">
                        Analyzer
                    </a>
                    <a className={`nav-link-refined ${activeRoute === "/dicom" ? "active" : ""}`} href="/dicom">
                        DICOM
                    </a>
                    <a className={`nav-link-refined ${activeRoute === "/podcast" ? "active" : ""}`} href="/podcast">
                        Podcast
                    </a>
                    <a className={`nav-link-refined ${activeRoute === "/community" ? "active" : ""}`} href="/community">
                        Community
                    </a>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                    <button className="px-4 py-2 text-sm font-medium text-foreground hover:text-[hsl(var(--gold))] transition-colors">
                        Login
                    </button>
                    <button className="btn-gold px-5 py-2 text-sm">
                        Sign up
                    </button>
                </div>
            </div>
        </nav>
    );
}