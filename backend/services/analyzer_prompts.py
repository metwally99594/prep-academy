"""
Analyzer prompts - Master + Subtype + Safety Pipeline.

Architecture:
  Image → Modality Detect → Visibility Detect → Safety Layer Build
        → Analyzer (JSON-first) → Confidence Gate → Modality Validator → Report

Vocabulary: rule-based data (blacklists, vote terms, language gate) lives in
findings_vocabulary.py - this module imports and re-exports for backward compat.
"""

import re as _re
import json as _json
from typing import Optional

from services.findings_vocabulary import (
    ANATOMY_TERMS        as _ANATOMY_TERMS,
    MODALITY_CONSTRAINTS,
    MEDICAL_VOTE_TERMS   as _MEDICAL_VOTE_TERMS,
    LANGUAGE_GATE        as _LANGUAGE_GATE,
    FORBIDDEN_PHRASES_ALWAYS as _FORBIDDEN_ALWAYS,
)

# ═══════════════════════════════════════════════════════════════
# STRICT JSON SCHEMA VALIDATION
# Validates the model's <<<JSON>>> block against a known schema.
# Returns errors WITHOUT modifying the report text.
# ═══════════════════════════════════════════════════════════════

_VALID_IMAGE_QUALITY_VALUES = {"good", "limited", "poor", "unknown"}

_REQUIRED_JSON_FIELDS = {
    "visible_regions":          list,
    "partial_regions":          list,
    "visible_findings":         list,
    "uncertain_findings":       list,
    "limitations":              list,
    "forbidden_sections_skipped": list,
}


def validate_json_schema(data: dict | None) -> dict:
    """
    Strict schema validation for the model's <<<JSON>>> block.

    Returns:
        {
            "valid":       bool,
            "errors":      list[str],   # human-readable error strings
            "schema_ok":   bool,        # True if all required fields present and typed
            "quality_ok":  bool,        # True if image_quality is a known value
        }

    Does NOT modify any report text.
    """
    result = {"valid": False, "errors": [], "schema_ok": False, "quality_ok": True}

    if data is None:
        result["errors"].append("JSON block not present or unparseable")
        return result

    if not isinstance(data, dict):
        result["errors"].append(f"JSON root must be object, got {type(data).__name__}")
        return result

    for field, expected_type in _REQUIRED_JSON_FIELDS.items():
        if field not in data:
            result["errors"].append(f"Fehlendes Pflichtfeld: '{field}'")
            continue
        if not isinstance(data[field], list):
            result["errors"].append(
                f"Feld '{field}' muss Liste sein, got {type(data[field]).__name__}"
            )
            continue
        # All list items must be strings (no nested dicts or numbers)
        for idx, item in enumerate(data[field]):
            if not isinstance(item, str):
                result["errors"].append(
                    f"'{field}[{idx}]' muss String sein, got {type(item).__name__}: {repr(item)[:50]}"
                )

    result["schema_ok"] = len(result["errors"]) == 0

    # Quality field validation (if present)
    if "image_quality" in data:
        qv = data["image_quality"]
        if not isinstance(qv, str) or qv.lower() not in _VALID_IMAGE_QUALITY_VALUES:
            result["errors"].append(
                f"Ungültiger image_quality-Wert: '{qv}' (erlaubt: {', '.join(sorted(_VALID_IMAGE_QUALITY_VALUES))})"
            )
            result["quality_ok"] = False

    # Soft check: warn if all required fields are empty lists (model may have refused)
    non_empty = any(
        isinstance(data.get(f), list) and len(data.get(f, [])) > 0
        for f in _REQUIRED_JSON_FIELDS
    )
    if result["schema_ok"] and not non_empty:
        result["errors"].append(
            "Warnung: Alle Felder sind leer - Modell hat möglicherweise keine Befunde extrahiert"
        )

    result["valid"] = result["schema_ok"]
    return result


# ═══════════════════════════════════════════════════════════════
# CANONICAL ANATOMY VOCABULARY VALIDATION
# All anatomical region names must come from a known set.
# Prevents hallucinated anatomy terms like "Herzventrikel",
# "Lungenlappen rechts unten anterior", etc.
# ═══════════════════════════════════════════════════════════════

_CANONICAL_ANATOMY: dict[str, set[str]] = {
    "thorax":    {"thorax", "lungen", "lungenfeld", "lunge", "herz", "mediastinum",
                  "pleura", "zwerchfell", "diaphragma", "rippen", "clavicula", "clavicles",
                  "hilum", "hili", "肋骨", "胸部"},  # German + some Latin + Chinese fallback
    "abdomen":   {"abdomen", "bauch", "leber", "magen", "milz", "pankreas", "darm",
                  "niere", "niere links", "niere rechts", "nebenniere", "galle",
                  "bladder", "bladder/biliary", "darm", "darmgas", "gas", "ascoites", "aszites"},
    "pelvis":    {"becken", "pelvis", "harnblase", "uterus", "ovarium", "prostata",
                  "rektum", "sigmoideum"},
    "extremities": {"extremität", "extremitäten", "arm", "bein", "oberschenkel",
                    "unterschenkel", "fuß", "hand", "knie", "schulter", "hüfte",
                    "gelenk", "knochen", "weichteil", "soft_tissue"},
    "spine":     {"wirbelsäule", "ws", "bws", "hws", "lws", "spine", "spinal",
                  "bandscheibe", "myelon", "paravertebral"},
    "head":      {"schädel", "skull", "gehirn", "hirn", "brain", "cerebral", "cortex",
                  "ventrikel", "hals", "neck"},
    "cardiac":   {"herz", "aorta", "lungenarterie", "pa", "vci", "pulmonary",
                  "perikard", "myokard", "koronar", "lv", "rv", "la", "ra",
                  "mitralklappe", "aortenklappe", "trikuspidalklappe", "pulmonalklappe",
                  "valve", "valves"},
    "vascular":  {"gefäß", "vaskulär", "arterie", "vene", "thrombose", "embolie",
                  "aneurysma", "stenose", "okklusion"},
    "soft_tissue": {"weichteil", "muskel", "haut", "subkutan", "lymphknoten",
                    "lymphadenopathie", "lymph node"},
    "generic":   {"unauffällig", "regelrecht", "normalbefund", "unauffälliger befund",
                 "kein nachweis", "kein hinweis"},
}

