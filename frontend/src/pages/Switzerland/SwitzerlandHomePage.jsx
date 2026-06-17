import { Link } from "react-router-dom";

const CARDS = [
  {
    title: "Schweiz Quiz",
    desc: "Medizinische Pruefungsvorbereitung mit Fokus auf Schweizer Lernwege.",
    path: "/guest-quiz",
    emoji: "🇨🇭",
  },
  {
    title: "Fachsprache",
    desc: "Medizinische Begriffe und klinische Kommunikation fuer den deutschsprachigen Raum.",
    path: "/quiz/fachsprache?country=CH&mode=study",
    emoji: "📖",
  },
  {
    title: "KP Protokolle",
    desc: "Pruefungsnahe Protokolle und klinische Faelle, sobald Schweizer Quellen verfuegbar sind.",
    path: "/kp-reports",
    emoji: "🩺",
  },
  {
    title: "KI Tutor",
    desc: "Fragen stellen, Zusammenhaenge verstehen und medizinische Themen gezielt wiederholen.",
    path: "/rag",
    emoji: "🧠",
  },
];

export default function SwitzerlandHomePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">🇨🇭 Schweiz</h1>
        <p className="text-muted-foreground">
          Vorbereitung fuer Schweizer und deutschsprachige medizinische Lernpfade.
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
