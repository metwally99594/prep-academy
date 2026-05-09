"""
Analyzer prompts — Master + Subtype + Safety Pipeline.

Architecture:
  Image → Modality Detect → Visibility Detect → Safety Layer Build
        → Analyzer (JSON-first) → Confidence Gate → Modality Validator → Report
"""

import re as _re
import json as _json
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# MASTER PROMPT — injected into every analysis regardless of modality
# ═══════════════════════════════════════════════════════════════

MASTER_PROMPT = """Du bist ein konservativer medizinischer KI-Assistent, spezialisiert auf strukturierte klinische Bild- und Befundanalyse.

PRIMÄRES ZIEL:
Sichere, begrenzte, evidenzbasierte Beobachtungen aus den bereitgestellten medizinischen Daten liefern.

KERNREGELN:
1. Erfinde NIEMALS Befunde.
2. Erfinde NIEMALS Messwerte.
3. Schätze NIEMALS Wahrscheinlichkeiten, außer wenn explizit angefragt.
4. Bei Unsicherheit: Unsicherheit explizit benennen.
5. Analysiere AUSSCHLIESSLICH tatsächlich sichtbare Anatomie.
6. Halluziniere NIEMALS verborgene Strukturen.
7. Unterscheide klar zwischen: beobachteten Befunden | möglicher Interpretation | Differentialdiagnose.
8. Überschätze NIEMALS die Konfidenz.
9. Bevorzuge "nicht ausgeschlossen" gegenüber definitiver Diagnose.
10. Bei eingeschränkter Bildqualität: Limitation explizit erwähnen.
11. Schließe KEINE klinische Vorgeschichte, wenn nicht angegeben.
12. Stelle KEINE finale medizinische Diagnose.
13. Vermeide medizinisch-rechtlich gefährliche Aussagen.
14. Wenn die Modalität für die Beurteilung unzureichend ist: "Nicht sicher beurteilbar."

STRENG VERBOTEN:
- Erfundene Messwerte / HU-Werte / Prozentzahlen / Staging
- Erfundene Metastasen- oder Embolie-Befunde
- Erfundene Malignitätssicherheit
- Erfundene Anatomie oder unsichtbare Pathologie

AUSGABESTIL: präzise, radiologisch, medizinisch vorsichtig, strukturiert.

Sprache: Deutsches medizinisches Format.

Wenn die Sichtbarkeit unzureichend ist: "Nicht sicher beurteilbar." statt Spekulation.
"""

# ═══════════════════════════════════════════════════════════════
# SUBTYPE PROMPTS — modality-specific rules appended to MASTER
# ═══════════════════════════════════════════════════════════════

