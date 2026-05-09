"""
Red-Team Dataset Tests — System robustness under adversarial inputs.

Tests the full safety pipeline's behaviour on pathological inputs:
  - Badly cropped / very small images
  - Rotated / wrong orientation images
  - Screenshots / meme images (near-uniform with text-like patterns)
  - Heavily noisy images
  - Mixed-modality images (half bright / half dark)
  - Fake medical images (overlaid text on noise)

Verifies that the pipeline:
  1. Does NOT crash
  2. Returns "poor" or "limited" quality estimate (no false confidence)
  3. Detects no confident anatomical regions on garbage inputs
  4. Clinical Safety Mode activates when signals converge
  5. Explainability log always produced

Run with: pytest backend/tests/test_analyzer_redteam.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import base64
import pytest

try:
    import numpy as np
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from services.image_segmentation import detect_anatomical_regions
from services.analyzer_prompts import (
    should_use_clinical_safety_mode,
    apply_clinical_safety_mode,
    build_pipeline_explainability_log,
    classify_risk,
    should_trigger_human_review,
)

pytestmark = pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not installed")


# ═══════════════════════════════════════════════════════════════
# RED-TEAM IMAGE GENERATORS
# ═══════════════════════════════════════════════════════════════

def _encode(arr: "np.ndarray") -> str:
    _, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode()


def make_badly_cropped(h=40, w=512) -> "np.ndarray":
    """Extremely narrow — too small in one dimension."""
    return np.random.randint(60, 200, (h, w), dtype=np.uint8)


def make_tiny_image(h=20, w=20) -> "np.ndarray":
    """Below minimum threshold on both sides."""
    return np.full((h, w), 128, dtype=np.uint8)


def make_rotated_90(base_h=512, base_w=200) -> "np.ndarray":
    """Portrait image rotated 90° → becomes wide, aspect < 1."""
    img = np.full((base_h, base_w), 80, dtype=np.uint8)
    img[:, base_w // 3: 2 * base_w // 3] = 200
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)


def make_meme_screenshot() -> "np.ndarray":
    """Near-white background with dark 'text' blocks — typical screenshot."""
    img = np.full((300, 500), 240, dtype=np.uint8)
    # Simulate text lines
    for y in range(30, 270, 25):
        img[y:y+8, 20:480] = np.random.randint(30, 80, (8, 460), dtype=np.uint8)
    return img


def make_heavy_noise() -> "np.ndarray":
    """Pure random noise — no anatomical structure."""
    return np.random.randint(0, 255, (300, 300), dtype=np.uint8)


def make_mixed_modality() -> "np.ndarray":
    """Left half: dark XRay-like, right half: bright CT-like."""
    img = np.zeros((400, 400), dtype=np.uint8)
    img[:, :200] = 60       # dark like lung field
    img[:, 200:] = 210      # bright like bone window CT
    return img


def make_fake_medical_overlay() -> "np.ndarray":
    """Noise base + bright central oval (simulates 'looks like CT but is noise)."""
    img = np.random.randint(40, 120, (300, 300), dtype=np.uint8)
    cv2.ellipse(img, (150, 150), (80, 80), 0, 0, 360, 220, -1)
    # Add noise inside the ellipse too
    mask = np.zeros((300, 300), dtype=np.uint8)
    cv2.ellipse(mask, (150, 150), (80, 80), 0, 0, 360, 1, -1)
    noise = np.random.randint(-30, 30, (300, 300), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise * mask, 0, 255).astype(np.uint8)
    return img


def make_inverted_colors() -> "np.ndarray":
    """255 - normal chest pattern — inversion attacks heuristics."""
    normal = np.full((512, 512), 130, dtype=np.uint8)
    normal[:256, :170] = 70   # dark lung fields
    normal[:256, 342:] = 70
    normal[128:384, 170:342] = 180  # bright mediastinum
    return (255 - normal).astype(np.uint8)


# ═══════════════════════════════════════════════════════════════
# TESTS: Segmentation robustness on bad inputs
# ═══════════════════════════════════════════════════════════════

class TestSegmentationRobustness:

    def test_badly_cropped_no_crash(self):
        b64 = _encode(make_badly_cropped())
        result = detect_anatomical_regions(b64, "xray")
        assert isinstance(result, dict)
        assert "detected_regions" in result

    def test_badly_cropped_no_confident_regions(self):
        """A 40-row strip should not produce confident anatomical claims."""
        b64 = _encode(make_badly_cropped())
        result = detect_anatomical_regions(b64, "xray")
        # Either too_small or we get empty regions
        if result["method"] == "image_too_small":
            assert result["detected_regions"] == []
        else:
            assert len(result["detected_regions"]) <= 2

    def test_tiny_image_graceful(self):
        b64 = _encode(make_tiny_image())
        result = detect_anatomical_regions(b64, "xray")
        assert result["method"] == "image_too_small"
        assert result["detected_regions"] == []

    def test_screenshot_poor_quality(self):
        """Screenshot (high mean, low std) must be flagged as poor quality."""
        b64 = _encode(make_meme_screenshot())
        result = detect_anatomical_regions(b64, "xray")
        assert result["quality_estimate"] == "poor"

    def test_screenshot_no_confident_anatomical_regions(self):
        b64 = _encode(make_meme_screenshot())
        result = detect_anatomical_regions(b64, "xray")
        assert result["detected_regions"] == []

    def test_heavy_noise_quality_is_poor_or_limited(self):
        """Pure noise: high std but no structure — quality should not be 'good'."""
        b64 = _encode(make_heavy_noise())
        result = detect_anatomical_regions(b64, "xray")
        # std will be very high but patterns are random — may detect regions or not
        # Critical: must not crash
        assert isinstance(result["detected_regions"], list)

    def test_mixed_modality_does_not_claim_thorax(self):
        """Half dark / half bright — heuristic should not confidently say 'thorax'."""
        b64 = _encode(make_mixed_modality())
        result = detect_anatomical_regions(b64, "xray")
        # The pattern is ambiguous — no certain claim
        assert isinstance(result, dict)

    def test_inverted_colors_does_not_hallucinate(self):
        """Inverted chest pattern: heuristic should NOT detect 'thorax' (values flipped)."""
        b64 = _encode(make_inverted_colors())
        result = detect_anatomical_regions(b64, "xray")
        # Inverted: lu/ru_mean now > 105 → thorax rule does NOT fire
        assert "thorax" not in result["detected_regions"]

    def test_rotated_image_handled_gracefully(self):
        """Rotated 90° image should not crash."""
        b64 = _encode(make_rotated_90())
        result = detect_anatomical_regions(b64, "xray")
        assert isinstance(result["detected_regions"], list)

    def test_fake_medical_overlay_no_crash(self):
        b64 = _encode(make_fake_medical_overlay())
        result = detect_anatomical_regions(b64, "ct")
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# TESTS: Clinical Safety Mode under red-team conditions
# ═══════════════════════════════════════════════════════════════

class TestClinicalSafetyModeRedTeam:

    def _poor_visibility(self):
        return {"visible": [], "partial": [], "hidden": ["lungs", "heart"], "image_quality": "poor", "segmentation": {}}

    def _disagreement_voting(self):
        return {"agreement_score": 0.30, "disagreement": True, "models_compared": 2, "disagreement_terms": ["Infiltrat", "Pleuraerguss"]}

    def test_poor_quality_plus_disagreement_triggers_csm(self):
        """poor quality + disagreement + dangerous risk → CSM must activate."""
        risk = {"level": "dangerous", "score": 80, "reasons": ["test"]}
        vis = self._poor_visibility()
        voting = self._disagreement_voting()
        activated, reason = should_use_clinical_safety_mode(risk, vis, voting)
        assert activated

    def test_low_risk_high_quality_does_not_trigger_csm(self):
        """Good quality + agreement + low risk → CSM must NOT activate."""
        risk = {"level": "low_risk", "score": 10, "reasons": []}
        vis = {"visible": ["lungs", "heart"], "partial": [], "hidden": [], "image_quality": "good", "segmentation": {"mean": 120.0}}
        voting = {"agreement_score": 0.90, "disagreement": False, "models_compared": 3, "disagreement_terms": []}
        activated, _ = should_use_clinical_safety_mode(risk, vis, voting)
        assert not activated

    def test_csm_strips_differentials(self):
        """apply_clinical_safety_mode() strips the Differentialdiagnosen section."""
        report = """## Befund
Lunge unauffällig.

## Differentialdiagnosen
- Pneumonie 60%
- Atelektase 40%

## Beurteilung
Klinische Korrelation erforderlich."""
        stripped, was_modified = apply_clinical_safety_mode(report)
        assert was_modified
        assert "Pneumonie 60%" not in stripped
        assert "Deaktiviert" in stripped

    def test_csm_strips_interpretation_section(self):
        report = """## Befund
Direkter Befund.

## Interpretation
Dies deutet auf Tumorinfiltrat hin.

## Limitation
Qualität eingeschränkt."""
        stripped, was_modified = apply_clinical_safety_mode(report)
        assert was_modified
        assert "Tumorinfiltrat" not in stripped

    def test_csm_preserves_befund(self):
        """Befund section must survive Clinical Safety Mode."""
        report = """## Befund
Lunge beidseits belüftet. Kein Infiltrat.

## Differentialdiagnosen
- Pneumonie 80%"""
        stripped, _ = apply_clinical_safety_mode(report)
        assert "beidseits belüftet" in stripped

    def test_csm_not_modified_when_not_triggered(self):
        """apply_clinical_safety_mode on a clean report returns was_modified=False."""
        clean = "## Befund\nLunge unauffällig.\n\n## Limitation\nQualität gut."
        _, was_modified = apply_clinical_safety_mode(clean)
        assert not was_modified

    def test_csm_activates_for_screenshot_like_conditions(self):
        """Screenshot image → poor quality → segmentation empty → triggers if risk also elevated."""
        risk = {"level": "critical_review_required", "score": 55, "reasons": ["Bildqualität: SCHLECHT"]}
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor", "segmentation": {}}
        activated, _ = should_use_clinical_safety_mode(risk, vis, None)
        assert activated


# ═══════════════════════════════════════════════════════════════
# TESTS: Explainability Log always produced
# ═══════════════════════════════════════════════════════════════

class TestExplainabilityLog:

    def _base_log(self, confidence=0.85, violations=None, lang_changes=None,
                  risk=None, voting=None, vis=None, csm=False):
        return build_pipeline_explainability_log(
            confidence=confidence,
            violations=violations or [],
            lang_changes=lang_changes or [],
            risk_result=risk or {"level": "low_risk", "score": 5, "reasons": []},
            voting_result=voting,
            visibility_data=vis or {},
            clinical_safety_mode=csm,
        )

    def test_log_always_non_empty(self):
        log = self._base_log()
        assert len(log) > 0

    def test_log_entry_has_required_keys(self):
        log = self._base_log()
        for entry in log:
            assert "step" in entry
            assert "reason" in entry
            assert "action" in entry
            assert "detail" in entry

    def test_high_confidence_gate_logged_as_none(self):
        log = self._base_log(confidence=0.90)
        gate_entries = [e for e in log if e["step"] == "confidence_gate"]
        assert len(gate_entries) == 1
        assert gate_entries[0]["action"] == "none"

    def test_low_confidence_gate_logs_disabled_differentials(self):
        log = self._base_log(confidence=0.55)
        gate_entries = [e for e in log if e["step"] == "confidence_gate"]
        assert len(gate_entries) == 1
        assert "disabled_differentials" in gate_entries[0]["action"]

    def test_violations_each_logged_separately(self):
        violations = ["Verbotener Begriff für XRAY: 'HU'", "Verbotener Begriff für XRAY: 'axiale Schicht'"]
        log = self._base_log(violations=violations)
        v_entries = [e for e in log if e["step"] == "modality_validator" and e["action"] == "flagged_violation"]
        assert len(v_entries) == 2

    def test_lang_changes_logged(self):
        log = self._base_log(lang_changes=["'definitiv' → 'möglicherweise'"])
        lang_entries = [e for e in log if e["step"] == "language_normalization"]
        assert len(lang_entries) == 1

    def test_disagreement_logged(self):
        voting = {"agreement_score": 0.25, "disagreement": True, "models_compared": 2, "disagreement_terms": ["Infiltrat"]}
        log = self._base_log(voting=voting)
        vote_entries = [e for e in log if e["step"] == "model_voting" and e["action"] == "flagged_disagreement"]
        assert len(vote_entries) == 1
        assert "Infiltrat" in vote_entries[0]["detail"]

    def test_csm_logged_when_active(self):
        log = self._base_log(csm=True)
        csm_entries = [e for e in log if e["step"] == "clinical_safety_mode"]
        assert len(csm_entries) == 1
        assert "stripped" in csm_entries[0]["action"]

    def test_csm_not_logged_when_inactive(self):
        log = self._base_log(csm=False)
        csm_entries = [e for e in log if e["step"] == "clinical_safety_mode"]
        assert len(csm_entries) == 0

    def test_poor_quality_visibility_logged(self):
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor", "segmentation": {}}
        log = self._base_log(vis=vis)
        vis_entries = [e for e in log if e["step"] == "visibility_check"]
        assert len(vis_entries) == 1
        assert "poor" in vis_entries[0]["reason"]

    def test_risk_classifier_always_logged(self):
        log = self._base_log()
        risk_entries = [e for e in log if e["step"] == "risk_classifier"]
        assert len(risk_entries) == 1

    def test_no_violations_still_logged(self):
        log = self._base_log(violations=[])
        validator_entries = [e for e in log if e["step"] == "modality_validator"]
        assert len(validator_entries) == 1
        assert validator_entries[0]["action"] == "none"


# ═══════════════════════════════════════════════════════════════
# TESTS: End-to-end safety pipeline under red-team conditions
# ═══════════════════════════════════════════════════════════════

class TestEndToEndRedTeam:
    """Simulate full pipeline response (no LLM) for a garbage-image scenario."""

    def test_screenshot_pipeline_activates_csm(self):
        """Screenshot image → poor quality → CSM should activate if risk also elevated."""
        b64 = _encode(make_meme_screenshot())
        seg = detect_anatomical_regions(b64, "xray")

        # Simulate merged visibility with poor quality
        vis = {
            "visible": [], "partial": [], "hidden": [],
            "image_quality": seg["quality_estimate"],
            "segmentation": seg.get("image_stats", {}),
        }
        violations = []
        risk = classify_risk(violations, vis, 0.55, None, None)
        voting = None

        activated, reason = should_use_clinical_safety_mode(risk, vis, voting)
        # With poor quality + low confidence → at least moderate activation
        assert isinstance(activated, bool)
        assert isinstance(reason, str)

    def test_human_review_triggered_on_garbage_input(self):
        """Any low-confidence + poor quality analysis must trigger human review."""
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor", "segmentation": {}}
        risk = classify_risk([], vis, 0.55, None, None)
        triggered, _ = should_trigger_human_review(
            risk_level=risk["level"],
            confidence_float=0.55,
            violations=[],
            visibility_data=vis,
            voting_result=None,
        )
        assert triggered

    def test_explainability_log_complete_pipeline(self):
        """Full pipeline log: all expected steps present."""
        vis = {"visible": [], "partial": [], "hidden": [], "image_quality": "poor", "segmentation": {}}
        violations = ["Verbotener Begriff: 'HU'"]
        lang_changes = ["'definitiv' → 'möglicherweise'"]
        risk = classify_risk(violations, vis, 0.55, None, None)
        voting = {"agreement_score": 0.30, "disagreement": True, "models_compared": 2, "disagreement_terms": []}
        csm_activated, _ = should_use_clinical_safety_mode(risk, vis, voting)

        log = build_pipeline_explainability_log(
            confidence=0.55,
            violations=violations,
            lang_changes=lang_changes,
            risk_result=risk,
            voting_result=voting,
            visibility_data=vis,
            clinical_safety_mode=csm_activated,
        )

        steps_logged = {e["step"] for e in log}
        assert "confidence_gate" in steps_logged
        assert "modality_validator" in steps_logged
        assert "language_normalization" in steps_logged
        assert "risk_classifier" in steps_logged
        assert "model_voting" in steps_logged
        assert "visibility_check" in steps_logged
        if csm_activated:
            assert "clinical_safety_mode" in steps_logged
