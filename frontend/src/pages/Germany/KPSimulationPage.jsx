import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  HelpCircle,
  RotateCcw,
  Stethoscope,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const CASES = [
  {
    id: "chest-pain",
    title: "Akuter Thoraxschmerz",
    specialty: "Innere Medizin / Notfall",
    patient: "58-jaehriger Patient mit retrosternalem Druckschmerz seit 45 Minuten, Kaltschweissigkeit und Uebelkeit. Risikofaktoren: Hypertonie, Rauchen.",
    tasks: [
      "Strukturierte Anamnese und Leitsymptom einordnen",
      "Akutes Koronarsyndrom erkennen und Sofortmassnahmen nennen",
      "EKG, Troponin, Monitoring und Antikoagulation/Thrombozytenhemmung begruenden",
    ],
    examiner: [
      "Welche Differentialdiagnosen muessen Sie sofort ausschliessen?",
      "Wie gehen Sie in den ersten zehn Minuten vor?",
      "Welche Medikamente geben Sie und welche Kontraindikationen pruefen Sie?",
      "Wann ist eine sofortige Koronarangiographie indiziert?",
    ],
  },
  {
    id: "acute-abdomen",
    title: "Akutes Abdomen",
    specialty: "Chirurgie / Innere Medizin",
    patient: "43-jaehrige Patientin mit zunehmenden rechtsseitigen Unterbauchschmerzen, Fieber 38,6 C, Abwehrspannung und Erbrechen.",
    tasks: [
      "Akutes Abdomen strukturiert untersuchen",
      "Appendizitis, gyn. Ursachen, Ileus und Divertikulitis abgrenzen",
      "Labor, Sonographie/CT und OP-Indikation begruenden",
    ],
    examiner: [
      "Welche klinischen Zeichen pruefen Sie?",
      "Welche Laborwerte und Bildgebung sind sinnvoll?",
      "Wann operieren Sie sofort?",
      "Welche perioperativen Risiken klaeren Sie auf?",
    ],
  },
  {
    id: "dyspnea",
    title: "Akute Dyspnoe",
    specialty: "Innere Medizin / Pneumologie",
    patient: "71-jaehrige Patientin mit akuter Luftnot, AF 30/min, SpO2 86 Prozent, Beinwellung rechts und pleuritischem Schmerz.",
    tasks: [
      "ABC-Einschaetzung und Sauerstoffstrategie darstellen",
      "Lungenembolie, Pneumonie, Herzinsuffizienz und Pneumothorax abgrenzen",
      "D-Dimer, CT-Angiographie, Antikoagulation und Risikostratifizierung begruenden",
    ],
    examiner: [
      "Welche Sofortmassnahmen leiten Sie ein?",
      "Wie schaetzen Sie die Wahrscheinlichkeit einer Lungenembolie ein?",
      "Welche Befunde sprechen fuer Rechtsherzbelastung?",
      "Wann ist Lyse oder Intensivtherapie noetig?",
    ],
  },
];

const RUBRIC = [
  "Struktur: Vorstellung mit Alter, Leitsymptom, relevanten Befunden, Verdachtsdiagnose und Plan.",
  "Klinik: lebensbedrohliche Differentialdiagnosen zuerst nennen.",
  "Diagnostik: Untersuchung, Labor und Bildgebung begruenden statt nur aufzaehlen.",
  "Therapie: Sofortmassnahmen, Medikamente, Monitoring und Eskalation klar darstellen.",
  "Kommunikation: kurz, geordnet, pruefungsnah und ohne Abschweifen antworten.",
];