SUBTYPE_PROMPTS = {
    "xray": """Modalität: Konventionelles Röntgen (Projektionsradiographie).

Regeln:
- Dies ist KEIN CT und KEIN MRT.
- Erwähne NIEMALS Hounsfield-Einheiten (HU).
- Beschreibe KEINE axialen Schichten.
- Beurteile AUSSCHLIESSLICH sichtbare Anatomie.
- Wenn Thorax nur partiell sichtbar: "Thorax nur partiell beurteilbar."
- Wenn Abdomen nur partiell sichtbar: "Abdomen nur eingeschränkt beurteilbar."

Erlaubt:
- Darmgasmuster, Stuhlbelastung, freie Luft
- Frakturen, Alignment, Achsabweichungen
- Sichtbare Infiltrate, eindeutiger Pleuraerguss, eindeutiger Pneumothorax

Verboten:
- Diagnose einer Lungenembolie
- Mediastinale Lymphadenopathie
- Subtiles Tumorstaging
- Mikroskopische Interpretationen
""",

    "ct": """Modalität: Computertomographie (CT).

Regeln:
- Analysiere NUR in bereitgestellten Schichten sichtbare Strukturen.
- Bei unbekanntem Kontrastmittelstatus: "Kontrastmittelstatus unklar."
- Bei unvollständiger Serie: Limitation erwähnen.

Erlaubt:
- Dichtebeschreibung (nur wenn Schichten vorhanden), Masseneffekt
- Hämorrhagie, Flüssigkeit, Konsolidierung, Frakturen
- Organvergrößerung, Obstruktion

Verboten:
- Präzises onkologisches Staging, außer wenn eindeutig
- Unbelegte Malignitätssicherheit
- Erfundene Messwerte
""",

    "mri": """Modalität: Magnetresonanztomographie (MRT).

Regeln:
- Sequenzqualität kann eingeschränkt sein.
- Bei unbekannten Sequenzen: "Sequenztyp nicht eindeutig identifizierbar."

Erlaubt:
- Weichteil-Signalauffälligkeiten, Ödem
- Bandscheibenpathologie, Bänder-/Sehnenveränderungen
- Flüssigkeitskollektionen

Verboten:
- CT-Terminologie, HU-Werte
- Unbelegte Gewebscharakterisierung
""",

    "ekg": """Modalität: 12-Kanal-EKG.

Analysiere: Rhythmus, Herzfrequenz, Achse, PQ/QRS/QTc, ST-T-Veränderungen, Arrhythmien.

Regeln:
- Diagnostiziere KEINEN Myokardinfarkt mit Sicherheit, außer bei klassischem Bild.
- Bei Artefakten: Limitation erwähnen.
- Unterscheide "unspezifische Veränderungen" vs. akute Pathologie.

Ausgabe:
1. Rhythmus
2. Frequenz
3. Intervalle (PQ, QRS, QTc)
4. Auffälligkeiten
5. Beurteilung
""",

    "ultrasound": """Modalität: Ultraschall / Sonographie.

Regeln:
- Ultraschallqualität abhängig von Untersucher und akustischem Fenster.
- Eingeschränkte Sichtbarkeit erwähnen, wenn vorhanden.

Erlaubt:
- Flüssigkeit, Gallensteine, Organvergrößerung
- Zystisch vs. solide Erscheinung
- Vaskulärer Fluss bei vorhandenem Doppler

Verboten:
- Definitive Malignitätsaussagen
- CT/MRT-Niveau Gewebscharakterisierung
""",

    "echo": """Modalität: Echokardiographie.

Analysiere: Kammergrößen, LV-Funktion (nur wenn sichtbar), Perikarderguss, grobe Klappenveränderungen.

Regeln:
- Bei nicht zuverlässig schätzbarer EF: "Ejektionsfraktion nicht sicher beurteilbar."

Verboten:
- Erfundene EF-Werte
- Klappengradierung ohne Doppler-Evidenz
""",

    "labs": """Modalität: Laborwerte / Blutbild.

Analysiere Laborwerte konservativ.

Regeln:
- Pathologische Werte markieren (↑ / ↓ mit Referenzbereich).
- Klinisch korrelieren.
- Keine definitive Diagnose allein aus Laborwerten.

Ausgabe:
1. Auffällige Werte
2. Mögliche Bedeutung
3. Differentialdiagnosen
4. Empfehlung
""",
}

# ═══════════════════════════════════════════════════════════════
# VISIBILITY DETECTION — Step 2 of the pipeline
# Quick pre-analysis call to determine what the image actually shows.
# ═══════════════════════════════════════════════════════════════

VISIBILITY_SYSTEM = (
    "You are a medical image visibility analyzer. "
    "You output ONLY valid JSON with no markdown, no explanation."
)

VISIBILITY_USER = """Examine this medical image carefully.
Identify which anatomical regions are clearly visible, partially visible, or not visible at all.

Output ONLY JSON in this exact format (no other text):
{"visible": ["region1", "region2"], "partial": ["region3"], "hidden": ["region4"], "image_quality": "good|limited|poor"}

Use these anatomical terms:
thorax, lungs, heart, mediastinum, abdomen, liver, spleen, kidneys, bowel, pelvis,
spine, bones, skull, brain, extremities, pleura, diaphragm, aorta, ribs, clavicles, soft_tissue

If image quality is too poor to assess:
{"visible": [], "partial": [], "hidden": [], "image_quality": "poor"}"""

# ═══════════════════════════════════════════════════════════════
# STRUCTURED JSON FORMAT — appended to system prompt
# Forces model to commit to what it saw before writing narrative.
# This is the core anti-hallucination mechanism for Step 4.
# ═══════════════════════════════════════════════════════════════

STRUCTURED_JSON_SUFFIX = """

=== PFLICHTFORMAT — STRIKTE REIHENFOLGE ===

SCHRITT 1: Gib zuerst einen JSON-Block zwischen <<<JSON>>> und <<<END_JSON>>> aus:
<<<JSON>>>
{
  "visible_regions": ["sichtbare anatomische Region 1"],
  "partial_regions": ["nur teilweise sichtbare Region"],
  "visible_findings": ["Befund 1 in konservativem Stil", "Befund 2"],
  "uncertain_findings": ["Möglicher Befund — Bestätigung erforderlich"],
  "limitations": ["Limitation 1", "Limitation 2"],
  "forbidden_sections_skipped": ["Was übersprungen wurde und warum"]
}
<<<END_JSON>>>

SCHRITT 2: Danach der deutsche Radiologiebericht in Abschnitten:
## 1. Technik
## 2. Befund
## 3. Beurteilung
## 4. Limitationen

PFLICHTREGELN FÜR BEFUNDSPRACHE — KEINE AUSNAHMEN:
- VERBOTEN:  "Pneumonie mit 85% Wahrscheinlichkeit"
  PFLICHT:   "Unspezifische Verschattung im rechten Unterfeld — Pneumonie nicht ausgeschlossen"
- VERBOTEN:  "Metastase erkennbar" / "Malignom bestätigt"
  PFLICHT:   "Rundliche Dichtezunahme — Dignität nicht sicher beurteilbar"
- VERBOTEN:  "Lungenembolie" (auf konventionellem Röntgen)
  PFLICHT:   "Emboliediagnostik erfordert CT-Angiographie — röntgenologisch nicht beurteilbar"
- VERBOTEN:  "Kardiomegalie" (auf Abdominalröntgen)
  PFLICHT:   "Herzschatten nicht vollständig beurteilbar"
- PFLICHT:   "vereinbar mit", "nicht ausgeschlossen", "fraglich", "möglicherweise" bei Interpretationen
"""

