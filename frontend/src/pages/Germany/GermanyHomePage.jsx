import { Link } from "react-router-dom";

const CARDS = [
  {
    title: "FSP Simulation",
    desc: "Mündliche Prüfungssimulation für die Fachsprachprüfung",
    path: "/de/fsp",
    emoji: "🎤",
  },
  {
    title: "Arztbrief Korrektur",
    desc: "Automatische Korrektur & Feedback für Arztbriefe",
    path: "/de/arztbrief",
    emoji: "📝",
  },
  {
    title: "Masterclass",
    desc: "Intensive Vorbereitungskurse für die Kenntnisprüfung",
    path: "/de/masterclass",
    emoji: "🎓",
  },
  {
    title: "KP Protokolle",
    desc: "Echte Kenntnisprüfungs-Protokolle aus Deutschland",
    path: "/kp-reports",
    emoji: "🩺",
  },
  {
    title: "Fachsprache",
    desc: "1500+ medizinische Fachbegriffe Deutsch — Latein",
    path: "/quiz/fachsprache?country=DE&mode=study",
    emoji: "📖",
  },
];

export default function GermanyHomePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">🇩🇪 Deutschland</h1>
        <p className="text-muted-foreground">
          Vorbereitung für die Kenntnisprüfung und Fachsprachprüfung
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {CARDS.map((card) => (
          <Link key={card.path} to={card.path}>
            <div className="rounded-xl border border-border/60 bg-card p-6 hover:border-primary/40 hover:shadow-md transition-all">
              <div className="text-3xl mb-3">{card.emoji}</div>
              <h2 className="text-lg font-semibold mb-1">{card.title}</h2>
              <p className="text-sm text-muted-foreground">{card.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
