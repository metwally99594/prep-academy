export const SPECIALTY_LABELS = {
  cardiology: "Kardiologie",
  radiology: "Radiologie",
  neurology: "Neurologie",
  pediatrics: "Pädiatrie",
  surgery: "Chirurgie",
  internal_medicine: "Innere Medizin",
  orthopedics: "Orthopädie",
  dermatology: "Dermatologie",
  ophthalmology: "Ophthalmologie",
  gynecology: "Gynäkologie",
  urology: "Urologie",
  psychiatry: "Psychiatrie",
  emergency_medicine: "Notfallmedizin",
  anesthesiology: "Anästhesiologie",
  pathology: "Pathologie",
  pharmacology: "Pharmakologie",
  microbiology: "Mikrobiologie",
  public_health: "Öffentl. Gesundheit",
  anatomy: "Anatomie",
  physiology: "Physiologie",
  biochemistry: "Biochemie",
};

export const TOPIC_LABELS = {
  diagnosis: "Diagnose",
  treatment: "Behandlung",
  guidelines: "Leitlinien",
  case_report: "Fallbericht",
  exam_prep: "Prüfungsvorbereitung",
  study_tips: "Lerntipps",
  research: "Forschung",
  clinical_skills: "Klinische Fähigkeiten",
  medical_education: "Medizinische Ausbildung",
  career: "Karriere",
  technology: "Technologie",
  ethics: "Ethik",
};

export const POST_TYPE_OPTIONS = [
  { value: "discussion", label: "Diskussion", icon: "💬", description: "Allgemeine Diskussion" },
  { value: "question", label: "Frage", icon: "❓", description: "Frage stellen" },
  { value: "case_study", label: "Fallstudie", icon: "🏥", description: "Klinischen Fall teilen" },
  { value: "resource", label: "Ressource", icon: "📚", description: "Ressource empfehlen" },
];

export const POST_TYPE_LABELS = {
  discussion: "Diskussion",
  question: "Frage",
  case_study: "Fallstudie",
  resource: "Ressource",
};

export const SORT_OPTIONS = [
  { value: "recent", label: "Neueste" },
  { value: "top", label: "Top" },
  { value: "discussed", label: "Diskutiert" },
  { value: "trending", label: "Trending" },
];

export const SPECIALTY_OPTIONS = Object.entries(SPECIALTY_LABELS).map(([value, label]) => ({ value, label }));
export const TOPIC_OPTIONS = Object.entries(TOPIC_LABELS).map(([value, label]) => ({ value, label }));