# ═══════════════════════════════════════════════════════════════
# MODALITY TERM BLACKLIST — Step 5 hard validation
# Terms that physically cannot appear in a valid report for that modality.
# ═══════════════════════════════════════════════════════════════

MODALITY_TERM_BLACKLIST: dict[str, list[str]] = {
    "xray": [
        "Hounsfield", " HU ", "HU-Wert",
        "axiale Schicht", "axiales Bild", "axial geschnitten",
        "enhancement", "Kontrastmittelverhalten", "Kontrastmittelanreicherung",
        "Attenuationskoeffizient", "Attenuierung",
        "Lungenembolie",                   # requires CT-angio
        "mediastinale Lymphadenopathie",   # requires CT
    ],
    "mri": [
        "Hounsfield", " HU ", "HU-Wert",
        "Attenuationskoeffizient",
    ],
    "ekg": [
        "Röntgenbefund", "CT-Befund", "Sonographie-Befund",
        "Schichtaufnahme", "axiale Schicht",
    ],
    "labs": [
        "Röntgenbefund", "CT-Befund", "Sonographiebefund",
    ],
    "ct": [],
    "ultrasound": [],
    "echo": [],
}

# ═══════════════════════════════════════════════════════════════
# CATEGORY ROUTING
# ═══════════════════════════════════════════════════════════════

REPORT_TYPE_MAP = {
    "ECG":        "ekg",
    "XRay":       "xray",
    "CT":         "ct",
    "MRI":        "mri",
    "Ultrasound": "ultrasound",
    "BloodTest":  "labs",
    "Echo":       "echo",
    "Other":      "",
}

VALID_CATEGORIES = set(SUBTYPE_PROMPTS.keys())

_ALIASES = {
    "x-ray": "xray", "röntgen": "xray", "roentgen": "xray",
    "ct-scan": "ct", "ct_scan": "ct", "computed_tomography": "ct",
    "mrt": "mri", "magnetresonanz": "mri",
    "ecg": "ekg", "elektrokardiogramm": "ekg",
    "us": "ultrasound", "sonography": "ultrasound", "sonographie": "ultrasound",
    "echocardiography": "echo", "echokardiographie": "echo",
    "blutbild": "labs", "lab": "labs", "laborwerte": "labs",
}

# ═══════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def build_prompt(
    category: str,
    safety_layer: dict | None = None,
    include_json_format: bool = True,
) -> str:
    """
    Build complete system prompt:
      MASTER + SUBTYPE + (optional) DYNAMIC SAFETY LAYER + JSON FORMAT INSTRUCTIONS

    Args:
        category: modality key (xray, ct, mri, ekg, ultrasound, echo, labs) or alias
        safety_layer: optional dict from visibility detection:
            {"visible_regions": [...], "partial_regions": [...], "forbidden_assessment": [...]}
        include_json_format: append structured JSON output instructions (default True)
    """
    cat = _ALIASES.get((category or "").lower().strip(), (category or "").lower().strip())
    subtype = SUBTYPE_PROMPTS.get(cat, "")

    parts = [MASTER_PROMPT.strip(), subtype.strip()]

    if safety_layer:
        parts.append(
            "DYNAMISCHER SICHERHEITSKONTEXT (aus automatischer Sichtbarkeitserkennung):\n"
            + _json.dumps(safety_layer, ensure_ascii=False, indent=2)
            + "\n\nAnweisungen:"
            "\n- Kommentiere NICHTS unter 'forbidden_assessment' — diese Regionen sind nicht sichtbar."
            "\n- Behandle 'partial_regions' als nur eingeschränkt beurteilbar."
            "\n- Analysiere AUSSCHLIESSLICH die 'visible_regions'.\n"
        )

    if include_json_format:
        parts.append(STRUCTURED_JSON_SUFFIX.strip())

    return "\n\n".join(p for p in parts if p)