export default function KPSimulationPage() {
  const [caseId, setCaseId] = useState(CASES[0].id);
  const [stage, setStage] = useState("setup");
  const [presentation, setPresentation] = useState("");
  const [answers, setAnswers] = useState({});
  const [checked, setChecked] = useState({});

  const activeCase = useMemo(() => CASES.find((item) => item.id === caseId) || CASES[0], [caseId]);
  const completed = Object.values(checked).filter(Boolean).length;

  const reset = () => {
    setStage("setup");
    setPresentation("");
    setAnswers({});
    setChecked({});
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 lg:px-6 lg:py-10">
      <Link to="/de">
        <Button variant="ghost" size="sm" className="mb-6 gap-1">
          <ArrowLeft className="h-4 w-4" /> Zurueck
        </Button>
      </Link>

      <div className="mb-6 flex items-start justify-between gap-4 border-b border-border/70 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-yellow-600">Kenntnispruefung Simulation</p>
          <h1 className="mt-1 text-3xl font-bold tracking-normal">Muendlich-praktische KP</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Trainiere den typischen Ablauf: Fall erfassen, Patientenvorstellung halten und Prueferfragen aus Innerer Medizin,
            Chirurgie, Notfallmedizin, Pharmakologie und Berufsrecht strukturiert beantworten.
          </p>
        </div>
        <ClipboardCheck className="mt-1 h-7 w-7 text-yellow-600" />
      </div>

      {stage === "setup" ? (
        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-4 text-xl font-semibold">Fall waehlen</h2>
            <div className="space-y-3">
              {CASES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setCaseId(item.id)}
                  className={`w-full rounded-md border p-4 text-left transition-all ${
                    caseId === item.id ? "border-yellow-500 bg-yellow-500/10" : "border-border/70 bg-background hover:border-yellow-500/50"
                  }`}
                >
                  <div className="font-semibold">{item.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{item.specialty}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 text-xl font-semibold">
              <Stethoscope className="h-5 w-5 text-yellow-600" />
              Ablauf der Simulation
            </h2>
            <div className="space-y-3 text-sm leading-6 text-muted-foreground">
              <p>1. Du liest den Fall und notierst die wichtigsten Befunde.</p>
              <p>2. Du formulierst eine kurze Patientenvorstellung wie vor einer Pruefungskommission.</p>
              <p>3. Du beantwortest typische Prueferfragen und hakst die Kernpunkte ab.</p>
              <p>4. Am Ende bekommst du eine strukturierte Selbstkontrolle mit KP-Rubrik.</p>
            </div>
            <Button className="mt-6 w-full gap-2" onClick={() => setStage("case")}>
              Simulation starten <CheckCircle2 className="h-4 w-4" />
            </Button>
          </section>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-yellow-600">{activeCase.specialty}</p>
                <h2 className="mt-1 text-xl font-semibold">{activeCase.title}</h2>
              </div>
              <button type="button" onClick={reset} className="rounded-md border border-border p-2 text-muted-foreground hover:text-foreground">
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>

            <div className="rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <FileText className="h-4 w-4 text-yellow-600" />
                Patientenfall
              </h3>
              <p className="text-sm leading-6 text-muted-foreground">{activeCase.patient}</p>
            </div>

            <div className="mt-4">
              <label className="text-sm font-semibold">Patientenvorstellung</label>
              <textarea
                value={presentation}
                onChange={(event) => setPresentation(event.target.value)}
                rows={7}
                className="mt-2 w-full rounded-md border border-border bg-background p-3 text-sm leading-6 outline-none focus:border-yellow-500"
                placeholder="Beispiel: Es handelt sich um einen ... mit ... Fuehrend ist der Verdacht auf ..."
              />
            </div>
          </section>

          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
              <HelpCircle className="h-5 w-5 text-yellow-600" />
              Prueferfragen
            </h2>
            <div className="space-y-4">
              {activeCase.examiner.map((question, index) => (
                <div key={question} className="rounded-md border border-border/70 bg-background p-4">
                  <div className="mb-2 text-sm font-semibold">{index + 1}. {question}</div>
                  <textarea
                    value={answers[index] || ""}
                    onChange={(event) => setAnswers((current) => ({ ...current, [index]: event.target.value }))}
                    rows={3}
                    className="w-full rounded-md border border-border bg-card p-3 text-sm outline-none focus:border-yellow-500"
                    placeholder="Antwort strukturieren: Diagnose, Begruendung, naechster Schritt..."
                  />
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-3 text-sm font-semibold">KP Checkliste ({completed}/{RUBRIC.length})</h3>
              <div className="space-y-2">
                {RUBRIC.map((item, index) => (
                  <label key={item} className="flex cursor-pointer gap-2 text-sm leading-6 text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={Boolean(checked[index])}
                      onChange={(event) => setChecked((current) => ({ ...current, [index]: event.target.checked }))}
                      className="mt-1"
                    />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
