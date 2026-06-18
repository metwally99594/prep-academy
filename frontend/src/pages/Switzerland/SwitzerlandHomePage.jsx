import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  ArrowRight,
  BookOpenCheck,
  Building2,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileCheck2,
  GraduationCap,
  Languages,
  Loader2,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { API } from "@/App";
import { Button } from "@/components/ui/button";

const PATHWAY_STEPS = [
  {
    icon: FileCheck2,
    title: "1. Dossier bei MEBEKO klaeren",
    text: "Diplom, Identitaet, Ausbildungsnachweise und bisherige Berufserfahrung sammeln. MEBEKO ist die zentrale Stelle fuer die Pruefung auslaendischer Medizinalberufe.",
  },
  {
    icon: ShieldCheck,
    title: "2. Anerkennung oder Pruefungsweg",
    text: "Bei Abschluessen ausserhalb EU/EFTA ist haeufig kein direkter Anerkennungsweg moeglich. Dann wird der Weg ueber eidgenoessische Anforderungen und Pruefung relevant.",
  },
  {
    icon: GraduationCap,
    title: "3. Eidgenoessische Pruefung Humanmedizin",
    text: "Die Vorbereitung sollte MC-Wissen, klinisches Denken und Clinical-Skills/OSCE-nahe Faelle abdecken. Genau dafuer trennen wir hier MC und praktische Lernpfade.",
  },
  {
    icon: Languages,
    title: "4. Sprache und Kanton",
    text: "Sprachanforderungen richten sich praktisch nach Arbeitsort und Kanton: Deutsch, Franzoesisch oder Italienisch. Die Berufsausuebungsbewilligung laeuft kantonal.",
  },
  {
    icon: Building2,
    title: "5. MedReg und Berufsausuebung",
    text: "Nach erfuellten Voraussetzungen folgen Eintrag/Pruefung der Berufsdaten und kantonale Bewilligung, bevor selbststaendige Berufsausuebung moeglich ist.",
  },
];

const REQUIREMENTS = [
  "Pass/Identitaetsnachweis",
  "Medizindiplom und Faecher-/Stundennachweise",
  "Nachweise ueber klinische Taetigkeit",
  "Good-standing/Unbedenklichkeitsbescheinigung, falls vorhanden",
  "Beglaubigte Uebersetzungen je nach Dokument",
  "Sprachnachweis passend zum Zielkanton",
];

const SOURCES = [
  {
    label: "BAG: Medizinalberufe",
    href: "https://www.bag.admin.ch/bag/de/home/berufe-im-gesundheitswesen/medizinalberufe.html",
  },
  {
    label: "BAG: Medizinalberufekommission MEBEKO",
    href: "https://www.bag.admin.ch/bag/de/home/berufe-im-gesundheitswesen/medizinalberufe/medizinalberufekommission-mebeko.html",
  },
  {
    label: "MedReg",
    href: "https://www.medregom.admin.ch/",
  },
];

const CITY_LABELS = {
  bern: "Bern",
  zurich: "Zuerich",
  basel: "Basel",
  geneva: "Genf",
  lausanne: "Lausanne",
  andere: "Andere",
};

const SUBJECT_LABELS = {
  internal: "Innere Medizin",
  emergency: "Notfallmedizin",
  surgery: "Chirurgie",
  pediatrics: "Paediatrie",
  neurology: "Neurologie",
  obgyn: "Gynaekologie",
  psychiatry: "Psychiatrie",
};

const SWISS_DEFAULT_QUIZ_PATH = "/quiz/custom?country=switzerland&mode=study&limit=50";

const trimQuestion = (text) => {
  if (!text) return "";
  return text.length > 124 ? `${text.slice(0, 124).trim()}...` : text;
};

const isDisplayableMcQuestion = (question) => {
  const text = question?.question_text_de || question?.question_text || "";
  const type = question?.question_type || "single_choice";
  return (
    text.trim().length >= 40 &&
    ["single_choice", "mcq", "multi_select"].includes(type) &&
    (question.status === "published" || !question.status)
  );
};