# Flat set for O(1) lookup across all categories
_ALL_CANONICAL_TERMS: set[str] = set()
for terms in _CANONICAL_ANATOMY.values():
    _ALL_CANONICAL_TERMS.update(t.lower() for t in terms)


def _is_canonical(term: str, category: str) -> bool:
    """Check if a term is canonical for a given category or generic."""
    t = term.lower().strip()
    if t in _ALL_CANONICAL_TERMS:
        return True
    if category in _CANONICAL_ANATOMY:
        return t in {x.lower() for x in _CANONICAL_ANATOMY[category]}
    return False


def validate_canonical_vocabulary(
    structured_json: dict | None,
    category: str = "",
) -> dict:
    """
    Validate that all region/finding strings come from known anatomical vocabulary.

    Returns:
        {
            "valid":           bool,
            "non_canonical":   list[dict],   # [{term, field, suggestion}]
            "unknown_terms":   list[str],     # flat list of unknown terms
            "canonical_ratio": float,         # known / total terms
        }
    """
    result = {
        "valid": True,
        "non_canonical": [],
        "unknown_terms": [],
        "canonical_ratio": 1.0,
    }

    if structured_json is None:
        return {**result, "valid": False}

    fields_to_check = [
        ("visible_regions",          "visible_regions"),
        ("partial_regions",          "partial_regions"),
        ("uncertain_findings",       "uncertain_findings"),
        ("visible_findings",         "visible_findings"),
    ]

    total = 0
    unknown = []

    for field, label in fields_to_check:
        items = structured_json.get(field, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str) or not item.strip():
                continue
            total += 1
            if not _is_canonical(item, category):
                unknown.append(item.strip())
                result["non_canonical"].append({
                    "term":       item.strip(),
                    "field":      field,
                    "suggestion": "Bitte medizinisch korrekten anatomischen Begriff verwenden",
                })

    if unknown:
        result["valid"] = False
    result["unknown_terms"] = unknown
    result["canonical_ratio"] = 0.0 if total == 0 else 1.0 - len(unknown) / total

    return result


# ═══════════════════════════════════════════════════════════════
# JSON vs NARRATIVE CONSISTENCY VALIDATION
# Cross-references the <<<JSON>>> block against the stripped narrative.
# Flags when findings appear in narrative but NOT in JSON's visible list,
# or when hidden regions are mentioned in narrative.
# ═══════════════════════════════════════════════════════════════

_HIDDEN_REGION_EXTRAS: dict[str, list[str]] = {
    "mediastinum":   ["mediastinale lymphadenopathie", "vergrößerte lymphknoten mediastinum"],
    "brain":         ["intrazerebrale blutung", "hirnblutung", "ischämie", "infarkt"],
    "liver":         ["lebermetastase", "hepatische läsion", "lebertumor"],
    "kidneys":       ["nierentumor", "nierenkarzinom"],
    "heart":         ["myokardinfarkt", "koronare herzkrankheit"],
}


def _extract_medical_terms(text: str) -> set[str]:
    """Extract German medical terms from free text for comparison."""
    if not text:
        return set()
    t = text.lower()
    return {term.lower() for term in _MEDICAL_VOTE_TERMS if term.lower() in t}


def _check_narrative_mentions_hidden_regions(
    narrative: str,
    hidden_regions: list[str],
) -> list[str]:
    """Check if narrative describes findings in regions classified as hidden."""
    conflicts = []
    if not hidden_regions:
        return conflicts
    narrative_lower = narrative.lower()
    for region in hidden_regions:
        for term in _HIDDEN_REGION_EXTRAS.get(region, []):
            if term in narrative_lower:
                conflicts.append(
                    f"Region '{region}' als unsichtbar markiert, aber '{term}' im Befund erwähnt"
                )
    return conflicts


