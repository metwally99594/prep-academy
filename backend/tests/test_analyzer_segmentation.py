"""
Anatomical Segmentation Unit Tests — OpenCV heuristic region detection.

Tests the detect_anatomical_regions() function using synthetically generated
base64-encoded grayscale images that mimic real radiological intensity patterns.

No real patient images needed. Each test constructs a numpy array with the
intensity pattern the heuristic expects, encodes it to JPEG base64, and
verifies the expected regions are (or are not) detected.

Run with: pytest backend/tests/test_analyzer_segmentation.py -v

Note: Tests are skipped automatically if OpenCV is not installed.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import base64
import io
import pytest

try:
    import numpy as np
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from services.image_segmentation import detect_anatomical_regions

pytestmark = pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not installed")


# ═══════════════════════════════════════════════════════════════
# HELPERS — synthetic image generators
# ═══════════════════════════════════════════════════════════════

def _encode_gray(arr: "np.ndarray") -> str:
    """Encode a numpy grayscale array to base64 JPEG string."""
    _, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return base64.b64encode(buf.tobytes()).decode()


def _make_chest_xray_pattern(h=512, w=512) -> "np.ndarray":
    """
    Simulate PA chest XRay intensity pattern:
    - Dark lateral zones (lung fields): lu_mean < 105, ru_mean < 105
    - Bright central mediastinum: center_mean > lat_mean + 18
    - Moderate bottom zone for diaphragm: bot_mean < 160
    - High std for ribs: std > 42
    """
    img = np.full((h, w), 130, dtype=np.uint8)
    # Dark left lung field (left 1/3)
    img[:h // 2, :w // 3] = 70
    # Dark right lung field (right 1/3)
    img[:h // 2, 2 * w // 3:] = 70
    # Bright central mediastinum
    img[h // 4: 3 * h // 4, w // 3: 2 * w // 3] = 180
    # Moderate bottom (diaphragm/lower thorax)
    img[2 * h // 3:, :] = 120
    # Add rib-like high contrast texture (alternating bright/dark stripes)
    for i in range(0, h, 30):
        img[i:i+4, :] = np.clip(img[i:i+4, :].astype(int) + 60, 0, 255).astype(np.uint8)
    return img


def _make_abdomen_pattern(h=512, w=600) -> "np.ndarray":
    """
    Simulate abdominal X-ray:
    - Uniform mid-gray throughout (70-190)
    - Some very dark spots in lower half (bowel gas < 35)
    - No lung dark pattern
    """
    img = np.full((h, w), 130, dtype=np.uint8)
    # Bowel gas pockets in lower half
    for y in range(h // 2, h, 60):
        for x in range(50, w - 50, 80):
            img[y:y+20, x:x+25] = 20
    # Upper portion also moderate gray
    img[:h // 3, :] = 145
    img[h // 3: 2 * h // 3, :] = 135
    return img


def _make_spine_pattern(h=700, w=300) -> "np.ndarray":
    """
    Simulate lateral spine X-ray:
    - Portrait aspect ratio > 1.3
    - Bright central column: ccol_mean > lat_mean + 22
    - No lung dark pattern
    """
    img = np.full((h, w), 100, dtype=np.uint8)
    # Bright central vertebral column
    cx = w // 3
    img[:, cx: cx + w // 3] = 200
    return img


def _make_extremity_pattern(h=600, w=150) -> "np.ndarray":
    """
    Simulate long bone X-ray (e.g. femur):
    - Very high aspect ratio > 1.6
    - No lung dark pattern
    - No abdomen pattern (not in 70-190 range)
    - High std > 35 for bones
    """
    img = np.full((h, w), 160, dtype=np.uint8)
    # Bright bone cortex in center column
    img[:, w // 3: 2 * w // 3] = 230
    # Dark soft tissue on sides
    img[:, :w // 4] = 60
    img[:, 3 * w // 4:] = 60
    return img


def _make_skull_ct_pattern(h=300, w=300) -> "np.ndarray":
    """
    Simulate axial skull CT (near-square):
    - Aspect ratio 0.85-1.15
    - Bright central oval (brain parenchyma): center_mean > 150
    - Dark outer border (air/skull table outer): mean_val < 130
    """
    img = np.full((h, w), 60, dtype=np.uint8)
    # Bright central oval
    cx, cy = w // 2, h // 2
    cv2.ellipse(img, (cx, cy), (w // 3, h // 3), 0, 0, 360, 200, -1)
    return img


def _make_blank_image(h=256, w=256, value=128) -> "np.ndarray":
    """Near-uniform image — should be flagged as poor quality."""
    return np.full((h, w), value, dtype=np.uint8)


def _make_tiny_image(h=32, w=32) -> "np.ndarray":
    """Below minimum size threshold (64x64)."""
    return np.full((h, w), 100, dtype=np.uint8)


# ═══════════════════════════════════════════════════════════════
# TESTS: Chest XRay Detection
# ═══════════════════════════════════════════════════════════════

class TestChestXRayDetection:
    def setup_method(self):
        img = _make_chest_xray_pattern()
        self.b64 = _encode_gray(img)
        self.result = detect_anatomical_regions(self.b64, "xray")

    def test_thorax_detected(self):
        assert "thorax" in self.result["detected_regions"]

    def test_lungs_detected(self):
        assert "lungs" in self.result["detected_regions"]

    def test_method_is_opencv(self):
        assert self.result["method"] == "opencv_heuristic"

    def test_image_stats_present(self):
        stats = self.result["image_stats"]
        assert "mean" in stats
        assert "std" in stats
        assert "aspect_ratio" in stats

    def test_quality_not_poor(self):
        assert self.result["quality_estimate"] in ("good", "limited")

    def test_no_extremities_in_chest(self):
        assert "extremities" not in self.result["detected_regions"]

    def test_no_abdomen_as_primary_region(self):
        # Abdomen may appear as partial but not as primary detected region
        assert "abdomen" not in self.result["detected_regions"]


# ═══════════════════════════════════════════════════════════════
# TESTS: Abdomen Detection
# ═══════════════════════════════════════════════════════════════

class TestAbdomenDetection:
    def setup_method(self):
        img = _make_abdomen_pattern()
        self.b64 = _encode_gray(img)
        self.result = detect_anatomical_regions(self.b64, "xray")

    def test_abdomen_detected(self):
        assert "abdomen" in self.result["detected_regions"]

    def test_thorax_not_detected(self):
        assert "thorax" not in self.result["detected_regions"]

    def test_lungs_not_detected(self):
        assert "lungs" not in self.result["detected_regions"]

    def test_method_is_opencv(self):
        assert self.result["method"] == "opencv_heuristic"

    def test_bowel_detected_from_gas_pattern(self):
        """Bowel gas pockets should trigger bowel detection."""
        assert "bowel" in self.result["detected_regions"]


# ═══════════════════════════════════════════════════════════════
# TESTS: Spine Detection
# ═══════════════════════════════════════════════════════════════

class TestSpineDetection:
    def setup_method(self):
        img = _make_spine_pattern()
        self.b64 = _encode_gray(img)
        self.result = detect_anatomical_regions(self.b64, "xray")

    def test_spine_detected(self):
        assert "spine" in self.result["detected_regions"]

    def test_thorax_not_detected(self):
        assert "thorax" not in self.result["detected_regions"]

    def test_aspect_ratio_portrait(self):
        assert self.result["image_stats"]["aspect_ratio"] > 1.3


# ═══════════════════════════════════════════════════════════════
# TESTS: Extremity Detection
# ═══════════════════════════════════════════════════════════════

class TestExtremityDetection:
    def setup_method(self):
        img = _make_extremity_pattern()
        self.b64 = _encode_gray(img)
        self.result = detect_anatomical_regions(self.b64, "xray")

    def test_extremities_detected(self):
        assert "extremities" in self.result["detected_regions"]

    def test_soft_tissue_detected(self):
        assert "soft_tissue" in self.result["detected_regions"]

    def test_no_thorax_detected(self):
        assert "thorax" not in self.result["detected_regions"]

    def test_aspect_ratio_high(self):
        assert self.result["image_stats"]["aspect_ratio"] > 1.6


# ═══════════════════════════════════════════════════════════════
# TESTS: Skull CT Detection
# ═══════════════════════════════════════════════════════════════

class TestSkullCTDetection:
    def setup_method(self):
        img = _make_skull_ct_pattern()
        self.b64 = _encode_gray(img)
        self.result = detect_anatomical_regions(self.b64, "ct")

    def test_skull_in_partial_or_detected(self):
        all_regions = (
            self.result["detected_regions"] + self.result["partial_regions"]
        )
        assert "skull" in all_regions

    def test_aspect_ratio_near_square(self):
        ar = self.result["image_stats"]["aspect_ratio"]
        assert 0.85 <= ar <= 1.15

    def test_method_is_opencv(self):
        assert self.result["method"] == "opencv_heuristic"


# ═══════════════════════════════════════════════════════════════
# TESTS: Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_blank_image_poor_quality(self):
        """Near-uniform image should be flagged as poor quality."""
        img = _make_blank_image(value=128)
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["quality_estimate"] == "poor"

    def test_blank_image_no_regions(self):
        """Blank image should produce no detected regions."""
        img = _make_blank_image(value=128)
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["detected_regions"] == []

    def test_tiny_image_returns_gracefully(self):
        """Images below 64x64 should return without crashing."""
        img = _make_tiny_image()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["detected_regions"] == []
        assert result["method"] == "image_too_small"

    def test_invalid_base64_returns_gracefully(self):
        """Garbage base64 should not raise — returns decode_failed."""
        result = detect_anatomical_regions("not_valid_base64!!", "xray")
        assert result["detected_regions"] == []
        assert result["method"] in ("decode_failed", "opencv_unavailable")

    def test_empty_string_returns_gracefully(self):
        """Empty string input should not crash."""
        result = detect_anatomical_regions("", "xray")
        assert result["detected_regions"] == []

    def test_result_keys_always_present(self):
        """All expected keys present regardless of input."""
        result = detect_anatomical_regions("", "xray")
        for key in ("detected_regions", "partial_regions", "image_stats",
                    "quality_estimate", "method"):
            assert key in result

    def test_modality_empty_string_works(self):
        """Empty modality string falls through to defaults gracefully."""
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "")
        assert isinstance(result["detected_regions"], list)

    def test_unknown_modality_works(self):
        """Unknown modality string does not crash."""
        img = _make_abdomen_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "unknown_modality")
        assert isinstance(result["detected_regions"], list)


# ═══════════════════════════════════════════════════════════════
# TESTS: Image Stats Sanity
# ═══════════════════════════════════════════════════════════════

class TestImageStats:
    def test_mean_in_valid_range(self):
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert 0 <= result["image_stats"]["mean"] <= 255

    def test_std_positive(self):
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["image_stats"]["std"] >= 0

    def test_aspect_ratio_is_float(self):
        img = _make_abdomen_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert isinstance(result["image_stats"]["aspect_ratio"], float)

    def test_high_std_image_not_poor_quality(self):
        """High contrast image should NOT be poor quality."""
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["quality_estimate"] != "poor"

    def test_near_uniform_image_poor_quality(self):
        """std < 12 → poor quality."""
        img = np.full((256, 256), 100, dtype=np.uint8)
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        assert result["quality_estimate"] == "poor"


# ═══════════════════════════════════════════════════════════════
# TESTS: No Duplicate Regions
# ═══════════════════════════════════════════════════════════════

class TestDeduplication:
    def test_no_duplicate_detected_regions(self):
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        detected = result["detected_regions"]
        assert len(detected) == len(set(detected))

    def test_no_duplicate_partial_regions(self):
        img = _make_abdomen_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        partial = result["partial_regions"]
        assert len(partial) == len(set(partial))

    def test_partial_not_in_detected(self):
        """A region cannot be in both detected and partial lists."""
        img = _make_chest_xray_pattern()
        b64 = _encode_gray(img)
        result = detect_anatomical_regions(b64, "xray")
        overlap = set(result["detected_regions"]) & set(result["partial_regions"])
        assert len(overlap) == 0
