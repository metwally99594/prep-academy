import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileText,
  Languages,
  Landmark,
  Stethoscope,
} from "lucide-react";

const CARDS = [
  {
    title: "FSP Simulation",
    desc: "Muendliche Pruefungssimulation fuer die Fachsprachpruefung",
    path: "/de/fsp",
    emoji: "🎤",
  },
  {
    title: "Arztbrief Korrektur",
    desc: "Automatische Korrektur und Feedback fuer Arztbriefe",
    path: "/de/arztbrief",
    emoji: "📝",
  },
  {
    title: "Masterclass",
    desc: "Intensive Vorbereitungskurse fuer die Kenntnispruefung",
    path: "/de/masterclass",
    emoji: "🎓",
  },
  {
    title: "KP Protokolle",
    desc: "Echte Kenntnispruefungs-Protokolle aus Deutschland",
    path: "/kp-reports",
    emoji: "🩺",
  },
  {
    title: "Fachsprache",
    desc: "1500+ medizinische Fachbegriffe Deutsch - Latein",
    path: "/quiz/fachsprache?country=DE&mode=study",
    emoji: "📖",
  },
];

const PATHWAY_STEPS = [
  {
    icon: Landmark,
    title: "1. Zustaendige Approbationsbehoerde finden",
    text: "Der Antrag laeuft ueber das Bundesland, in dem du arbeiten willst. Dort wird entschieden, ob Approbation, Berufserlaubnis, Gleichwertigkeitspruefung oder Kenntnispruefung noetig ist.",
  },
  {
    icon: FileText,
    title: "2. Unterlagen einreichen",
    text: "Typisch sind Diplom, Faechernachweise, Stunden/Logbuch, Identitaet, Lebenslauf, Fuehrungszeugnis/Good Standing, Gesundheitsnachweis und beglaubigte Uebersetzungen.",
  },
  {
    icon: Languages,
    title: "3. Sprache nachweisen",
    text: "In allen Bundeslaendern wird in der Regel allgemeines Deutsch B2 verlangt. Dazu kommt meistens die medizinische Fachsprachpruefung auf C1-Fachsprach-Niveau.",
  },
  {
    icon: BookOpenCheck,
    title: "4. Gleichwertigkeit oder Kenntnispruefung",
    text: "Wenn wesentliche Unterschiede zur deutschen Ausbildung bestehen und nicht durch Berufserfahrung ausgeglichen werden, folgt die Kenntnispruefung.",
  },
  {
    icon: Stethoscope,
    title: "5. Approbation und Weiterbildung",
    text: "Nach erfolgreicher Anerkennung ist die Approbation bundesweit unbefristet. Die Facharztweiterbildung laeuft danach ueber die jeweilige Landesaerztekammer.",
  },
];

const EXAM_POINTS = [
  "Fachsprachpruefung: Arzt-Patient-Gespraech, Arzt-Arzt-Uebergabe, Dokumentation/Arztbrief; Ziel ist sichere medizinische Kommunikation.",
  "Kenntnispruefung: muendlich-praktische Pruefung mit Patientenbezug, meist 60 bis 90 Minuten.",
  "Kernfaecher der KP: Innere Medizin und Chirurgie.",
  "Ergaenzende Themen: Notfallmedizin, Bildgebung, klinische Pharmakologie, Strahlenschutz und Berufsrecht.",
  "Je nach Bescheid kann die Behoerde zusaetzliche Faecher festlegen, wenn dort wesentliche Unterschiede gesehen wurden.",
];

const REQUIREMENTS = [
  "Abgeschlossenes Medizinstudium und Ausbildungsnachweise",
  "Nachweis der persoenlichen Eignung, z. B. Fuehrungszeugnis/Good Standing",
  "Gesundheitliche Eignung",
  "Deutsch B2 plus medizinische Fachsprache C1/FSP",
  "Gleichwertigkeitsbescheid oder bestandene Kenntnispruefung",
  "Optional befristete Berufserlaubnis, wenn das Bundesland sie vor Approbation zulaesst",
];

const SOURCES = [
  {
    label: "Make it in Germany: Physicians",
    href: "https://www.make-it-in-germany.com/en/working-in-germany/professions-in-demand/physicians",
  },
  {
    label: "Bundesaerztekammer: Recognition",
    href: "https://www.bundesaerztekammer.de/en/work-and-training-in-germany/recognition",
  },
  {
    label: "Bundesaerztekammer: Work and training in Germany",
    href: "https://www.bundesaerztekammer.de/en/work-and-training-in-germany",
  },
];

export default function GermanyHomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6 lg:py-10">
      <div className="mb-8 flex flex-col gap-3 border-b border-border/70 pb-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/10 text-sm font-bold text-yellow-600">
            DE
          </span>
          <div>
            <h1 className="text-3xl font-bold tracking-normal">Deutschland</h1>
            <p className="text-sm text-muted-foreground">
              Vorbereitung fuer Approbation, Fachsprachpruefung und Kenntnispruefung.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-yellow-600">
                Approbation fuer Aerzte aus dem Ausland
              </p>
              <h2 className="mt-1 text-2xl font-semibold">Weg zur aerztlichen Taetigkeit in Deutschland</h2>
            </div>
            <ClipboardList className="mt-1 h-6 w-6 text-yellow-600" />
          </div>

          <div className="space-y-3">
            {PATHWAY_STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="flex gap-3 rounded-md border border-border/70 bg-background/70 p-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-yellow-500/10 text-yellow-600">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">{step.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.text}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-yellow-600">Pruefungen und Anforderungen</p>
              <h2 className="mt-1 text-2xl font-semibold">FSP + Kenntnispruefung</h2>
            </div>
            <BookOpenCheck className="mt-1 h-6 w-6 text-yellow-600" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Voraussetzungen
              </h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {REQUIREMENTS.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <Stethoscope className="h-4 w-4 text-yellow-600" />
                Pruefungssystem
              </h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {EXAM_POINTS.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-5 rounded-md border border-border/70 bg-background/70 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <ExternalLink className="h-4 w-4 text-yellow-600" />
              Offizielle Quellen
            </h3>
            <div className="grid gap-2 sm:grid-cols-3">
              {SOURCES.map((source) => (
                <a
                  key={source.href}
                  href={source.href}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-card px-3 py-2 text-sm hover:border-yellow-500 hover:text-yellow-600"
                >
                  <span>{source.label}</span>
                  <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                </a>
              ))}
            </div>
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-lg border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-yellow-600">Prep Academy Tools</p>
            <h2 className="mt-1 text-xl font-semibold">Vorbereitungsmodule</h2>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CARDS.map((card) => (
            <Link key={card.path} to={card.path}>
              <div className="rounded-lg border border-border/60 bg-background p-5 transition-all hover:border-yellow-500/50 hover:shadow-md">
                <div className="mb-3 text-3xl">{card.emoji}</div>
                <h3 className="mb-1 text-lg font-semibold">{card.title}</h3>
                <p className="text-sm leading-6 text-muted-foreground">{card.desc}</p>
                <div className="mt-4 inline-flex items-center text-xs font-medium text-yellow-600">
                  Oeffnen <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
