import { Link } from "react-router-dom";
import { BadgeCheck, Sparkles, Brain, Heart, Shield, ChevronDown } from "lucide-react";

export function HeroMedicalRefined() {
  return (
    <section className="hero-medical-refined min-h-[90vh] flex items-center relative">
      <div className="glow-orb gold w-96 h-96 -top-20 -left-20" />
      <div className="glow-orb blue w-72 h-72 -bottom-10 -right-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <span className="section-label-refined">Exam Preparation</span>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight">
            Your{" "}
            <span className="text-gradient-gold-refined">Medical Career</span>
            {" "}Starts Here
          </h1>
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
            AI-powered mock exams, real-time analytics, and a community of peers —
            everything you need to ace the USMLE, NBME, and COMLEX.
          </p>
          <div className="flex flex-wrap justify-center gap-4 pt-4">
            <Link to="/register" className="btn-gold text-base px-8 py-3">
              <Sparkles className="w-5 h-5" />
              Start Free Trial
            </Link>
            <Link to="/about" className="btn-gold-outline text-base px-8 py-3">
              Learn More
            </Link>
          </div>

          <div className="flex flex-wrap justify-center gap-6 pt-6 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <BadgeCheck className="w-4 h-4 text-gold" /> 5,000+ Questions
            </span>
            <span className="flex items-center gap-1.5">
              <BadgeCheck className="w-4 h-4 text-gold" /> AI Explanations
            </span>
            <span className="flex items-center gap-1.5">
              <BadgeCheck className="w-4 h-4 text-gold" /> Peer Community
            </span>
          </div>
        </div>
      </div>

      <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
        <div className="scroll-indicator">
          <div className="mouse" />
          <span>Scroll</span>
        </div>
      </div>
    </section>
  );
}

export function SpecialtyCardRefined({ icon: Icon, title, description, badge }) {
  return (
    <div className="specialty-card-refined p-6 space-y-4 group">
      <div className="flex items-start justify-between">
        <div className="w-11 h-11 rounded-xl bg-accent/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform">
          {Icon && <Icon className="w-5 h-5" />}
        </div>
        {badge && <span className="badge-gold">{badge}</span>}
      </div>
      <h3 className="font-semibold text-lg">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

export function AIToolCard({ icon: Icon, title, description }) {
  return (
    <div className="ai-tool-card p-5 space-y-3 group">
      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
        {Icon && <Icon className="w-5 h-5" />}
      </div>
      <h4 className="font-semibold text-sm">{title}</h4>
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

export function StatNumberRefined({ value, label }) {
  return (
    <div className="text-center space-y-1">
      <div className="stat-number-refined">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  );
}

export function NavLinkRefined({ to, children, active }) {
  return (
    <Link
      to={to}
      className={`nav-link-refined${active ? " active" : ""}`}
    >
      {children}
    </Link>
  );
}

export function LogoRefined() {
  return (
    <Link to="/" className="logo-refined">
      <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-accent-foreground font-bold text-sm">
        P
      </div>
      Prep<span>Academy</span>
    </Link>
  );
}

export function QuizChoiceRefined({ label, selected, correct, incorrect, disabled, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`choice-refined${
        selected ? " selected" : ""
      }${correct ? " correct" : ""}${incorrect ? " incorrect" : ""}`}
    >
      <span className="flex-1">{label}</span>
      {correct && <BadgeCheck className="w-5 h-5 text-success shrink-0" />}
      {incorrect && <Shield className="w-5 h-5 text-destructive shrink-0" />}
    </button>
  );
}

export function TimerPillRefined({ seconds }) {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return (
    <div className="timer-pill">
      <Brain className="w-3.5 h-3.5" />
      <span>{String(minutes).padStart(2, "0")}:{String(secs).padStart(2, "0")}</span>
    </div>
  );
}

export function ProgressRefined({ value }) {
  return (
    <div className="progress-refined">
      <div style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
}

export function CardNavyGoldRefined({ children, className = "" }) {
  return (
    <div className={`card-navy-gold p-6 ${className}`}>
      {children}
    </div>
  );
}

export function BadgeExample() {
  return (
    <div className="flex flex-wrap gap-2">
      <span className="badge-gold">Premium</span>
      <span className="badge-gold-soft">Featured</span>
      <span className="badge-success">Verified</span>
      <span className="badge-danger">Urgent</span>
      <span className="badge-info">Info</span>
      <span className="badge-dot">Online</span>
    </div>
  );
}
