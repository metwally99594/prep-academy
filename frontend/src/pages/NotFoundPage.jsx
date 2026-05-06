import { Link } from "react-router-dom";
import { ArrowLeft, Search, BookOpen, Brain, BarChart3 } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="text-center max-w-lg">
        {/* Big 404 */}
        <div className="relative mb-8">
          <div className="text-[120px] sm:text-[160px] font-black leading-none select-none"
            style={{ color: 'rgba(201,168,76,0.08)', fontFamily: "'Playfair Display', serif" }}>
            404
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.2)' }}>
              <Search size={32} style={{ color: '#c9a84c' }} />
            </div>
          </div>
        </div>

        <h1 className="text-2xl font-bold mb-3" style={{ fontFamily: "'Playfair Display', serif" }}>
          Seite nicht gefunden
        </h1>
        <p className="text-muted-foreground text-sm mb-8 leading-relaxed">
          Diese Seite existiert nicht oder wurde verschoben.<br />
          Kein Problem — hier sind ein paar hilfreiche Links:
        </p>

        {/* Quick links */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          {[
            { to: "/dashboard", icon: BarChart3, label: "Dashboard" },
            { to: "/notebook", icon: Brain, label: "Notebook" },
            { to: "/guest-quiz", icon: BookOpen, label: "Quiz" },
          ].map(({ to, icon: Icon, label }) => (
            <Link key={to} to={to}
              className="flex flex-col items-center gap-2 p-4 rounded-xl border transition-all hover:-translate-y-0.5"
              style={{ borderColor: 'rgba(201,168,76,0.08)', background: 'rgba(201,168,76,0.02)' }}>
              <Icon size={20} style={{ color: '#c9a84c' }} />
              <span className="text-xs font-medium">{label}</span>
            </Link>
          ))}
        </div>

        <Link to="/"
          className="inline-flex items-center gap-2 text-sm font-medium transition-colors"
          style={{ color: '#c9a84c' }}>
          <ArrowLeft size={16} />
          Zurück zur Startseite
        </Link>
      </div>
    </div>
  );
}