export default function SwitzerlandHomePage() {
  const [questionCount, setQuestionCount] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [questionError, setQuestionError] = useState("");

  useEffect(() => {
    let mounted = true;
    const token = typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    async function loadSwissQuestions() {
      setLoadingQuestions(true);
      setQuestionError("");
      try {
        const [countRes, questionsRes] = await Promise.all([
          axios.get(`${API}/questions/count?country=switzerland`),
          token
            ? axios.get(`${API}/questions?country=switzerland&limit=30`, { headers })
            : Promise.resolve({ data: [] }),
        ]);
        if (!mounted) return;
        setQuestionCount(countRes.data?.count ?? 0);
        setQuestions(
          (Array.isArray(questionsRes.data) ? questionsRes.data : [])
            .filter(isDisplayableMcQuestion)
            .slice(0, 8)
        );
      } catch (error) {
        if (!mounted) return;
        setQuestionError("Schweizer MC-Fragen konnten gerade nicht geladen werden.");
      } finally {
        if (mounted) setLoadingQuestions(false);
      }
    }

    loadSwissQuestions();
    return () => {
      mounted = false;
    };
  }, []);

  const cityCounts = useMemo(() => {
    return questions.reduce((acc, question) => {
      const city = question.exam_location || question.city || "andere";
      acc[city] = (acc[city] || 0) + 1;
      return acc;
    }, {});
  }, [questions]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6 lg:py-10">
      <div className="mb-8 flex flex-col gap-3 border-b border-border/70 pb-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-sm font-bold text-blue-600">
            CH
          </span>
          <div>
            <h1 className="text-3xl font-bold tracking-normal">Schweiz</h1>
            <p className="text-sm text-muted-foreground">
              Anerkennungsweg fuer Aerzte aus Drittstaaten und Schweizer MC-Vorbereitung.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Drittstaaten / ausserhalb EU-EFTA</p>
              <h2 className="mt-1 text-2xl font-semibold">Weg zur aerztlichen Taetigkeit in der Schweiz</h2>
            </div>
            <ClipboardList className="mt-1 h-6 w-6 text-blue-500" />
          </div>

          <div className="space-y-3">
            {PATHWAY_STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="flex gap-3 rounded-md border border-border/70 bg-background/70 p-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-blue-500/10 text-blue-600">
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

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Typische Unterlagen
              </h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {REQUIREMENTS.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-md border border-border/70 bg-muted/30 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <ExternalLink className="h-4 w-4 text-blue-600" />
                Offizielle Quellen
              </h3>
              <div className="space-y-2">
                {SOURCES.map((source) => (
                  <a
                    key={source.href}
                    href={source.href}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between rounded-md border border-border/60 bg-background px-3 py-2 text-sm hover:border-blue-400 hover:text-blue-600"
                  >
                    <span>{source.label}</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ))}
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Hinweis: Die finale Bewertung ist immer individuell und wird von Behoerden/Kanton entschieden.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">MC-Fragenbank Schweiz</p>
              <h2 className="mt-1 text-2xl font-semibold">Eidgenoessische Pruefung MC</h2>
            </div>
            <BookOpenCheck className="mt-1 h-6 w-6 text-blue-500" />
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border border-blue-500/20 bg-blue-500/10 p-3">
              <div className="text-2xl font-bold text-blue-600">
                {questionCount === null ? "..." : questionCount}
              </div>
              <div className="text-xs text-muted-foreground">CH Fragen</div>
            </div>
            <div className="rounded-md border border-border/70 bg-muted/30 p-3">
              <div className="text-2xl font-bold">{Math.max(Object.keys(cityCounts).length, 5)}</div>
              <div className="text-xs text-muted-foreground">Staedte</div>
            </div>
            <div className="rounded-md border border-border/70 bg-muted/30 p-3">
              <div className="text-2xl font-bold">MC</div>
              <div className="text-xs text-muted-foreground">Pruefungsteil</div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {["bern", "zurich", "basel", "geneva", "lausanne"].map((city) => (
              <Link
                key={city}
                to={`/quiz/custom?country=switzerland&loc=${city}&mode=study&limit=50`}
                className="inline-flex items-center gap-1 rounded-md border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-600 hover:border-blue-400"
              >
                <MapPin className="h-3 w-3" />
                {CITY_LABELS[city]}
              </Link>
            ))}
          </div>

          <div className="mt-5 min-h-[260px] rounded-md border border-border/70">
            {loadingQuestions ? (
              <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Lade Schweizer MC-Fragen...
              </div>
            ) : questionError ? (
              <div className="flex h-56 items-center justify-center px-6 text-center text-sm text-muted-foreground">
                {questionError}
              </div>
            ) : questions.length === 0 ? (
              <div className="flex h-56 flex-col items-center justify-center gap-3 px-6 text-center">
                <p className="text-sm text-muted-foreground">
                  Melde dich an, um die neuesten Schweizer MC-Fragen hier direkt zu sehen.
                </p>
                <Button asChild size="sm">
                  <Link to="/login">Einloggen</Link>
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-border/70">
                {questions.map((question) => (
                  <Link
                    key={question.id}
                    to="/quiz/custom?country=switzerland&mode=study&limit=50"
                    className="block px-4 py-3 hover:bg-muted/40"
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="rounded bg-blue-500/10 px-2 py-0.5 text-xs font-semibold text-blue-600">
                        CH
                      </span>
                      <span className="rounded bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-600">
                        {CITY_LABELS[question.exam_location] || question.exam_location || "Schweiz"}
                      </span>
                      <span className="text-xs text-muted-foreground">{question.year || 2024}</span>
                      <span className="text-xs text-muted-foreground">
                        {SUBJECT_LABELS[question.specialty_id] || question.specialty_id || "Medizin"}
                      </span>
                    </div>
                    <p className="text-sm leading-6">{trimQuestion(question.question_text_de || question.question_text)}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Button asChild>
              <Link to={SWISS_DEFAULT_QUIZ_PATH}>
                MC starten <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/custom-quiz?country=switzerland">
                Eigene Auswahl CH
              </Link>
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