def parse_visibility_response(raw: str) -> dict:
    """
    Extract visibility JSON from LLM response.
    Returns fallback dict if parsing fails.
    """
    default = {"visible": [], "partial": [], "hidden": [], "image_quality": "unknown"}
    if not raw:
        return default
    raw = raw.strip()
    # Try direct parse
    try:
        data = _json.loads(raw)
        if isinstance(data, dict):
            return {**default, **data}
    except Exception:
        pass
    # Extract first {...} block
    m = _re.search(r'\{[^{}]*\}', raw, _re.DOTALL)
    if m:
        try:
            data = _json.loads(m.group(0))
            if isinstance(data, dict):
                return {**default, **data}
        except Exception:
            pass
    return default


def parse_analysis_json(raw: str) -> dict | None:
    """
    Extract structured JSON block from the model's <<<JSON>>>...<<<END_JSON>>> markers.
    Returns None if not present or unparseable.
    """
    if not raw:
        return None
    m = _re.search(r'<<<JSON>>>(.*?)<<<END_JSON>>>', raw, _re.DOTALL)
    if not m:
        return None
    try:
        data = _json.loads(m.group(1).strip())
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def strip_analysis_json_block(raw: str) -> str:
    """Remove the <<<JSON>>>...<<<END_JSON>>> block from text for display."""
    cleaned = _re.sub(r'<<<JSON>>>.*?<<<END_JSON>>>', '', raw, flags=_re.DOTALL)
    cleaned = _re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def apply_confidence_gate(text: str, confidence: float) -> str:
    """
    Post-processing safety gate based on confidence level.

    confidence thresholds (normalized 0-1):
      >= 0.75  → HIGH   — no modifications
      0.60-0.74 → MEDIUM — remove percentage values from differentials
      < 0.60   → LOW    — disable differentials, flag malignancy terms, add notice

    confidence is derived from: {1 model: 0.55, 2 models: 0.72, 3 models: 0.85}
    """
    if confidence >= 0.75:
        return text

    # MEDIUM + LOW: strip probability percentages everywhere
    text = _re.sub(r'\b(\d+)\s*%', r'(Prozentangabe entfernt)', text)

    if confidence < 0.60:
        # LOW: replace differential diagnosis section
        text = _re.sub(
            r'(##\s*(?:Differential(?:diagnos\w*)|Differenzialdiagnos\w*))(.*?)(?=\n##|\Z)',
            (
                r'\1\n_Differentialdiagnosen wurden aufgrund eingeschränkter Konfidenz deaktiviert. '
                r'Klinische Korrelation erforderlich._\n'
            ),
            text,
            flags=_re.DOTALL | _re.IGNORECASE,
        )

        # LOW: flag high-risk terms
        _HIGH_RISK = [
            "Karzinom", "Karzinoms", "Karzinome",
            "Malignom", "Malignoms", "Malignome",
            "Metastase", "Metastasen",
            "Neoplasie", "Neoplasien",
            "maligne", "maligner", "malignes",
        ]
        for term in _HIGH_RISK:
            text = _re.sub(
                rf'\b{_re.escape(term)}\b',
                f'[{term} — Konfidenz zu niedrig für diese Aussage]',
                text,
                flags=_re.IGNORECASE,
            )

        # Add confidence notice at end
        text += (
            "\n\n---\n"
            "ℹ️ **Konfidenz-Hinweis:** Nur ein KI-Modell hat geantwortet. "
            "Differentialdiagnosen und Prozentwerte wurden deaktiviert. "
            "Ärztliche Überprüfung dringend empfohlen."
        )

    return text


def validate_modality_output(text: str, category: str) -> tuple[str, list[str]]:
    """
    Hard validation — detect forbidden modality-specific terms in the output.

    Returns (original_text, list_of_violations).
    Does NOT modify the text — violations are reported as warnings to the caller.
    The caller decides whether to show/suppress.
    """
    violations: list[str] = []
    blacklist = MODALITY_TERM_BLACKLIST.get((category or "").lower(), [])
    text_lower = text.lower()
    for term in blacklist:
        if term.lower() in text_lower:
            violations.append(f"Verbotener Begriff für {category.upper()}: '{term}'")
    return text, violations


def build_safety_layer_from_visibility(visibility_data: dict) -> dict | None:
    """
    Convert visibility detection output into a safety_layer dict for build_prompt.

    Returns None if nothing is hidden/partial (no restriction needed).
    """
    hidden = visibility_data.get("hidden", [])
    partial = visibility_data.get("partial", [])
    visible = visibility_data.get("visible", [])
    if not hidden and not partial:
        return None
    return {
        "visible_regions": visible,
        "partial_regions": partial,
        "forbidden_assessment": hidden,
    }