def check_json_narrative_consistency(
    structured_json: dict | None,
    narrative: str,
    visibility_data: dict | None = None,
) -> dict:
    """
    Cross-validate JSON findings against the narrative text.

    Returns:
        {
            "consistent":              bool,
            "narrative_only_findings":  list[str],
            "hidden_region_conflicts":  list[str],
            "json_empty_narrative_full": bool,
            "warnings":                 list[str],
        }
    """
    result = {
        "consistent":               True,
        "narrative_only_findings":  [],
        "hidden_region_conflicts":  [],
        "json_empty_narrative_full": False,
        "warnings":                 [],
    }
    if not narrative:
        return result

    narrative_terms = _extract_medical_terms(narrative)
    if not narrative_terms:
        return result

    if structured_json is None:
        danger_terms = {"embolie", "karzinom", "metastase", "infarkt", "blutung", "tumor"}
        found = narrative_terms & danger_terms
        if found:
            result["consistent"] = False
            result["warnings"].append(
                f"Kein strukturiertes JSON vorhanden, aber kritische Begriffe im Text: {', '.join(found)}"
            )
        result["json_empty_narrative_full"] = True
        return result

    json_findings = set()
    for field in ["visible_findings", "uncertain_findings"]:
        for item in structured_json.get(field, []):
            if isinstance(item, str) and item.strip():
                json_findings.add(item.lower())

    narrative_has_content = len(narrative_terms) >= 3
    json_is_empty = all(
        len(structured_json.get(f, [])) == 0
        for f in ["visible_findings", "uncertain_findings", "visible_regions"]
    )
    if json_is_empty and narrative_has_content:
        result["json_empty_narrative_full"] = True
        result["warnings"].append(
            "Modell hat JSON nicht ausgefüllt, aber Narrative enthält Befunde"
        )

    if json_findings:
        uncovered = sorted(narrative_terms - json_findings)
        if uncovered:
            result["narrative_only_findings"] = uncovered
            if len(uncovered) >= 2:
                result["consistent"] = False
                result["warnings"].append(
                    f"Befunde im Text nicht in JSON: {', '.join(uncovered)}"
                )

    hidden = []
    if visibility_data and isinstance(visibility_data, dict):
        hidden = visibility_data.get("hidden", [])
    if hidden:
        conflicts = _check_narrative_mentions_hidden_regions(narrative, hidden)
        if conflicts:
            result["hidden_region_conflicts"] = conflicts
            result["consistent"] = False
            result["warnings"].extend(conflicts)

    return result


# ═══════════════════════════════════════════════════════════════
# STRICT MINIMAL-FACTUAL CLINICAL SAFETY MODE
# Activates when: high disagreement OR poor visibility OR high risk score
#                OR multiple validator violations OR low confidence
#
# When triggered:
# - disable differential diagnoses section
# - disable speculative interpretation section
# - output findings + limitations only
# - inject strong human review notice
# ═══════════════════════════════════════════════════════════════

_STRICT_CSM_SECTIONS_TO_KEEP = {"befund", "technik", "befundbeschreibung", "observation"}
_STRICT_CSM_SECTIONS_TO_STRIP = {
    "differentialdiagnose", "differenzialdiagnose", "differential",
    "interpretation", "einschätzung", "beurteilung", "prognose",
    "empfehlung", "therapie", "follow-up", "follow up",
}

_STRICT_CSM_BANNER = (
    "\n> **KLINISCHER SICHERHEITSMODUS - REDUZIERTER BEFUND**\n"
    "> \n"
    "> Aufgrund erhoehter Unsicherheitssignale werden nur direkt beobachtbare "
    "Befunde angezeigt.\n"
    "> Differentialdiagnosen, spekulative Interpretationen und Empfehlungen "
    "wurden deaktiviert.\n"
    "> \n"
    "> _Dieser Bericht ersetzt KEINE aerztliche Beurteilung._\n"
    "> _Aerztliche Ueberpruefung ist zwingend erforderlich._\n\n"
)


def should_trigger_strict_csm(
    voting_result: dict | None,
    visibility_data: dict | None,
    risk_result: dict | None,
    violations: list[str],
    confidence_float: float,
) -> tuple[bool, str]:
    """
    Determine whether to activate strict minimal-factual CSM.

    Triggers when ANY of:
    1. High disagreement (voting disagreement detected)
    2. Poor visibility (image_quality == "poor") OR >=2 hidden regions
    3. High risk score (level in {critical_review_required, dangerous})
    4. Multiple validator violations (>= 2)
    5. Low confidence (< 0.60)

    Returns (activate: bool, reason: str).
    """
    reasons: list[str] = []

    if voting_result and voting_result.get("disagreement"):
        reasons.append(
            f"Modelldisagreement (agreement={voting_result['agreement_score']:.2f})"
        )

    iq = (visibility_data or {}).get("image_quality", "unknown")
    if iq == "poor":
        reasons.append("Bildqualität: SCHLECHT")
    n_hidden = len((visibility_data or {}).get("hidden", []))
    if n_hidden >= 2:
        reasons.append(f"{n_hidden} Regionen nicht sichtbar")

    level = (risk_result or {}).get("level", "low_risk")
    if level in ("critical_review_required", "dangerous"):
        reasons.append(f"Risikostufe: {level.upper()}")

    if len(violations or []) >= 2:
        reasons.append(f"{len(violations)} Modalitätsverletzungen")

    if confidence_float < 0.60:
        reasons.append(f"Niedrige KI-Konfidenz (conf={confidence_float:.2f})")

    if not reasons:
        return False, ""
    return True, f"CSM-Strict aktiviert: {', '.join(reasons)}"


