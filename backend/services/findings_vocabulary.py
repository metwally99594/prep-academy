"""
Medical findings vocabulary — single source of truth for all rule-based data.

Pure data module: no functions, no logic, no imports from this package.
All other modules import FROM here; this module imports from nothing.

Contents:
  ANATOMY_TERMS              — canonical anatomy region names (used in visibility prompt)
  MODALITY_CONSTRAINTS       — per-modality forbidden terms + cannot-diagnose list
  MODALITY_TERM_BLACKLIST    — backward-compatible flat alias for forbidden_terms
  MEDICAL_VOTE_TERMS         — German medical findings for multi-model voting
  FINDING_SEVERITY           — term → (certainty_required, patient_risk) (future calibration)
  LANGUAGE_GATE              — overconfident phrase → (conservative replacement, min_confidence)
  FORBIDDEN_PHRASES_ALWAYS   — phrases replaced unconditionally regardless of confidence
  CATEGORY_KEYWORDS          — expected keyword signals per report type (mismatch detection)
"""

# ═══════════════════════════════════════════════════════════════
# 1. CANONICAL ANATOMY TERMS
# Used to build the VISIBILITY_USER prompt — single place to add/remove regions.
# Order matches the current hardcoded list; do not reorder without updating tests.
# ═══════════════════════════════════════════════════════════════

ANATOMY_TERMS: list[str] = [
    "thorax", "lungs", "heart", "mediastinum", "abdomen",
    "liver", "spleen", "kidneys", "bowel", "pelvis",
    "spine", "bones", "skull", "brain", "extremities",
    "pleura", "diaphragm", "aorta", "ribs", "clavicles", "soft_tissue",
]


# ═══════════════════════════════════════════════════════════════
# 2. MODALITY CONSTRAINTS
# Structured per-modality rules:
#   forbidden_terms  — terms that physically cannot appear in a valid report
#   cannot_diagnose  — conditions that require a different/additional modality
# ═══════════════════════════════════════════════════════════════

MODALITY_CONSTRAINTS: dict[str, dict] = {
    "xray": {
        "forbidden_terms": [
            "Hounsfield", " HU ", "HU-Wert",
            "axiale Schicht", "axiales Bild", "axial geschnitten",
            "enhancement", "Kontrastmittelverhalten", "Kontrastmittelanreicherung",
            "Attenuationskoeffizient", "Attenuierung",
            "Lungenembolie",                  # requires CT-angiography
            "mediastinale Lymphadenopathie",  # requires CT
        ],
        "cannot_diagnose": [
            "Lungenembolie",
            "mediastinale Lymphadenopathie",
        ],
    },
    "ct": {
        "forbidden_terms": [],
        "cannot_diagnose": [],
    },
    "mri": {
        "forbidden_terms": [
            "Hounsfield", " HU ", "HU-Wert",
            "Attenuationskoeffizient",
        ],
        "cannot_diagnose": [],
    },
    "ekg": {
        "forbidden_terms": [
            "Röntgenbefund", "CT-Befund", "Sonographie-Befund",
            "Schichtaufnahme", "axiale Schicht",
        ],
        "cannot_diagnose": [],
    },
    "labs": {
        "forbidden_terms": [
            "Röntgenbefund", "CT-Befund", "Sonographiebefund",
        ],
        "cannot_diagnose": [],
    },
    "ultrasound": {
        "forbidden_terms": [],
        "cannot_diagnose": [],
    },
    "echo": {
        "forbidden_terms": [],
        "cannot_diagnose": [],
    },
}

# Backward-compatible flat alias — existing imports of MODALITY_TERM_BLACKLIST still work.
# Any code doing `from services.findings_vocabulary import MODALITY_TERM_BLACKLIST`
# or using it via analyzer_prompts continues to get the same list structure.
MODALITY_TERM_BLACKLIST: dict[str, list[str]] = {
    k: v.get("forbidden_terms", []) for k, v in MODALITY_CONSTRAINTS.items()
}


# ═══════════════════════════════════════════════════════════════
# 3. MEDICAL VOTE TERMS
# German medical findings for multi-model term-overlap voting.
# Disagreement on these terms contributes to the disagreement score.
# ═══════════════════════════════════════════════════════════════

MEDICAL_VOTE_TERMS: set[str] = {
    # Positive findings (pathological)
    "Infiltrat", "Atelektase", "Pleuraerguss", "Pneumothorax", "Konsolidierung",
    "Ödem", "Nodulus", "Masse", "Ileus", "Perforation", "Fraktur", "Frakturen",
    "Blutung", "Ischämie", "Infarkt", "Thrombose", "Embolie", "Stenose",
    "Dilatation", "Kardiomegalie", "Lymphadenopathie", "Abszess", "Zyste",
    "Erguss", "Aszites", "Pneumonie", "Emphysem", "Fibrose", "Verkalkung",
    # Additional lung/pulmonary pathology
    "Bronchitis", "Bronchopneumonie", "Lungenödem", "Lungenembolie",
    "Bronchiektase", "Lungenkarzinom", "Lungenkontusion",
    # Pleural findings
    "Pleuraschwiele", "Pleuraverkalkung",
    # Cardiovascular
    "Herzinsuffizienz", "Perikarderguss",
    # General pathology
    "Läsion", "Nekrose", "Hernie", "Rezidiv",
    # Tumors / critical findings
    "Metastase", "Karzinom", "Malignom", "Neoplasie", "Tumor",
    # Symptoms / clinical context
    "Fieber", "Husten", "Dyspnoe", "Schmerz", "Tachypnoe", "Hypotonie",
    "Hypertonie", "Ödem peripher", "Zyanose", "Hämoptyse",
    # Normal / negative findings
    "unauffällig", "regelrecht", "kein Nachweis", "kein Hinweis",
    # Organ systems
    "Leber", "Milz", "Niere", "Pankreas", "Galle", "Magen", "Darm",
    "Schilddrüse", "Lymphknoten", "Haut", "Muskel", "Knochen",
    # ECG-specific
    "Vorhofflimmern", "Sinusrhythmus", "Tachykardie", "Bradykardie",
    "Schenkelblock", "ST-Hebung", "ST-Senkung", "AV-Block",
    # Head / neuro
    "Schlaganfall", "Hirnblutung", "Hirninfarkt", "Meningitis",
}


