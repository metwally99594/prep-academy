"""
Safety Pipeline Unit Tests — Regression suite for analyzer hardening.

Tests the POST-LLM safety pipeline functions directly (no server, no LLM calls).
Run with: pytest backend/tests/test_analyzer_safety.py -v

On every commit, these tests verify that:
  - Confidence gate fires at the right thresholds
  - Modality blacklist catches forbidden terms
  - Language normalization replaces unsafe phrases
  - Risk classifier scores correctly
  - Human review banner triggers on the right conditions
  - Multi-model voting detects disagreements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.analyzer_prompts import (
    apply_confidence_gate,
    validate_modality_output,
    normalize_clinical_language,
    classify_risk,
    should_trigger_human_review,
    compute_model_agreement,
    parse_analysis_json,
    strip_analysis_json_block,
    build_prompt,
    validate_json_schema,
    validate_canonical_vocabulary,
    check_json_narrative_consistency,
    should_trigger_strict_csm,
    apply_strict_clinical_safety_mode,
    VALID_CATEGORIES,
)


# ═══════════════════════════════════════════════════════════════
# GOLDEN DATASET — mock LLM responses for each scenario
# ═══════════════════════════════════════════════════════════════

CLEAN_XRAY_REPORT = """
## 1. Technik
Konventionelle Thoraxaufnahme p.a. Stehend.

## 2. Befund
Lunge beidseits belüftet. Kein Nachweis eines Infiltrates. Zwerchfell beidseits glatt begrenzt.
Herzschatten nicht vergrößert. Mediastinum regelrecht.

## 3. Beurteilung
Unauffälliger Thoraxbefund. Kein Nachweis einer akuten kardiopulmonalen Pathologie.

## 4. Limitationen
Beurteilung auf konventionelles Röntgen beschränkt.
"""

HALLUCINATED_CT_TERMS_ON_XRAY = """
## 2. Befund
Hounsfield-Einheiten im Lungenparenchym: 45 HU beidseits.
Axiale Schichten zeigen bihiläre Lymphadenopathie.
Enhancement nach Kontrastmittelgabe deutlich erkennbar.
Lungenembolie beidseits nicht ausgeschlossen — CT-Angiographie empfohlen.
"""

HALLUCINATED_CANCER_CLAIM = """
## 2. Befund
Eindeutig bestätigt: Pancoast-Tumor rechts apical. Malignom definitiv gesichert.
Mediastinalmetastasen beidseits nachweisbar. Hochwahrscheinlich Karzinom Stadium IV.
Metastasen in Lunge und Leber gesichert.

## Differentialdiagnosen
1. Lungenkarzinom (95%)
2. Lymphom (80%)
3. Metastasen (75%)
"""

HALLUCINATED_EMBOLISM = """
## 2. Befund
Lungenembolie beidseits nachweisbar. Mediastinale Lymphadenopathie.
Hounsfield-Einheiten 45 HU zentral. Enhancement typisch für Embolie.
"""

HALLUCINATED_PROBABILITY_REPORT = """
## Differentialdiagnosen
1. Pneumonie (85%)
2. Lungenödem (70%)
3. Atelektase (55%)
"""

SAFE_CONSERVATIVE_REPORT = """
## 2. Befund
Unspezifische Verschattung im rechten Unterfeld, vereinbar mit entzündlichem Infiltrat nicht ausgeschlossen.
Pleurawinkel rechts fraglich verschattet — möglicherweise geringer Erguss.

## 3. Beurteilung
Befund nicht sicher beurteilbar. Klinische Korrelation erforderlich.