def apply_strict_clinical_safety_mode(
    text: str,
    additional_notice: str = "",
) -> tuple[str, bool]:
    """
    Strict minimal-factual mode: keep only findings + limitations.
    Strips: differentials, interpretation, prognosis, recommendations, etc.

    Returns (stripped_text, was_modified: bool).
    """
    if not text:
        return text, False
    original = text
    lines = text.split("\n")
    output: list[str] = []
    skip_until_next_h2 = False
    skip_remaining = False
    banner_prepended = False

    for line in lines:
        stripped = line.strip()
        is_h2 = stripped.lower().startswith("## ")

        if is_h2:
            h_text = stripped.lower().lstrip("#").strip()
            is_keep = any(s in h_text for s in _STRICT_CSM_SECTIONS_TO_KEEP)
            is_strip = any(s in h_text for s in _STRICT_CSM_SECTIONS_TO_STRIP)
            if is_strip:
                skip_until_next_h2 = True
                skip_remaining = False
            elif is_keep:
                skip_until_next_h2 = False
                skip_remaining = False
            else:
                skip_remaining = True

        if skip_until_next_h2:
            continue
        if skip_remaining:
            continue

        if output and not banner_prepended:
            output.insert(0, _STRICT_CSM_BANNER)
            banner_prepended = True
        output.append(line)

    if output and not banner_prepended:
        output.insert(0, _STRICT_CSM_BANNER)
        banner_prepended = True

    result = "\n".join(output).strip()
    if additional_notice and additional_notice not in result:
        result += f"\n\n---\n{additional_notice}"

    return result, result != original


def build_strict_csm_log_entry(
    activated: bool,
    reason: str,
    was_modified: bool,
    original_length: int,
    final_length: int,
) -> dict:
    """Build a structured log entry for strict CSM activation."""
    return {
        "step":          "strict_clinical_safety_mode",
        "activated":     activated,
        "reason":        reason,
        "was_modified":  was_modified,
        "chars_before":  original_length,
        "chars_after":   final_length,
        "chars_removed": original_length - final_length,
    }


# ═══════════════════════════════════════════════════════════════
# MASTER PROMPT
# ═══════════════════════════════════════════════════════════════

MASTER_PROMPT = """
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
# VISIBILITY DETECTION - Step 2 of the pipeline
# Quick pre-analysis call to determine what the image actually shows.
# ═══════════════════════════════════════════════════════════════

VISIBILITY_SYSTEM = (
    "You are a medical image visibility analyzer. "
    "You output ONLY valid JSON with no markdown, no explanation."
)

VISIBILITY_USER = (
    "Examine this medical image carefully.\n"
    "Identify which anatomical regions are clearly visible, partially visible, or not visible at all.\n\n"
    "Output ONLY JSON in this exact format (no other text):\n"
    "{\"visible\": [\"region1\", \"region2\"], \"partial\": [\"region3\"], \"hidden\": [\"region4\"], "
    "\"image_quality\": \"good|limited|poor\"}\n\n"
    "Use these anatomical terms:\n"
    + ", ".join(_ANATOMY_TERMS) + "\n\n"
    "If image quality is too poor to assess:\n"
    "{\"visible\": [], \"partial\": [], \"hidden\": [], \"image_quality\": \"poor\"}"
)

# ═══════════════════════════════════════════════════════════════
# SUBTYPE PROMPTS - modality-specific rules appended to MASTER
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
- Pathologische Werte markieren (erhoeht / vermindert mit Referenzbereich).
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
# MASTER PROMPT
# Quick pre-analysis call to determine what the image actually shows.
# ═══════════════════════════════════════════════════════════════

VISIBILITY_SYSTEM = (
    "You are a medical image visibility analyzer. "
    "You output ONLY valid JSON with no markdown, no explanation."
)

VISIBILITY_USER = (
    "Examine this medical image carefully.\n"
    "Identify which anatomical regions are clearly visible, partially visible, or not visible at all.\n\n"
    "Output ONLY JSON in this exact format (no other text):\n"
    "{\"visible\": [\"region1\", \"region2\"], \"partial\": [\"region3\"], \"hidden\": [\"region4\"], "
    "\"image_quality\": \"good|limited|poor\"}\n\n"
    "Use these anatomical terms:\n"
    + ", ".join(_ANATOMY_TERMS) + "\n\n"
    "If image quality is too poor to assess:\n"
    "{\"visible\": [], \"partial\": [], \"hidden\": [], \"image_quality\": \"poor\"}"
)

# ═══════════════════════════════════════════════════════════════
# STRUCTURED JSON FORMAT - appended to system prompt
# Forces model to commit to what it saw before writing narrative.
# This is the core anti-hallucination mechanism for Step 4.
# ═══════════════════════════════════════════════════════════════

STRUCTURED_JSON_SUFFIX = """

=== PFLICHTFORMAT - STRIKTE REIHENFOLGE ===

SCHRITT 1: Gib zuerst einen JSON-Block zwischen <<<JSON>>> und <<<END_JSON>>> aus:
<<<JSON>>>
{
  "visible_regions": ["sichtbare anatomische Region 1"],
  "partial_regions": ["nur teilweise sichtbare Region"],
  "visible_findings": ["Befund 1 in konservativem Stil", "Befund 2"],
  "uncertain_findings": ["Möglicher Befund - Bestätigung erforderlich"],
  "limitations": ["Limitation 1", "Limitation 2"],
  "forbidden_sections_skipped": ["Was übersprungen wurde und warum"]
}
<<<END_JSON>>>

SCHRITT 2: Danach der deutsche Radiologiebericht in Abschnitten:
## 1. Technik
## 2. Befund
## 3. Beurteilung
## 4. Limitationen

PFLICHTREGELN FÜR BEFUNDSPRACHE - KEINE AUSNAHMEN:
- VERBOTEN:  "Pneumonie mit 85% Wahrscheinlichkeit"
  PFLICHT:   "Unspezifische Verschattung im rechten Unterfeld - Pneumonie nicht ausgeschlossen"
- VERBOTEN:  "Metastase erkennbar" / "Malignom bestätigt"
  PFLICHT:   "Rundliche Dichtezunahme - Dignität nicht sicher beurteilbar"