# ═══════════════════════════════════════════════════════════════
# 4. FINDING SEVERITY
# Maps a finding term → (certainty_required, patient_risk_level).
# Intended for future risk-score calibration — not yet used in the pipeline.
# certainty_required: "low" | "medium" | "high"
# patient_risk:       "low" | "moderate" | "critical"
# ═══════════════════════════════════════════════════════════════

FINDING_SEVERITY: dict[str, tuple[str, str]] = {
    "Pneumothorax":     ("high",   "critical"),
    "Blutung":          ("high",   "critical"),
    "Embolie":          ("high",   "critical"),
    "Infarkt":          ("high",   "critical"),
    "Ischämie":         ("high",   "critical"),
    "Malignom":         ("high",   "critical"),
    "Metastase":        ("high",   "critical"),
    "Abszess":          ("high",   "critical"),
    "Ileus":            ("high",   "critical"),
    "Perforation":      ("high",   "critical"),
    "Pleuraerguss":     ("medium", "moderate"),
    "Lymphadenopathie": ("medium", "moderate"),
    "Thrombose":        ("medium", "moderate"),
    "Stenose":          ("medium", "moderate"),
    "Kardiomegalie":    ("medium", "moderate"),
    "Fraktur":          ("medium", "moderate"),
    "Frakturen":        ("medium", "moderate"),
    "Infiltrat":        ("medium", "low"),
    "Konsolidierung":   ("medium", "low"),
    "Atelektase":       ("medium", "low"),
    "Nodulus":          ("medium", "low"),
    "Ödem":             ("medium", "low"),
    "Emphysem":         ("low",    "low"),
    "Fibrose":          ("low",    "low"),
    "Verkalkung":       ("low",    "low"),
    "Zyste":            ("low",    "low"),
    "Dilatation":       ("low",    "low"),
}


# ═══════════════════════════════════════════════════════════════
# 5. LANGUAGE NORMALIZATION RULES
# Overconfident phrase → (conservative replacement, min_confidence_threshold).
# Applied in normalize_clinical_language() when confidence < threshold.
# threshold > 1.0 means "always replace, regardless of confidence".
# ═══════════════════════════════════════════════════════════════

LANGUAGE_GATE: dict[str, tuple[str, float]] = {
    "definitiv":                    ("möglicherweise",                   0.85),
    "beweisend für":                ("vereinbar mit",                    0.85),
    "sicher nachweisbar":           ("fraglich nachweisbar",             0.85),
    "zweifelsfrei":                 ("hinweisend auf",                   0.85),
    "gesicherter":                  ("möglicher",                        0.85),
    "bewiesener":                   ("möglicher",                        0.85),
    "eindeutig diagnostisch":       ("vereinbar mit",                    0.85),
    "hochwahrscheinlich Karzinom":  ("Malignität nicht ausgeschlossen",  1.01),  # always
    "100% sicher":                  ("nicht sicher beurteilbar",         1.01),  # always
}

# Phrases that are always removed (replaced with a warning marker), regardless of confidence.
# Distinct from LANGUAGE_GATE in that they have no valid alternative — they are simply illegal.
FORBIDDEN_PHRASES_ALWAYS: list[str] = [
    "ohne jeden Zweifel",
    "absolut sicher",
    "garantiert diagnostiziert",
    "100%ige Wahrscheinlichkeit",
]


# ═══════════════════════════════════════════════════════════════
# 6. CATEGORY KEYWORDS
# Expected signal words per frontend report_type.
# Used in the category-mismatch check (Step 10 of the pipeline).
# If < 2 keywords found in the primary report, a mismatch warning is shown.
# ═══════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ECG":        ["EKG", "QRS", "P-Welle", "Sinusrhythmus", "Vorhofflimmern",
                   "Herzrhythmus", "RR-Intervall", "ST", "QT", "T-Welle", "Herzfrequenz"],
    "XRay":       ["Röntgen", "Thorax", "Lunge", "Pneumonie", "Atelektase",
                   "Pleura", "Kardiomegalie", "Hilus", "Zwerchfell"],
    "CT":         ["CT", "Computertomographie", "Hounsfield", "Densität",
                   "Schnitt", "axial", "koronal", "sagittal"],
    "MRI":        ["MRT", "Magnetresonanz", "T1", "T2", "FLAIR",
                   "Sequenz", "Signalveränderung", "Hyperintens"],
    "Ultrasound": ["Ultraschall", "Sonographie", "Echostruktur",
                   "hyperechogen", "hypoechogen", "Schallschatten"],
    "BloodTest":  ["Hämoglobin", "Leukozyten", "Thrombozyten", "CRP",
                   "Kreatinin", "GOT", "GPT", "Elektrolyt"],
    "Echo":       ["Echokardiographie", "Ejektionsfraktion", "Wandbewegung",
                   "Mitral", "Aorta", "Perikard", "LVEF"],
}
