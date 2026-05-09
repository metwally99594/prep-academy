"""
Anatomical region segmentation — OpenCV heuristics only.
No ML models required. Supplements LLM-based visibility detection.

Heuristic rules (X-ray / CT focus):
  - Thorax: dark lateral zones (lung fields) + bright central mediastinum
  - Abdomen: mid-range gray tones with gas (very dark) patterns in lower half
  - Spine:   bright vertical central band in portrait images
  - Extremity: high aspect ratio, no lung pattern

When uncertain, returns empty lists rather than guessing.
Results are merged with LLM visibility in merge_visibility_with_segmentation().
"""

import base64 as _b64
from typing import Optional

try:
    import numpy as _np
    import cv2 as _cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False


def _decode_b64_to_gray(image_b64: str) -> "Optional[_np.ndarray]":
    if not _CV2_OK:
        return None
    try:
        raw = _b64.b64decode(image_b64)
        arr = _np.frombuffer(raw, dtype=_np.uint8)
        return _cv2.imdecode(arr, _cv2.IMREAD_GRAYSCALE)
    except Exception:
        return None


def detect_anatomical_regions(image_b64: str, modality: str = "") -> dict:
    """
    Heuristic anatomical region detection from intensity patterns.

    Args:
        image_b64: raw base64 (no data-URI prefix)
        modality:  detected category hint ('xray', 'ct', 'mri', ...)

    Returns:
        {
            "detected_regions": list[str],   # high-confidence visible
            "partial_regions":  list[str],   # partial / edge-of-frame
            "image_stats":      dict,        # mean, std, aspect_ratio
            "quality_estimate": str,         # "good"|"limited"|"poor"
            "method":           str,
        }
    """
    _default = {
        "detected_regions": [], "partial_regions": [],
        "image_stats": {}, "quality_estimate": "unknown",
        "method": "unavailable",
    }

    if not _CV2_OK:
        return {**_default, "method": "opencv_unavailable"}

    img = _decode_b64_to_gray(image_b64)
    if img is None or img.size == 0:
        return {**_default, "method": "decode_failed"}

    h, w = img.shape
    if h < 64 or w < 64:
        return {**_default, "method": "image_too_small"}

    mean_val = float(img.mean())
    std_val  = float(img.std())
    aspect   = h / max(w, 1)

    # ── Image quality estimate ──
    if std_val < 12:
        quality = "poor"      # near-uniform → blank / overexposed / screenshot
    elif std_val < 28:
        quality = "limited"
    else:
        quality = "good"

    detected: list[str] = []
    partial:  list[str] = []

    # ── Zone crops ──
    top3   = img[:h // 3,       :]
    bot3   = img[2 * h // 3:,   :]
    center = img[h // 4: 3 * h // 4,  w // 4: 3 * w // 4]
    lu     = img[:h // 2,  :w // 3]           # left upper
    ru     = img[:h // 2,  2 * w // 3:]       # right upper
    ccol   = img[:,          w // 3: 2 * w // 3]  # central column

    top_mean    = float(top3.mean())
    bot_mean    = float(bot3.mean())
    center_mean = float(center.mean())
    lu_mean     = float(lu.mean())
    ru_mean     = float(ru.mean())
    ccol_mean   = float(ccol.mean())
    lat_mean    = (lu_mean + ru_mean) / 2

    # ── Thorax / Lung pattern ──
    # PA chest X-ray: dark lateral lung fields, brighter central mediastinum
    lung_dark = lu_mean < 105 and ru_mean < 105

    if lung_dark and modality in ("xray", "ct", ""):
        detected.append("thorax")
        detected.append("lungs")

        # Heart / mediastinum: central zone noticeably brighter than lateral
        if center_mean > lat_mean + 18:
            detected.append("heart")
            detected.append("mediastinum")
        else:
            partial.append("mediastinum")

        # Pleura / diaphragm visible if image covers bottom of thorax
        if bot_mean < 160:
            detected.append("pleura")
            detected.append("diaphragm")

        # Ribs / clavicles (high local contrast on dark background)
        if std_val > 42:
            detected.append("ribs")
            detected.append("clavicles")

        # Abdomen partially visible if lower portion is moderate gray
        if bot_mean > 80:
            partial.append("abdomen")

    # ── Abdomen pattern ──
    # More uniform mid-gray; bowel gas = very dark focal areas
    elif not lung_dark and 70 < top_mean < 190 and 70 < bot_mean < 190:
        detected.append("abdomen")
        bowel_gas_ratio = float((bot3 < 35).mean())
        if bowel_gas_ratio > 0.04:
            detected.append("bowel")
        if center_mean > 130:
            partial.append("liver")
            partial.append("spleen")
        if aspect < 1.0:  # wide image → pelvis likely included
            partial.append("pelvis")

    # ── Spine pattern ──
    # Bright vertical central band in portrait images
    if ccol_mean > lat_mean + 22 and aspect > 1.3 and not lung_dark:
        detected.append("spine")

    # ── Extremity pattern ──
    # Portrait with no lung / abdomen pattern
    if (aspect > 1.6
            and not lung_dark
            and "abdomen" not in detected
            and "spine" not in detected):
        detected.append("extremities")
        if std_val > 35:
            detected.append("bones")
        detected.append("soft_tissue")

    # ── Skull / Brain (rough) ──
    # Near-square image: bright central oval surrounded by dark border
    if (0.85 < aspect < 1.15
            and center_mean > 150
            and mean_val < 130
            and modality in ("ct", "mri", "")):
        partial.append("skull")
        if modality == "mri":
            partial.append("brain")

    # Deduplicate, preserve order
    detected = list(dict.fromkeys(detected))
    partial  = [r for r in dict.fromkeys(partial) if r not in detected]

    return {
        "detected_regions": detected,
        "partial_regions":  partial,
        "image_stats": {
            "mean":         round(mean_val, 1),
            "std":          round(std_val,  1),
            "aspect_ratio": round(aspect,   2),
        },
        "quality_estimate": quality,
        "method": "opencv_heuristic",
    }