- VERBOTEN:  "Lungenembolie" (auf konventionellem Röntgen)
  PFLICHT:   "Emboliediagnostik erfordert CT-Angiographie - röntgenologisch nicht beurteilbar"
- VERBOTEN:  "Kardiomegalie" (auf Abdominalröntgen)
  PFLICHT:   "Herzschatten nicht vollständig beurteilbar"
- PFLICHT:   "vereinbar mit", "nicht ausgeschlossen", "fraglich", "möglicherweise" bei Interpretationen
"""

# ═══════════════════════════════════════════════════════════════
# MODALITY TERM BLACKLIST - Step 5 hard validation
# Derived from findings_vocabulary.MODALITY_CONSTRAINTS so there is
# exactly one place to add/remove forbidden terms.
# Kept as a public name for backward compatibility with tests and imports.
# ═══════════════════════════════════════════════════════════════

MODALITY_TERM_BLACKLIST: dict[str, list[str]] = {
    k: v.get("forbidden_terms", []) for k, v in MODALITY_CONSTRAINTS.items()
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
            "\n- Kommentiere NICHTS unter 'forbidden_assessment' - diese Regionen sind nicht sichtbar."
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
    Proportional safety gate: language aggressiveness ∝ (1 - confidence).

    Thresholds (from model-count proxy: 1→0.55, 2→0.72, 3→0.85):

      >= 0.85  FULL    - no modifications (3 models, high agreement)
      0.72-0.84 MEDIUM  - strip explicit probability percentages only
      0.60-0.71 LOW     - strip all percentages + soft malignancy warnings
      < 0.60   MINIMAL - disable differentials + hard-flag malignancy + notice
    """
    if confidence >= 0.85:
        return text

    # MEDIUM (0.72+): Remove explicit "(80%)" or "80%" in differential context
    if confidence < 0.85:
        # Remove parenthesised percentages like "(85%)" or "(>80%)"
        text = _re.sub(r'\(\s*>?\d+\s*%\s*\)', '', text)

    # LOW (< 0.72): Remove ALL probability percentages
    if confidence < 0.72:
        text = _re.sub(r'(?<!\w)\d+\s*%(?!\w)', '', text)
        # Soft warning on high-risk terms (bracket, don't remove)
        _SOFT_RISK = ["Karzinom", "Malignom", "Metastase", "Neoplasie"]
        for term in _SOFT_RISK:
            text = _re.sub(
                rf'\b({_re.escape(term)}\w*)\b',
                r'[\1 - eingeschränkte Konfidenz]',
                text, flags=_re.IGNORECASE,
            )

    # MINIMAL (< 0.60): disable differentials + hard-flag + notice
    if confidence < 0.60:
        text = _re.sub(
            r'(##\s*(?:Differential(?:diagnos\w*)|Differenzialdiagnos\w*))(.*?)(?=\n##|\Z)',
            (
                r'\1\n_Deaktiviert - Konfidenz zu niedrig für Differentialdiagnosen. '
                r'Klinische Korrelation zwingend erforderlich._\n'
            ),
            text, flags=_re.DOTALL | _re.IGNORECASE,
        )
        # Hard-flag remaining high-risk terms
        _HARD_RISK = ["maligne", "maligner", "malignes"]
        for term in _HARD_RISK:
            text = _re.sub(
                rf'\b{_re.escape(term)}\b',
                f'[{term} - Konfidenz unzureichend]',
                text, flags=_re.IGNORECASE,
            )
        text += (
            "\n\n---\n"
            "ℹ️ **Konfidenz-Hinweis (MINIMAL):** Nur 1 Modell geantwortet. "
            "Differentialdiagnosen deaktiviert. Prozentwerte entfernt. "
            "Ärztliche Überprüfung zwingend erforderlich."
        )

    return text