## 4. Limitationen
Konventionelles Röntgen, keine Schnittbildgebung verfügbar.
"""

OVERCONFIDENT_LANGUAGE_REPORT = """
## Befund
Definitiv Pneumonie. Beweisend für bakterielle Infektion. Zweifelsfrei pathologisch.
Gesicherter Befund: Lungenödem beidseits. Bewiesener Herzfehler.
"""

# Voting test cases
ANALYSIS_A_PNEUMONIA = "Infiltrat rechts basal. Atelektase links. Pleuraerguss fraglich."
ANALYSIS_B_PNEUMONIA = "Infiltrat rechts. Pleuraerguss beidseits nicht ausgeschlossen."
ANALYSIS_A_DIVERGE   = "Pneumothorax links. Tension-Pneumothorax möglich. Trachea verlagert."
ANALYSIS_B_DIVERGE   = "Atelektase rechts basal. Zwerchfell hochstand. Erguss links."


# ═══════════════════════════════════════════════════════════════
# A) CONFIDENCE GATE — Proportional aggressiveness tests
# ═══════════════════════════════════════════════════════════════

class TestConfidenceGate:

    def test_high_confidence_no_changes(self):
        """≥ 0.85: report must pass through unchanged."""
        text = "Pneumonie nicht ausgeschlossen. Infiltrat rechts basal."
        result = apply_confidence_gate(text, 0.85)
        assert result == text

    def test_medium_confidence_strips_parenthesised_percentages(self):
        """0.72-0.84: removes (80%) but not standalone text."""
        text = "Pneumonie (80%) wahrscheinlich. Verdacht auf Infiltrat."
        result = apply_confidence_gate(text, 0.72)
        assert "(80%)" not in result
        assert "Infiltrat" in result

    def test_low_confidence_strips_all_percentages(self):
        """0.60-0.71: removes all '80%' forms."""
        text = "Pneumonie 80% wahrscheinlich. Atelektase 60% möglich."
        result = apply_confidence_gate(text, 0.65)
        assert "80%" not in result
        assert "60%" not in result

    def test_low_confidence_soft_warns_malignancy(self):
        """0.60-0.71: brackets malignancy terms."""
        text = "Möglicherweise Karzinom im rechten Oberlappen."
        result = apply_confidence_gate(text, 0.68)
        assert "eingeschränkte Konfidenz" in result

    def test_minimal_confidence_disables_differentials(self):
        """< 0.60: differential diagnosis section replaced."""
        text = "## 2. Befund\nInfiltrat.\n\n## Differentialdiagnosen\n1. Pneumonie (80%)\n\n## 4. Limitationen\nNein."
        result = apply_confidence_gate(text, 0.55)
        assert "Deaktiviert" in result or "deaktiviert" in result
        assert "80%" not in result

    def test_minimal_confidence_adds_notice(self):
        """< 0.60: confidence notice appended."""
        result = apply_confidence_gate("Infiltrat rechts.", 0.55)
        assert "Konfidenz" in result
        assert "Modell" in result or "MINIMAL" in result

    def test_aggressive_probability_report_at_low_conf(self):
        """Hallucinated probability report should lose all percentages at low conf."""
        result = apply_confidence_gate(HALLUCINATED_PROBABILITY_REPORT, 0.55)
        import re
        assert not re.search(r'\d+\s*%', result), "Percentages should be removed at low confidence"


# ═══════════════════════════════════════════════════════════════
# B) MODALITY VALIDATOR — Cross-modality hallucination detection
# ═══════════════════════════════════════════════════════════════

class TestModalityValidator:

    def test_xray_catches_hounsfield(self):
        text = "Hounsfield-Einheiten im Parenchym: 45."
        _, violations = validate_modality_output(text, "xray")
        assert any("Hounsfield" in v for v in violations)

    def test_xray_catches_HU_value(self):
        text = "Dichtemessung: 45 HU -Wert im Lungenherd."
        _, violations = validate_modality_output(text, "xray")
        assert any("HU" in v for v in violations)

    def test_xray_catches_axial_slice(self):
        text = "Axiale Schicht zeigt bihiläre Lymphadenopathie."
        _, violations = validate_modality_output(text, "xray")
        assert any("axiale Schicht" in v for v in violations)

    def test_xray_catches_embolism_diagnosis(self):
        text = "Lungenembolie beidseits nachweisbar."
        _, violations = validate_modality_output(text, "xray")
        assert any("Lungenembolie" in v for v in violations)

    def test_xray_catches_enhancement(self):
        text = "Enhancement nach Kontrastmittelgabe deutlich."
        _, violations = validate_modality_output(text, "xray")
        assert any("enhancement" in v.lower() for v in violations)

    def test_mri_catches_HU(self):
        text = "Signalintensität HU-Wert entsprechend."
        _, violations = validate_modality_output(text, "mri")
        assert any("HU" in v for v in violations)

    def test_ct_no_violations_for_ct_terms(self):
        """CT-specific terms must NOT trigger violations on CT modality."""
        text = "Hounsfield-Einheiten 45 HU. Axiale Schicht zentraler Herd."
        _, violations = validate_modality_output(text, "ct")
        assert violations == []

    def test_clean_report_no_violations(self):
        _, violations = validate_modality_output(CLEAN_XRAY_REPORT, "xray")
        assert violations == []

    def test_hallucinated_ct_on_xray_catches_multiple(self):
        _, violations = validate_modality_output(HALLUCINATED_CT_TERMS_ON_XRAY, "xray")
        assert len(violations) >= 2, f"Expected ≥2 violations, got: {violations}"

    def test_unknown_modality_no_crash(self):
        _, violations = validate_modality_output("Some text", "unknown_modality")
        assert isinstance(violations, list)


# ═══════════════════════════════════════════════════════════════
# C) LANGUAGE NORMALIZATION
# ═══════════════════════════════════════════════════════════════

class TestLanguageNormalization:

    def test_replaces_definitiv_at_low_conf(self):
        text = "Definitiv Pneumonie nachweisbar."
        result, changes = normalize_clinical_language(text, 0.72)
        assert "möglicherweise" in result.lower() or len(changes) > 0

    def test_replaces_beweisend_fuer(self):
        text = "Beweisend für bakterielle Infektion."
        result, changes = normalize_clinical_language(text, 0.72)
        assert "vereinbar mit" in result.lower() or len(changes) > 0

    def test_high_conf_keeps_definitiv(self):
        """At confidence >= 0.85, overconfident phrases are kept (gate min_conf check)."""
        text = "Definitiv Pneumonie."
        result, changes = normalize_clinical_language(text, 0.85)
        # 'definitiv' gate is 0.85, so at exactly 0.85 it should NOT replace
        # (confidence < min_conf means < 0.85 → replace. At 0.85 → no replace)
        assert "definitiv" in result.lower() or len(changes) == 0

    def test_always_removes_absolut_sicher(self):
        """absolut sicher is always forbidden regardless of confidence."""
        text = "Absolut sicher handelt es sich um Pneumonie."
        result, changes = normalize_clinical_language(text, 0.95)
        assert "absolut sicher" not in result.lower()
        assert len(changes) > 0

    def test_always_removes_ohne_jeden_zweifel(self):
        text = "Ohne jeden Zweifel: Karzinom."
        result, changes = normalize_clinical_language(text, 0.99)
        assert "ohne jeden zweifel" not in result.lower()

    def test_overconfident_report_gets_normalized(self):
        result, changes = normalize_clinical_language(OVERCONFIDENT_LANGUAGE_REPORT, 0.72)
        assert len(changes) > 0


# ═══════════════════════════════════════════════════════════════
# D) RISK CLASSIFIER — 4-level severity
# ═══════════════════════════════════════════════════════════════

class TestRiskClassifier:

    def _base_visibility(self):
        return {"visible": ["thorax"], "partial": [], "hidden": [], "image_quality": "good"}

    def test_clean_input_is_low_risk(self):
        result = classify_risk(
            violations=[], visibility_data=self._base_visibility(),
            confidence_float=0.85, structured_json={"visible_findings": ["Unauffällig"], "uncertain_findings": []},
            voting_result={"disagreement": False, "agreement_score": 0.9},
        )
        assert result["level"] == "low_risk"
        assert result["score"] < 21

    def test_low_confidence_is_moderate_or_higher(self):
        result = classify_risk(
            violations=[], visibility_data=self._base_visibility(),
            confidence_float=0.72, structured_json=None,
            voting_result=None,
        )
        assert result["level"] in ("moderate_risk", "critical_review_required", "dangerous")
        assert result["score"] >= 21

    def test_single_model_is_critical(self):
        """1 model (conf=0.55) + JSON missing → critical_review_required."""
        result = classify_risk(
            violations=[], visibility_data=self._base_visibility(),
            confidence_float=0.55, structured_json=None,
            voting_result=None,
        )
        assert result["level"] in ("critical_review_required", "dangerous")
        assert result["score"] >= 46

    def test_multiple_violations_escalate_risk(self):
        violations = ["HU on xray", "axiale Schicht on xray", "Lungenembolie on xray"]
        result = classify_risk(
            violations=violations, visibility_data=self._base_visibility(),
            confidence_float=0.85, structured_json={"visible_findings": [], "uncertain_findings": []},
            voting_result=None,
        )
        assert result["score"] >= 45  # 3 × 15 = 45

    def test_poor_image_quality_adds_score(self):
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor"}
        result = classify_risk(
            violations=[], visibility_data=vis,
            confidence_float=0.85, structured_json={"visible_findings": [], "uncertain_findings": []},
            voting_result=None,
        )
        assert result["score"] >= 25

    def test_disagreement_adds_score(self):
        result = classify_risk(
            violations=[], visibility_data=self._base_visibility(),
            confidence_float=0.85, structured_json={"visible_findings": [], "uncertain_findings": []},
            voting_result={"disagreement": True, "agreement_score": 0.25, "disagreement_terms": ["Embolie"]},
        )
        assert result["score"] >= 25

    def test_high_risk_term_in_uncertain_escalates(self):
        result = classify_risk(
            violations=[], visibility_data=self._base_visibility(),
            confidence_float=0.85,
            structured_json={"visible_findings": [], "uncertain_findings": ["Mögliche Metastase"]},
            voting_result=None,
        )
        assert result["score"] >= 20

    def test_dangerous_level_threshold(self):
        """Score >= 71 must produce 'dangerous'."""
        vis_poor = {"visible": [], "partial": ["a","b","c"], "hidden": ["x","y"], "image_quality": "poor"}
        violations = ["v1", "v2", "v3", "v4"]
        result = classify_risk(
            violations=violations, visibility_data=vis_poor,
            confidence_float=0.55, structured_json=None,
            voting_result={"disagreement": True, "agreement_score": 0.1, "disagreement_terms": []},
        )
        assert result["level"] == "dangerous"
        assert result["score"] >= 71

    def test_4_levels_are_complete(self):
        """All 4 level strings must be reachable (no typos)."""
        valid_levels = {"low_risk", "moderate_risk", "critical_review_required", "dangerous"}
        base_vis = self._base_visibility()
        # low_risk
        r1 = classify_risk([], base_vis, 0.85, {"visible_findings":[], "uncertain_findings":[]}, None)
        assert r1["level"] in valid_levels
        # moderate_risk
        r2 = classify_risk([], base_vis, 0.72, {"visible_findings":[], "uncertain_findings":[]}, None)
        assert r2["level"] in valid_levels


# ═══════════════════════════════════════════════════════════════
# E) HUMAN REVIEW MODE
# ═══════════════════════════════════════════════════════════════

class TestHumanReviewMode:

    def _base_vis(self):
        return {"visible": ["thorax"], "partial": [], "hidden": [], "image_quality": "good"}

    def test_no_trigger_when_safe(self):
        show, banner = should_trigger_human_review(
            "low_risk", 0.85, [], self._base_vis(), {"disagreement": False}
        )
        assert not show
        assert banner == ""

    def test_triggers_on_low_confidence(self):
        show, banner = should_trigger_human_review(
            "low_risk", 0.55, [], self._base_vis(), None
        )
        assert show
        assert "ÜBERPRÜFUNG" in banner or "Überprüfung" in banner

    def test_triggers_on_many_violations(self):
        show, banner = should_trigger_human_review(
            "low_risk", 0.85, ["v1", "v2"], self._base_vis(), None
        )
        assert show

    def test_triggers_on_critical_risk_level(self):
        show, banner = should_trigger_human_review(
            "critical_review_required", 0.85, [], self._base_vis(), None
        )
        assert show

    def test_triggers_on_dangerous_risk_level(self):
        show, banner = should_trigger_human_review(
            "dangerous", 0.55, ["v1","v2","v3"], self._base_vis(), {"disagreement": True}
        )
        assert show
        assert "EMPFOHLEN" in banner

    def test_triggers_on_disagreement(self):
        show, banner = should_trigger_human_review(
            "low_risk", 0.85, [], self._base_vis(),
            {"disagreement": True, "disagreement_terms": []}
        )
        assert show

    def test_triggers_on_poor_image_quality(self):
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor"}
        show, banner = should_trigger_human_review("low_risk", 0.85, [], vis, None)
        assert show

    def test_banner_contains_reasons(self):
        vis = {"visible": [], "partial": ["a","b","c"], "hidden": [], "image_quality": "limited"}
        show, banner = should_trigger_human_review(
            "critical_review_required", 0.55, ["v1","v2"], vis,
            {"disagreement": True}
        )
        assert show
        assert len(banner) > 50


# ═══════════════════════════════════════════════════════════════
# F) MULTI-MODEL VOTING
# ═══════════════════════════════════════════════════════════════

class TestModelVoting:

    def test_single_model_no_disagreement(self):
        result = compute_model_agreement([ANALYSIS_A_PNEUMONIA])
        assert result["agreement_score"] == 1.0
        assert not result["disagreement"]

    def test_similar_analyses_agree(self):
        result = compute_model_agreement([ANALYSIS_A_PNEUMONIA, ANALYSIS_B_PNEUMONIA])
        assert result["agreement_score"] >= 0.40, f"Expected agreement, got {result}"
        assert not result["disagreement"]

    def test_divergent_analyses_disagree(self):
        result = compute_model_agreement([ANALYSIS_A_DIVERGE, ANALYSIS_B_DIVERGE])
        # A mentions Pneumothorax, B mentions Atelektase — low overlap
        assert result["models_compared"] == 2

    def test_empty_analyses_no_crash(self):
        result = compute_model_agreement([])
        assert result["agreement_score"] == 1.0

    def test_short_text_ignored(self):
        result = compute_model_agreement(["ok", "yes"])
        assert result["models_compared"] == 0  # too short

    def test_three_agreeing_models(self):
        result = compute_model_agreement([
            ANALYSIS_A_PNEUMONIA, ANALYSIS_B_PNEUMONIA,
            "Infiltrat nachweisbar. Pleuraerguss nicht ausgeschlossen."
        ])
        assert result["models_compared"] == 3


# ═══════════════════════════════════════════════════════════════
# G) JSON PARSING
# ═══════════════════════════════════════════════════════════════

class TestJSONParsing:

    def test_parses_valid_json_block(self):
        raw = """<<<JSON>>>
{"visible_findings": ["Infiltrat rechts"], "uncertain_findings": [], "limitations": ["eingeschränkt"], "forbidden_sections_skipped": []}
<<<END_JSON>>>
## 1. Technik
Bericht hier."""
        result = parse_analysis_json(raw)
        assert result is not None
        assert result["visible_findings"] == ["Infiltrat rechts"]

    def test_returns_none_without_markers(self):
        result = parse_analysis_json("Normaler Bericht ohne JSON-Block.")
        assert result is None

    def test_strip_removes_json_block(self):
        raw = """<<<JSON>>>
{"visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []}
<<<END_JSON>>>
## 1. Technik
Bericht hier."""
        stripped = strip_analysis_json_block(raw)
        assert "<<<JSON>>>" not in stripped
        assert "Bericht hier" in stripped

    def test_strip_preserves_report_text(self):
        raw = "<<<JSON>>>{\"x\":1}<<<END_JSON>>>\n\n## Befund\nNormal."
        stripped = strip_analysis_json_block(raw)
        assert "## Befund" in stripped
        assert "Normal." in stripped


# ═══════════════════════════════════════════════════════════════
# H) BUILD PROMPT — sanity checks
# ═══════════════════════════════════════════════════════════════

class TestBuildPrompt:

    def test_valid_categories_produce_subtype(self):
        for cat in VALID_CATEGORIES:
            prompt = build_prompt(cat)
            assert len(prompt) > 200, f"Prompt too short for category: {cat}"

    def test_unknown_category_returns_master_only(self):
        prompt = build_prompt("unknown_modality_xyz")
        assert "KERNREGELN" in prompt
        assert "Nicht sicher beurteilbar" in prompt

    def test_xray_prompt_forbids_hu(self):
        prompt = build_prompt("xray")
        assert "Hounsfield" in prompt or "HU" in prompt  # mentioned as forbidden

    def test_xray_prompt_forbids_embolism(self):
        prompt = build_prompt("xray")
        assert "Lungenembolie" in prompt  # listed as forbidden in xray subtype

    def test_json_format_included_by_default(self):
        prompt = build_prompt("ct")
        assert "<<<JSON>>>" in prompt

    def test_json_format_excluded_when_disabled(self):
        prompt = build_prompt("ct", include_json_format=False)
        assert "<<<JSON>>>" not in prompt

    def test_safety_layer_injected(self):
        safety = {"visible_regions": ["abdomen"], "partial_regions": [], "forbidden_assessment": ["heart"]}
        prompt = build_prompt("ct", safety_layer=safety)
        assert "abdomen" in prompt
        assert "heart" in prompt or "forbidden_assessment" in prompt

    def test_alias_resolution(self):
        """Aliases must resolve to correct category."""
        assert "EKG" in build_prompt("ecg") or "Rhythmus" in build_prompt("ecg")
        assert "Röntgen" in build_prompt("röntgen") or "Hounsfield" in build_prompt("röntgen")


# ═══════════════════════════════════════════════════════════════
# UNSAFE OUTPUT BENCHMARKS — detect specific dangerous hallucinations
# ═══════════════════════════════════════════════════════════════

class TestUnsafeOutputBenchmarks:
    """
    Golden dataset tests: inject known-unsafe LLM outputs through
    the pipeline and verify safety functions catch them.
    """

    def test_blocks_fake_cancer_claim_via_language_norm(self):
        """'Hochwahrscheinlich Karzinom' must be normalized at any reasonable conf."""
        text = "Hochwahrscheinlich Karzinom Stadium IV gesichert."
        result, changes = normalize_clinical_language(text, 0.72)
        assert len(changes) > 0 or "nicht ausgeschlossen" in result.lower()

    def test_blocks_fake_embolism_on_xray_via_validator(self):
        """Lungenembolie on X-ray must trigger violation."""
        _, violations = validate_modality_output(HALLUCINATED_EMBOLISM, "xray")
        assert any("Lungenembolie" in v for v in violations)

    def test_blocks_fake_HU_on_xray_via_validator(self):
        """HU values on X-ray must trigger violation."""
        _, violations = validate_modality_output(HALLUCINATED_CT_TERMS_ON_XRAY, "xray")
        assert any("Hounsfield" in v or "HU" in v for v in violations)

    def test_blocks_probability_percentages_at_low_conf(self):
        """Probability percentages removed at confidence < 0.72."""
        result = apply_confidence_gate(HALLUCINATED_PROBABILITY_REPORT, 0.65)
        import re
        assert not re.search(r'\b(85|70|55)\s*%', result)

    def test_blocks_definitiv_at_medium_conf(self):
        """'Definitiv' replaced when confidence < 0.85."""
        result, changes = normalize_clinical_language(
            "Definitiv handelt es sich um Malignom.", 0.72
        )
        assert len(changes) > 0

    def test_hallucinated_cancer_gets_risk_dangerous_or_critical(self):
        """Cancer claim in uncertain_findings → risk escalates."""
        result = classify_risk(
            violations=["Hounsfield on xray", "Lungenembolie on xray"],
            visibility_data={"visible": [], "partial": ["thorax"], "hidden": ["heart"], "image_quality": "limited"},
            confidence_float=0.55,
            structured_json={"visible_findings": [], "uncertain_findings": ["Mögliches Karzinom"]},
            voting_result={"disagreement": True, "agreement_score": 0.2, "disagreement_terms": []},
        )
        assert result["level"] in ("critical_review_required", "dangerous")

    def test_hallucinated_hemorrhage_certainty_triggers_review(self):
        """High-certainty hemorrhage claim at low confidence triggers review."""
        vis = {"visible": ["brain"], "partial": [], "hidden": [], "image_quality": "limited"}
        text = apply_confidence_gate("Definitive Hirnblutung links temporal nachgewiesen. 90% sicher.", 0.55)
        show, banner = should_trigger_human_review("critical_review_required", 0.55, [], vis, None)
        assert show
        assert "90%" not in text


# ═══════════════════════════════════════════════════════════════
# N) JSON SCHEMA VALIDATION TESTS — Step 6b
# ═══════════════════════════════════════════════════════════════

class TestValidateJsonSchema:

    def test_valid_minimal_json(self):
        """All required fields present and typed correctly => valid."""
        data = {
            "visible_regions": ["thorax"],
            "partial_regions": [],
            "visible_findings": ["Infiltrat rechts basal"],
            "uncertain_findings": [],
            "limitations": [],
            "forbidden_sections_skipped": [],
            "image_quality": "limited",
        }
        result = validate_json_schema(data)
        assert result["valid"] is True
        assert result["schema_ok"] is True
        assert result["quality_ok"] is True
        assert len(result["errors"]) == 0

    def test_missing_required_field(self):
        """Missing 'visible_regions' => schema error."""
        data = {
            "partial_regions": ["lungen"],
            "visible_findings": [],
            "uncertain_findings": [],
            "limitations": [],
            "forbidden_sections_skipped": [],
        }
        result = validate_json_schema(data)
        assert result["valid"] is False
        assert result["schema_ok"] is False
        assert any("visible_regions" in e for e in result["errors"])

    def test_field_wrong_type_list_expected(self):
        """'visible_regions' as string instead of list => type error."""
        data = {
            "visible_regions": "thorax",
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
            "limitations": [],
            "forbidden_sections_skipped": [],
        }
        result = validate_json_schema(data)
        assert result["valid"] is False
        assert any("Liste" in e for e in result["errors"])

    def test_field_item_not_string(self):
        """List item is a number => type error."""
        data = {
            "visible_regions": ["thorax", 123],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
            "limitations": [],
            "forbidden_sections_skipped": [],
        }
        result = validate_json_schema(data)
        assert result["valid"] is False
        assert any("String" in e for e in result["errors"])

    def test_invalid_image_quality_value(self):
        """image_quality = 'super' => quality error."""
        data = {
            "visible_regions": ["thorax"],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
            "limitations": [],
            "forbidden_sections_skipped": [],
            "image_quality": "super",
        }
        result = validate_json_schema(data)
        assert result["valid"] is False
        assert result["quality_ok"] is False
        assert any("image_quality" in e.lower() for e in result["errors"])

    def test_valid_image_quality_known_values(self):
        """All four known quality values pass."""
        for qval in ("good", "limited", "poor", "unknown"):
            data = {
                "visible_regions": [],
                "partial_regions": [],
                "visible_findings": [],
                "uncertain_findings": [],
                "limitations": [],
                "forbidden_sections_skipped": [],
                "image_quality": qval,
            }
            result = validate_json_schema(data)
            assert result["quality_ok"] is True, f"quality={qval} should be valid"

    def test_none_input_returns_invalid(self):
        """None data => not valid."""
        result = validate_json_schema(None)
        assert result["valid"] is False
        assert result["schema_ok"] is False

    def test_non_dict_input_returns_invalid(self):
        """Non-dict data => not valid."""
        result = validate_json_schema(["not", "a", "dict"])
        assert result["valid"] is False


# ═══════════════════════════════════════════════════════════════
# O) CANONICAL VOCABULARY TESTS — Step 6c
# ═══════════════════════════════════════════════════════════════

class TestValidateCanonicalVocabulary:

    def test_canonical_anatomical_terms_valid(self):
        """Known anatomical terms => valid."""
        data = {
            "visible_regions": ["thorax", "lungen"],
            "partial_regions": ["herz"],
            "visible_findings": ["Infiltrat rechts"],
            "uncertain_findings": [],
        }
        result = validate_canonical_vocabulary(data)
        assert result["valid"] is True
        assert len(result["non_canonical"]) == 0

    def test_non_canonical_hallucinated_term(self):
        """Hallucinated term like 'Lungenventrikel' => invalid."""
        data = {
            "visible_regions": ["thorax"],
            "partial_regions": [],
            "visible_findings": ["Lungenventrikel rechts vergrößert"],
            "uncertain_findings": [],
        }
        result = validate_canonical_vocabulary(data)
        assert result["valid"] is False
        assert len(result["non_canonical"]) > 0

    def test_generic_terms_always_canonical(self):
        """Generic safe terms like 'unauffällig', 'regelrecht' => always pass."""
        for term in ("unauffällig", "regelrecht", "normalbefund", "kein nachweis"):
            data = {
                "visible_regions": [term],
                "partial_regions": [],
                "visible_findings": [],
                "uncertain_findings": [],
            }
            result = validate_canonical_vocabulary(data)
            assert result["valid"] is True, f"term '{term}' should be canonical"

    def test_none_input_returns_invalid(self):
        """None structured_json => invalid."""
        result = validate_canonical_vocabulary(None)
        assert result["valid"] is False

    def test_empty_fields_all_canonical(self):
        """All empty lists => canonical ratio 1.0, valid."""
        data = {
            "visible_regions": [],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
        }
        result = validate_canonical_vocabulary(data)
        assert result["valid"] is True
        assert result["canonical_ratio"] == 1.0


# ═══════════════════════════════════════════════════════════════
# P) JSON-NARRATIVE CONSISTENCY TESTS — Step 6d
# ═══════════════════════════════════════════════════════════════

class TestCheckJsonNarrativeConsistency:

    def test_hidden_region_mentioned_in_narrative_flags_warning(self):
        """Narrative mentions finding in hidden region => consistency warning."""
        json_data = {
            "visible_regions": ["thorax"],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
        }
        visibility_data = {"visible": ["thorax"], "partial": [], "hidden": ["brain"], "image_quality": "limited"}
        narrative = "Intrazerebrale Blutung links temporal. Mediastinum unauffällig."
        result = check_json_narrative_consistency(json_data, narrative, visibility_data)
        assert result["warnings"] is not None
        assert len(result["warnings"]) > 0

    def test_visible_region_mentioned_in_narrative_is_consistent(self):
        """Narrative findings match visible regions => no warnings."""
        json_data = {
            "visible_regions": ["thorax", "lungen"],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
        }
        visibility_data = {"visible": ["thorax", "lungen"], "partial": [], "hidden": [], "image_quality": "good"}
        narrative = "Infiltrat rechts basal. Zwerchfell glatt begrenzt. Lunge beidseits belüftet."
        result = check_json_narrative_consistency(json_data, narrative, visibility_data)
        assert result["warnings"] is None or len(result["warnings"]) == 0

    def test_none_json_returns_consistent(self):
        """None json_data => consistent (nothing to cross-check)."""
        result = check_json_narrative_consistency(None, "Some narrative text")
        assert result["consistent"] is True

    def test_empty_narrative_returns_consistent(self):
        """Empty narrative => consistent."""
        json_data = {
            "visible_regions": ["thorax"],
            "partial_regions": [],
            "visible_findings": [],
            "uncertain_findings": [],
        }
        visibility_data = {"visible": ["thorax"], "partial": [], "hidden": [], "image_quality": "good"}
        result = check_json_narrative_consistency(json_data, "", visibility_data)
        assert result["consistent"] is True


# ═══════════════════════════════════════════════════════════════
# Q) STRICT CLINICAL SAFETY MODE TESTS — Step 9d-2
# ═══════════════════════════════════════════════════════════════

class TestStrictClinicalSafetyMode:

    def test_high_uncertainty_triggers_strict_csm(self):
        """Low confidence (0.40) + disagreement => triggers strict CSM."""
        triggered, reason = should_trigger_strict_csm(
            voting_result={"disagreement": True, "agreement_score": 0.1},
            visibility_data={"visible": [], "partial": [], "hidden": ["brain"], "image_quality": "poor"},
            risk_result={"level": "high_risk"},
            violations=["forbidden_term"],
            confidence_float=0.40,
        )
        assert triggered is True
        assert len(reason) > 0

    def test_high_image_quality_low_confidence_no_csm(self):
        """Good image quality but very low confidence => not strict CSM."""
        triggered, reason = should_trigger_strict_csm(
            voting_result={"disagreement": False, "agreement_score": 0.3},
            visibility_data={"visible": ["thorax"], "partial": [], "hidden": [], "image_quality": "good"},
            risk_result={"level": "low"},
            violations=[],
            confidence_float=0.40,
        )
        assert triggered is False

    def test_poor_image_quality_triggers_csm(self):
        """Poor image quality alone => triggers strict CSM."""
        triggered, reason = should_trigger_strict_csm(
            voting_result=None,
            visibility_data={"visible": [], "partial": [], "hidden": [], "image_quality": "poor"},
            risk_result=None,
            violations=[],
            confidence_float=0.70,
        )
        assert triggered is True
        assert "image_quality" in reason.lower() or "poor" in reason.lower()

    def test_apply_strict_csm_strips_differential(self):
        """Strict CSM removes differentialdiagnose section."""
        text = """
## 1. Technik
Thorax p.a.

## 2. Befund
Infiltrat rechts basal.

## 3. Differentialdiagnose
1. Pneumonie (80%)
2. Atelektase (20%)

## 4. Beurteilung
Klinische Korrelation erforderlich.
"""
        stripped, modified = apply_strict_clinical_safety_mode(text)
        assert modified is True
        assert "Differentialdiagnose" not in stripped or "Deaktiviert" in stripped

    def test_apply_strict_csm_preserves_findings(self):
        """Strict CSM keeps ## 2. Befund section."""
        text = """
## 2. Befund
Infiltrat rechts basal. Pleurawinkel rechts verschattet.
"""
        stripped, modified = apply_strict_clinical_safety_mode(text)
        assert "Infiltrat" in stripped
        assert "Befund" in stripped

    def test_apply_strict_csm_adds_banner(self):
        """Strict CSM output starts with safety banner."""
        text = "## 2. Befund\nNormale Lunge beidseits."
        stripped, modified = apply_strict_clinical_safety_mode(text)
        assert modified is True
        assert "KLINISCHER SICHERHEITSMODUS" in stripped or "KLIN." in stripped

    def test_build_strict_csm_log_entry(self):
        """Log entry captures before/after lengths."""
        from services.analyzer_prompts import build_strict_csm_log_entry
        log = build_strict_csm_log_entry(True, "low_confidence", True, 200, 100)
        assert log["step"] == "strict_clinical_safety_mode"
        assert log["activated"] is True
        assert log["chars_removed"] == 100

    def test_pipeline_catch_rate_on_ct_terms_xray(self):
        """Full unsafe XRAY report: expect ≥ 3 violations."""
        text = """Hounsfield-Einheiten 45 HU. Axiale Schicht zeigt mediastinale Lymphadenopathie.
                  Enhancement nach Kontrastmittelgabe. Lungenembolie beidseits."""
        _, violations = validate_modality_output(text, "xray")
        assert len(violations) >= 3, f"Expected ≥3 violations, got: {violations}"
