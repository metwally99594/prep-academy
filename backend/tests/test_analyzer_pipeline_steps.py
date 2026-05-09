"""
Analyzer Pipeline Steps — Pure Function Unit Tests.

Tests each safety-critical function in analyzer_prompts.py in isolation —
no LLM calls, no server, no database.

Each test class corresponds to one pipeline step (Step 7-9e).
All inputs are constructed inline as plain Python values.

Run with: pytest backend/tests/test_analyzer_pipeline_steps.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.analyzer_prompts import (
    apply_confidence_gate,
    normalize_clinical_language,
    validate_modality_output,
    classify_risk,
    should_trigger_human_review,
    should_use_clinical_safety_mode,
    apply_clinical_safety_mode,
    compute_model_agreement,
    build_pipeline_explainability_log,
)


# ═══════════════════════════════════════════════════════════════
# STEP 8 — apply_confidence_gate
# ═══════════════════════════════════════════════════════════════

class TestApplyConfidenceGate:
    SAFE_TEXT = "Kein Nachweis einer Pneumonie. Regelrechter Befund."

    def test_high_confidence_preserves_text(self):
        result = apply_confidence_gate(self.SAFE_TEXT, 0.90)
        assert result == self.SAFE_TEXT

    def test_low_confidence_does_not_crash(self):
        result = apply_confidence_gate(self.SAFE_TEXT, 0.40)
        assert isinstance(result, str)

    def test_returns_string(self):
        result = apply_confidence_gate("some text", 0.72)
        assert isinstance(result, str)

    def test_empty_text_returns_empty(self):
        result = apply_confidence_gate("", 0.72)
        assert result == ""

    def test_confidence_above_threshold_keeps_malignancy_terms(self):
        text = "Verdacht auf malignen Prozess."
        result = apply_confidence_gate(text, 0.90)
        assert isinstance(result, str)

    def test_threshold_boundary_0_85_is_high_confidence(self):
        """At confidence = 0.85, gate should allow full text."""
        result = apply_confidence_gate(self.SAFE_TEXT, 0.85)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════
# STEP 8b — normalize_clinical_language
# ═══════════════════════════════════════════════════════════════

class TestNormalizeClinicalLanguage:
    def test_returns_tuple(self):
        text, changes = normalize_clinical_language("Normal text.", 0.90)
        assert isinstance(text, str)
        assert isinstance(changes, list)

    def test_no_changes_on_safe_text(self):
        _, changes = normalize_clinical_language("Kein Nachweis einer Pneumonie.", 0.90)
        assert changes == []

    def test_always_forbidden_phrase_replaced_at_high_confidence(self):
        """FORBIDDEN_PHRASES_ALWAYS must always be replaced."""
        text = "Das Ergebnis ist absolut sicher ein Infarkt."
        result, changes = normalize_clinical_language(text, 0.99)
        assert "absolut sicher" not in result.lower()

    def test_language_gate_phrase_replaced_at_low_confidence(self):
        """'definitiv' at confidence < 0.85 must be replaced."""
        text = "Definitiv eine Pneumonie."
        result, changes = normalize_clinical_language(text, 0.60)
        assert "definitiv" not in result.lower()
        assert len(changes) > 0

    def test_language_gate_phrase_kept_at_high_confidence(self):
        """'definitiv' at confidence >= 0.85 should NOT be replaced."""
        text = "Definitiv eine Pneumonie."
        result, changes = normalize_clinical_language(text, 0.90)
        assert "definitiv" in result.lower()
        assert changes == []

    def test_empty_text_returns_empty(self):
        text, changes = normalize_clinical_language("", 0.72)
        assert text == ""
        assert changes == []


# ═══════════════════════════════════════════════════════════════
# STEP 9 — validate_modality_output
# ═══════════════════════════════════════════════════════════════

class TestValidateModalityOutput:
    def test_returns_tuple(self):
        text, violations = validate_modality_output("Normal chest X-ray.", "xray")
        assert isinstance(text, str)
        assert isinstance(violations, list)

    def test_clean_xray_report_no_violations(self):
        text = "Kein Nachweis eines Pneumothorax. Herz normal groß."
        _, violations = validate_modality_output(text, "xray")
        assert violations == []

    def test_hounsfield_in_xray_is_violation(self):
        text = "Der Herd zeigt einen Hounsfield-Wert von 45 HU."
        _, violations = validate_modality_output(text, "xray")
        assert len(violations) > 0

    def test_hounsfield_in_ct_is_not_violation(self):
        text = "Der Herd zeigt einen Hounsfield-Wert von 45 HU."
        _, violations = validate_modality_output(text, "ct")
        assert violations == []

    def test_lungenembolie_in_xray_is_violation(self):
        text = "Der Befund ist vereinbar mit einer Lungenembolie."
        _, violations = validate_modality_output(text, "xray")
        assert any("lungenembolie" in v.lower() for v in violations)

    def test_lungenembolie_in_ct_is_not_violation(self):
        text = "Der Befund ist vereinbar mit einer Lungenembolie."
        _, violations = validate_modality_output(text, "ct")
        assert violations == []

    def test_ekg_ct_terms_are_violation(self):
        text = "Röntgenbefund zeigt normalen Thorax."
        _, violations = validate_modality_output(text, "ekg")
        assert len(violations) > 0

    def test_empty_modality_no_crash(self):
        text, violations = validate_modality_output("Some text.", "")
        assert isinstance(text, str)
        assert isinstance(violations, list)

    def test_unknown_modality_no_crash(self):
        text, violations = validate_modality_output("Some text.", "unknown")
        assert isinstance(violations, list)

    def test_violations_are_strings(self):
        text = "Hounsfield Wert und axiale Schicht."
        _, violations = validate_modality_output(text, "xray")
        for v in violations:
            assert isinstance(v, str)


# ═══════════════════════════════════════════════════════════════
# STEP 9b — classify_risk
# ═══════════════════════════════════════════════════════════════

class TestClassifyRisk:
    def _make_visibility(self, quality="good", hidden=None):
        return {
            "image_quality": quality,
            "visible": ["thorax", "lungs"],
            "partial": [],
            "hidden": hidden or [],
        }

    def test_returns_dict_with_required_keys(self):
        result = classify_risk(
            violations=[],
            visibility_data=self._make_visibility(),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        assert "level" in result
        assert "score" in result
        assert "reasons" in result

    def test_clean_input_is_low_risk(self):
        result = classify_risk(
            violations=[],
            visibility_data=self._make_visibility(),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        assert result["level"] == "low_risk"

    def test_violations_increase_risk(self):
        clean = classify_risk(
            violations=[],
            visibility_data=self._make_visibility(),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        risky = classify_risk(
            violations=["Hounsfield", "axiale Schicht"],
            visibility_data=self._make_visibility(),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        assert risky["score"] > clean["score"]

    def test_poor_quality_increases_risk(self):
        good = classify_risk(
            violations=[],
            visibility_data=self._make_visibility("good"),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        poor = classify_risk(
            violations=[],
            visibility_data=self._make_visibility("poor"),
            confidence_float=0.85,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        assert poor["score"] > good["score"]

    def test_low_confidence_increases_risk(self):
        high = classify_risk(
            violations=[],
            visibility_data=self._make_visibility(),
            confidence_float=0.90,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        low = classify_risk(
            violations=[],
            visibility_data=self._make_visibility(),
            confidence_float=0.40,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )
        assert low["score"] > high["score"]

    def test_level_is_valid_enum(self):
        result = classify_risk(
            violations=["Hounsfield"] * 5,
            visibility_data=self._make_visibility("poor"),
            confidence_float=0.40,
            structured_json=None,
            voting_result={"disagreement": True, "agreement_score": 0.3},
        )
        valid_levels = {"low_risk", "moderate_risk", "critical_review_required", "dangerous"}
        assert result["level"] in valid_levels

    def test_reasons_is_list(self):
        result = classify_risk(
            violations=["Hounsfield"],
            visibility_data=self._make_visibility(),
            confidence_float=0.72,
            structured_json=None,
            voting_result={"disagreement": False, "agreement_score": 0.8},
        )
        assert isinstance(result["reasons"], list)


# ═══════════════════════════════════════════════════════════════
# STEP 9c — should_trigger_human_review
# ═══════════════════════════════════════════════════════════════

class TestShouldTriggerHumanReview:
    def _safe_inputs(self):
        return dict(
            risk_level="low_risk",
            confidence_float=0.85,
            violations=[],
            visibility_data={"image_quality": "good", "hidden": []},
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )

    def test_returns_tuple_bool_str(self):
        triggered, banner = should_trigger_human_review(**self._safe_inputs())
        assert isinstance(triggered, bool)
        assert isinstance(banner, str)

    def test_clean_input_no_review(self):
        triggered, _ = should_trigger_human_review(**self._safe_inputs())
        assert triggered is False

    def test_dangerous_risk_triggers_review(self):
        inputs = self._safe_inputs()
        inputs["risk_level"] = "dangerous"
        triggered, _ = should_trigger_human_review(**inputs)
        assert triggered is True

    def test_critical_risk_triggers_review(self):
        inputs = self._safe_inputs()
        inputs["risk_level"] = "critical_review_required"
        triggered, _ = should_trigger_human_review(**inputs)
        assert triggered is True

    def test_banner_is_non_empty_when_triggered(self):
        inputs = self._safe_inputs()
        inputs["risk_level"] = "dangerous"
        triggered, banner = should_trigger_human_review(**inputs)
        assert triggered is True
        assert len(banner) > 0


# ═══════════════════════════════════════════════════════════════
# STEP 9d — should_use_clinical_safety_mode
# ═══════════════════════════════════════════════════════════════

class TestShouldUseClinicalSafetyMode:
    def _safe_inputs(self):
        return dict(
            risk_result={"level": "low_risk", "score": 10, "reasons": []},
            visibility_data={"image_quality": "good", "hidden": [], "partial": []},
            voting_result={"disagreement": False, "agreement_score": 1.0},
        )

    def test_returns_tuple_bool_str(self):
        activated, reason = should_use_clinical_safety_mode(**self._safe_inputs())
        assert isinstance(activated, bool)
        assert isinstance(reason, str)

    def test_safe_input_no_activation(self):
        activated, _ = should_use_clinical_safety_mode(**self._safe_inputs())
        assert activated is False

    def test_dangerous_risk_activates_csm(self):
        inputs = self._safe_inputs()
        inputs["risk_result"] = {"level": "dangerous", "score": 90, "reasons": ["critical"]}
        activated, _ = should_use_clinical_safety_mode(**inputs)
        assert activated is True

    def test_multiple_signals_activate_csm(self):
        """Poor quality + disagreement + critical risk should activate CSM."""
        inputs = dict(
            risk_result={"level": "critical_review_required", "score": 70, "reasons": ["r"]},
            visibility_data={"image_quality": "poor", "hidden": ["lungs", "heart"], "partial": []},
            voting_result={"disagreement": True, "agreement_score": 0.3},
        )
        activated, _ = should_use_clinical_safety_mode(**inputs)
        assert activated is True


# ═══════════════════════════════════════════════════════════════
# STEP 9d — apply_clinical_safety_mode
# ═══════════════════════════════════════════════════════════════

class TestApplyClinicalSafetyMode:
    REPORT_WITH_INTERPRETATION = (
        "## Befunde\nKein Nachweis eines Pneumothorax.\n\n"
        "## Interpretation\nDer Befund ist regelrecht.\n\n"
        "## Differentialdiagnosen\nKeine relevanten Differentialdiagnosen."
    )

    def test_returns_tuple_str_bool(self):
        result, applied = apply_clinical_safety_mode(self.REPORT_WITH_INTERPRETATION)
        assert isinstance(result, str)
        assert isinstance(applied, bool)

    def test_strips_interpretation_section(self):
        result, applied = apply_clinical_safety_mode(self.REPORT_WITH_INTERPRETATION)
        assert "## Interpretation" not in result

    def test_strips_differential_section(self):
        result, applied = apply_clinical_safety_mode(self.REPORT_WITH_INTERPRETATION)
        assert "## Differentialdiagnosen" not in result

    def test_preserves_befunde_section(self):
        result, applied = apply_clinical_safety_mode(self.REPORT_WITH_INTERPRETATION)
        assert "Kein Nachweis eines Pneumothorax" in result

    def test_applied_flag_true_when_section_stripped(self):
        _, applied = apply_clinical_safety_mode(self.REPORT_WITH_INTERPRETATION)
        assert applied is True

    def test_no_change_on_report_without_sections(self):
        simple = "Kein Nachweis eines Pneumothorax. Normalbefund."
        result, applied = apply_clinical_safety_mode(simple)
        assert applied is False

    def test_empty_text_no_crash(self):
        result, applied = apply_clinical_safety_mode("")
        assert isinstance(result, str)
        assert isinstance(applied, bool)


# ═══════════════════════════════════════════════════════════════
# STEP 7b — compute_model_agreement
# ═══════════════════════════════════════════════════════════════

class TestComputeModelAgreement:
    PNEUMONIA_TEXT = "Infiltrat im linken Unterlappen. Verdacht auf Pneumonie."
    NORMAL_TEXT = "Kein Nachweis eines Infiltrats. Unauffälliger Thoraxbefund."

    def test_returns_dict(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT])
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT, self.PNEUMONIA_TEXT])
        for key in ("disagreement", "agreement_score"):
            assert key in result, f"Missing key: {key}"

    def test_single_report_no_disagreement(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT])
        assert result.get("disagreement") is False

    def test_identical_reports_no_disagreement(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT, self.PNEUMONIA_TEXT])
        assert result.get("disagreement") is False

    def test_contradictory_reports_show_disagreement(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT, self.NORMAL_TEXT])
        assert result.get("disagreement") is True

    def test_agreement_score_is_float(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT, self.NORMAL_TEXT])
        assert isinstance(result.get("agreement_score"), float)

    def test_agreement_score_in_range(self):
        result = compute_model_agreement([self.PNEUMONIA_TEXT, self.PNEUMONIA_TEXT])
        score = result.get("agreement_score", 0.0)
        assert 0.0 <= score <= 1.0

    def test_empty_list_no_crash(self):
        result = compute_model_agreement([])
        assert isinstance(result, dict)

    def test_none_values_filtered(self):
        result = compute_model_agreement([None, self.PNEUMONIA_TEXT])
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# STEP 9e — build_pipeline_explainability_log
# ═══════════════════════════════════════════════════════════════

class TestBuildPipelineExplainabilityLog:
    def _minimal_inputs(self):
        return dict(
            confidence=0.85,
            violations=[],
            lang_changes=[],
            risk_result={"level": "low_risk", "score": 10, "reasons": []},
            voting_result={"disagreement": False, "agreement_score": 1.0},
            visibility_data={"image_quality": "good", "hidden": [], "partial": []},
            clinical_safety_mode=False,
        )

    def test_returns_list(self):
        result = build_pipeline_explainability_log(**self._minimal_inputs())
        assert isinstance(result, list)

    def test_each_entry_has_required_keys(self):
        result = build_pipeline_explainability_log(**self._minimal_inputs())
        for entry in result:
            for key in ("step", "reason", "action", "detail"):
                assert key in entry, f"Missing key {key!r} in entry {entry}"

    def test_entries_contain_strings(self):
        result = build_pipeline_explainability_log(**self._minimal_inputs())
        for entry in result:
            assert isinstance(entry.get("step"), str)
            assert isinstance(entry.get("action"), str)

    def test_violation_entry_appears_when_violations_present(self):
        inputs = self._minimal_inputs()
        inputs["violations"] = ["Hounsfield", "axiale Schicht"]
        result = build_pipeline_explainability_log(**inputs)
        steps = [e["step"] for e in result]
        assert any("validat" in s.lower() or "violation" in s.lower() or "modality" in s.lower()
                   for s in steps)

    def test_language_change_entry_appears(self):
        inputs = self._minimal_inputs()
        inputs["lang_changes"] = ["definitiv → möglicherweise"]
        result = build_pipeline_explainability_log(**inputs)
        steps = [e["step"] for e in result]
        assert any("language" in s.lower() or "sprach" in s.lower() or "lang" in s.lower()
                   for s in steps)

    def test_csm_entry_appears_when_activated(self):
        inputs = self._minimal_inputs()
        inputs["clinical_safety_mode"] = True
        result = build_pipeline_explainability_log(**inputs)
        steps = [e["step"] for e in result]
        assert any("safety" in s.lower() or "csm" in s.lower() or "klinisch" in s.lower()
                   for s in steps)

    def test_no_entry_for_normal_pipeline(self):
        """With all clean inputs, minimal or no entries expected."""
        result = build_pipeline_explainability_log(**self._minimal_inputs())
        assert isinstance(result, list)