def validate_modality_output(text: str, category: str) -> tuple[str, list[str]]:
    """
    Hard validation - detect forbidden modality-specific terms in the output.

    Returns (original_text, list_of_violations).
    Does NOT modify the text - violations are reported as warnings to the caller.
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


# ═══════════════════════════════════════════════════════════════
# FEATURE 1 - Multi-model Voting
# Compare findings across models; flag high disagreement.
# ═══════════════════════════════════════════════════════════════

# _MEDICAL_VOTE_TERMS imported from findings_vocabulary as _MEDICAL_VOTE_TERMS


def compute_model_agreement(analyses: list[str]) -> dict:
    """
    Term-overlap voting between model outputs.

    Extracts known medical terms from each analysis and measures
    how many appear in the majority of models.

    Returns:
        {
          "agreement_score": float 0-1  (1 = perfect agreement),
          "disagreement": bool,
          "models_compared": int,
          "disagreement_terms": list[str],
        }
    """
    valid = [a for a in analyses if a and len((a or "").strip()) > 80]
    if len(valid) < 2:
        return {
            "agreement_score": 1.0, "disagreement": False,
            "models_compared": len(valid), "disagreement_terms": [],
        }

    term_sets: list[set[str]] = []
    for text in valid:
        tl = text.lower()
        term_sets.append({t for t in _MEDICAL_VOTE_TERMS if t.lower() in tl})

    all_terms = set().union(*term_sets)
    if not all_terms:
        return {
            "agreement_score": 1.0, "disagreement": False,
            "models_compared": len(valid), "disagreement_terms": [],
        }

    majority_threshold = len(valid) / 2
    majority_count = sum(
        1 for t in all_terms
        if sum(1 for s in term_sets if t in s) > majority_threshold
    )
    agreement_score = majority_count / len(all_terms)

    disagreement_terms = [
        t for t in all_terms
        if sum(1 for s in term_sets if t in s) == 1
    ][:6]

    return {
        "agreement_score": round(agreement_score, 2),
        "disagreement": agreement_score < 0.40,
        "models_compared": len(valid),
        "disagreement_terms": disagreement_terms,
    }


# ═══════════════════════════════════════════════════════════════
# FEATURE 2 helper - Merge LLM visibility with OpenCV segmentation
# ═══════════════════════════════════════════════════════════════

def merge_visibility_with_segmentation(
    llm_visibility: dict,
    seg_result: dict,
) -> dict:
    """
    Combine LLM visibility detection with OpenCV anatomical segmentation.

    Strategy:
    - visible:  LLM says visible (trusted source of truth)
    - partial:  LLM says partial OR seg says partial but LLM didn't confirm visible
    - hidden:   LLM says hidden AND seg didn't detect it confidently
    - quality:  worst of both estimates
    """
    llm_visible = set(llm_visibility.get("visible", []))
    llm_partial = set(llm_visibility.get("partial", []))
    llm_hidden  = set(llm_visibility.get("hidden",  []))
    seg_visible = set(seg_result.get("detected_regions", []))
    seg_partial = set(seg_result.get("partial_regions",  []))

    confirmed_visible = llm_visible
    confirmed_partial = llm_partial | (seg_partial - llm_visible)
    # Remove hidden if OpenCV confidently detected it (contradiction → downgrade to partial)
    confirmed_hidden  = llm_hidden - seg_visible
    contradicted      = llm_hidden & seg_visible
    if contradicted:
        confirmed_partial |= contradicted  # downgrade from hidden → partial

    confirmed_partial -= confirmed_visible

    _quality_order = {"poor": 0, "limited": 1, "good": 2, "unknown": 1}
    llm_q = llm_visibility.get("image_quality", "unknown")
    seg_q = seg_result.get("quality_estimate", "unknown")
    merged_quality = min(llm_q, seg_q, key=lambda q: _quality_order.get(q, 1))

    return {
        "visible":       sorted(confirmed_visible),
        "partial":       sorted(confirmed_partial),
        "hidden":        sorted(confirmed_hidden),
        "image_quality": merged_quality,
        "segmentation":  seg_result.get("image_stats", {}),
        "contradictions": sorted(contradicted),
    }


# ═══════════════════════════════════════════════════════════════
# FEATURE 3 - Risk Classifier
# Aggregates all pipeline signals → safe / uncertain / dangerous
# Controls report shortening and limitation text injection.
# ═══════════════════════════════════════════════════════════════

def classify_risk(
    violations: list[str],
    visibility_data: dict,
    confidence_float: float,
    structured_json: dict | None,
    voting_result: dict | None,
) -> dict:
    """
    Rule-based risk classifier.  No ML needed - deterministic.

    Returns:
        {
          "level":   "safe" | "uncertain" | "dangerous",
          "score":   int 0-100,
          "reasons": list[str],
        }
    """
    score = 0
    reasons: list[str] = []

    # - Modality violations
    if violations:
        score += len(violations) * 15
        reasons.append(f"{len(violations)} Modalitätsverletzung(en) erkannt")

    # - Confidence (model count proxy)
    if confidence_float < 0.60:
        score += 35
        reasons.append("Niedrige Konfidenz - nur 1 Modell geantwortet")
    elif confidence_float < 0.75:
        score += 15
        reasons.append("Moderate Konfidenz - 2 Modelle geantwortet")

    # - Partial / hidden visibility
    n_partial = len(visibility_data.get("partial", []))
    n_hidden  = len(visibility_data.get("hidden",  []))
    if n_partial >= 3:
        score += 20
        reasons.append(f"{n_partial} Regionen nur partiell sichtbar")
    if n_hidden >= 2:
        score += 10
        reasons.append(f"{n_hidden} Regionen nicht sichtbar")

    # - Image quality
    iq = visibility_data.get("image_quality", "unknown")
    if iq == "poor":
        score += 25
        reasons.append("Bildqualität: SCHLECHT")
    elif iq == "limited":
        score += 10
        reasons.append("Bildqualität: EINGESCHRÄNKT")

    # - JSON extraction failure
    if structured_json is None:
        score += 10
        reasons.append("Strukturiertes JSON nicht extrahierbar")
    else:
        # High-risk terms in uncertain_findings → more dangerous
        _risky = ["Metastase", "Karzinom", "Malignom", "Embolie", "Infarkt"]
        uncertain_blob = " ".join(structured_json.get("uncertain_findings", []))
        for term in _risky:
            if term.lower() in uncertain_blob.lower():
                score += 20
                reasons.append(f"Hochrisikoterm in unsicheren Befunden: {term}")
                break

    # - Model disagreement (Feature 1 result)
    if voting_result and voting_result.get("disagreement"):
        score += 25
        dt = voting_result.get("disagreement_terms", [])
        reasons.append(
            "Modelldisagreement erkannt"
            + (f" (strittige Befunde: {', '.join(dt)})" if dt else "")
        )

    # 4-level severity (replaces 3-level)
    if score >= 71:
        level = "dangerous"
    elif score >= 46:
        level = "critical_review_required"
    elif score >= 21:
        level = "moderate_risk"
    else:
        level = "low_risk"

    return {"level": level, "score": min(score, 100), "reasons": reasons}


# ═══════════════════════════════════════════════════════════════
# FEATURE 4 - Clinical Language Normalization
# Whitelist-driven: replaces overconfident phrases
# at low/medium confidence. Always removes absolutely forbidden terms.
# ═══════════════════════════════════════════════════════════════

# _LANGUAGE_GATE and _FORBIDDEN_ALWAYS imported from findings_vocabulary


def normalize_clinical_language(text: str, confidence: float) -> tuple[str, list[str]]:
    """
    Replace overconfident clinical phrases with conservative alternatives.

    Returns (modified_text, list_of_replacements_made).
    """
    changes: list[str] = []

    # Always-forbidden phrases
    for phrase in _FORBIDDEN_ALWAYS:
        if phrase.lower() in text.lower():
            text = _re.sub(_re.escape(phrase), "[nicht zulässige Aussage]", text, flags=_re.IGNORECASE)
            changes.append(f"ENTFERNT (immer verboten): '{phrase}'")

    # Confidence-gated replacements
    for forbidden, (replacement, min_conf) in _LANGUAGE_GATE.items():
        if confidence < min_conf and forbidden.lower() in text.lower():
            text = _re.sub(_re.escape(forbidden), replacement, text, flags=_re.IGNORECASE)
            changes.append(f"'{forbidden}' → '{replacement}'")

    return text, changes


# ═══════════════════════════════════════════════════════════════
# FEATURE 5 - Human Review Mode
# Triggered by any combination of: low confidence, many violations,
# high partial visibility, risk level dangerous/uncertain, disagreement.
# Outputs a prominent banner prepended to the report.
# ═══════════════════════════════════════════════════════════════

def should_trigger_human_review(
    risk_level: str,
    confidence_float: float,
    violations: list[str],
    visibility_data: dict,
    voting_result: dict | None,
) -> tuple[bool, str]:
    """
    Determine whether to show the human-review banner.

    Returns (show_banner: bool, banner_text: str).
    """
    triggers: list[str] = []

    if confidence_float < 0.60:
        triggers.append("niedrige KI-Konfidenz (1 Modell)")
    if len(violations) >= 2:
        triggers.append(f"{len(violations)} Sicherheitsverletzungen")
    if len(visibility_data.get("partial", [])) >= 3:
        triggers.append("eingeschränkte Sichtbarkeit in ≥3 Regionen")
    if risk_level in ("dangerous", "critical_review_required", "moderate_risk"):
        triggers.append(f"Risikostufe: {risk_level.replace('_', ' ').upper()}")
    if voting_result and voting_result.get("disagreement"):
        triggers.append("KI-Modelle nicht einig")
    iq = visibility_data.get("image_quality", "unknown")
    if iq in ("poor", "limited"):
        triggers.append(f"Bildqualität: {iq.upper()}")

    if not triggers:
        return False, ""

    banner = (
        "\n> 🔴 **ÄRZTLICHE ÜBERPRÜFUNG EMPFOHLEN**\n"
        "> \n"
        "> **KI-Analyse mit eingeschränkter diagnostischer Sicherheit.**\n"
        "> \n"
        f"> Gründe: {', '.join(triggers)}.\n"
        "> \n"
        "> _Diese Analyse ersetzt KEINE ärztliche Beurteilung und darf nicht als "
        "alleinige Entscheidungsgrundlage verwendet werden._\n\n"
    )
    return True, banner


# ═══════════════════════════════════════════════════════════════
# FEATURE 6 - Clinical Safety Mode
# Automatically activates minimal factual mode when multiple
# safety signals converge. Strips interpretation / differentials
# from the already-generated report so the model outputs
# only verifiable observations.
# ═══════════════════════════════════════════════════════════════

# Sections that are removed in clinical safety mode
_CSM_SECTIONS_TO_STRIP = [
    r"Differential(?:diagnos\w*)",
    r"Differenzialdiagnos\w*",
    r"Interpretation",
    r"Prognose",
    r"Einschätzung",
]

_CSM_BANNER = (
    "\n> 🛡️ **KLINISCHER SICHERHEITSMODUS AKTIV**\n"
    "> \n"
    "> Zu viele Unsicherheitssignale erkannt. "
    "Nur direkt beobachtbare Befunde werden angezeigt.\n"
    "> Differentialdiagnosen und Interpretationen wurden automatisch deaktiviert.\n"
    "> \n"
    "> _Ärztliche Beurteilung zwingend erforderlich._\n\n"
)


def should_use_clinical_safety_mode(
    risk_result: dict,
    visibility_data: dict,
    voting_result: dict | None,
) -> tuple[bool, str]:
    """
    Decide whether to activate Clinical Safety Mode.

    Triggers when ≥ 3 independent safety signals are active.
    Returns (activate: bool, reason: str).
    """
    signals: list[str] = []

    # Signal 1+2: high risk level (worth 2 points - structural issues)
    if risk_result.get("level") in ("critical_review_required", "dangerous"):
        signals.append("Risikostufe CRITICAL/DANGEROUS")
        signals.append("Risikostufe CRITICAL/DANGEROUS (2)")  # weight 2

    # Signal 3: poor image quality
    iq = visibility_data.get("image_quality", "unknown")
    if iq == "poor":
        signals.append("Bildqualität SCHLECHT")

    # Signal 4: model disagreement
    if voting_result and voting_result.get("disagreement"):
        signals.append("Modelldisagreement erkannt")

    # Signal 5: many hidden regions
    n_hidden = len(visibility_data.get("hidden", []))
    if n_hidden >= 2:
        signals.append(f"{n_hidden} Regionen nicht sichtbar")

    # Signal 6: segmentation produced no stats (image decode problem)
    if not visibility_data.get("segmentation"):
        signals.append("Segmentierung fehlgeschlagen")

    # Signal 7: many partial regions
    n_partial = len(visibility_data.get("partial", []))
    if n_partial >= 4:
        signals.append(f"{n_partial} Regionen nur partiell sichtbar")

    activated = len(signals) >= 3
    reason = f"Clinical Safety Mode: {len(signals)} Signale aktiv ({'; '.join(signals[:4])})"
    return activated, reason


def apply_clinical_safety_mode(text: str) -> tuple[str, bool]:
    """
    Strip interpretive sections from the report, leaving only direct findings.

    Returns (stripped_text, was_modified: bool).
    """
    original = text
    for section_pattern in _CSM_SECTIONS_TO_STRIP:
        text = _re.sub(
            rf'##\s+{section_pattern}(.*?)(?=\n##|\Z)',
            '_Deaktiviert - Klinischer Sicherheitsmodus aktiv. Nur gesicherte Befunde werden angezeigt._\n',
            text,
            flags=_re.DOTALL | _re.IGNORECASE,
        )
    was_modified = text != original
    return text, was_modified


# ═══════════════════════════════════════════════════════════════
# FEATURE 7 - Pipeline Explainability Log
# Structured audit trail: WHY each safety action was taken.
# Stored per-analysis for debugging and metrics.
# ═══════════════════════════════════════════════════════════════

def build_pipeline_explainability_log(
    confidence: float,
    violations: list[str],
    lang_changes: list[str],
    risk_result: dict,
    voting_result: dict | None,
    visibility_data: dict,
    clinical_safety_mode: bool = False,
) -> list[dict]:
    """
    Build a structured log of every safety action taken in the pipeline.

    Each entry has: step, reason, action, detail.
    """
    log: list[dict] = []

    # - Confidence gate actions
    if confidence >= 0.85:
        log.append({
            "step": "confidence_gate",
            "reason": f"confidence={confidence:.2f} >= 0.85",
            "action": "none",
            "detail": "High confidence - no modifications",
        })
    elif confidence >= 0.72:
        log.append({
            "step": "confidence_gate",
            "reason": f"confidence={confidence:.2f} in [0.72, 0.85)",
            "action": "removed_parenthesized_percentages",
            "detail": "Stripped (85%) style inline probability estimates",
        })
    elif confidence >= 0.60:
        log.append({
            "step": "confidence_gate",
            "reason": f"confidence={confidence:.2f} in [0.60, 0.72)",
            "action": "removed_all_percentages + softened_malignancy_terms",
            "detail": "All % removed; high-risk terms bracketed with confidence warning",
        })
    else:
        log.append({
            "step": "confidence_gate",
            "reason": f"confidence={confidence:.2f} < 0.60",
            "action": "disabled_differentials + hard_flagged_malignancy + added_notice",
            "detail": "Only 1 model responded - differentials blocked, strong warning appended",
        })

    # - Modality violations
    if violations:
        for v in violations:
            log.append({
                "step": "modality_validator",
                "reason": "Forbidden term detected for this modality",
                "action": "flagged_violation",
                "detail": v,
            })
    else:
        log.append({
            "step": "modality_validator",
            "reason": "No forbidden terms found",
            "action": "none",
            "detail": "Output clean for modality",
        })

    # - Language normalization
    if lang_changes:
        for change in lang_changes:
            log.append({
                "step": "language_normalization",
                "reason": f"confidence={confidence:.2f} below phrase threshold",
                "action": "replaced_overconfident_phrase",
                "detail": change,
            })

    # - Risk classification
    log.append({
        "step": "risk_classifier",
        "reason": " | ".join(risk_result.get("reasons", [])) or "No risk factors",
        "action": f"level={risk_result['level']} score={risk_result['score']}",
        "detail": f"Score breakdown: {risk_result['score']}/100 → {risk_result['level']}",
    })

    # - Model voting
    if voting_result:
        if voting_result.get("disagreement"):
            dt = voting_result.get("disagreement_terms", [])
            log.append({
                "step": "model_voting",
                "reason": f"agreement_score={voting_result['agreement_score']} < 0.40",
                "action": "flagged_disagreement",
                "detail": f"Disputed terms: {', '.join(dt)}" if dt else "High term divergence",
            })
        else:
            log.append({
                "step": "model_voting",
                "reason": f"agreement_score={voting_result['agreement_score']} >= 0.40",
                "action": "none",
                "detail": f"{voting_result.get('models_compared', 0)} models agreed",
            })

    # - Visibility / image quality
    iq = visibility_data.get("image_quality", "unknown")
    if iq in ("poor", "limited"):
        log.append({
            "step": "visibility_check",
            "reason": f"image_quality={iq}",
            "action": "added_quality_notice",
            "detail": (
                f"hidden={visibility_data.get('hidden', [])}, "
                f"partial={visibility_data.get('partial', [])}"
            ),
        })

    # - Clinical safety mode
    if clinical_safety_mode:
        log.append({
            "step": "clinical_safety_mode",
            "reason": "≥3 safety signals converged",
            "action": "stripped_interpretation_and_differentials",
            "detail": "Report limited to direct findings only",
        })

    return log
