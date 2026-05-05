"""
DICOM Analysis Pipeline — 100% Open-Source & Near-Zero-Cost
============================================================
Stack:
  - pydicom        → .dcm parsing (single file or ZIP series)
  - numpy + OpenCV → windowing, Canny edge scoring, feature extraction
  - Smart Sampling → no AI needed; selects top-K slices by edge density & variance
  - RAG + DeepSeek → cross-reference findings with the medical KB (citations)

Endpoints (all /api/dicom/*):
  POST /upload              multipart .dcm or .zip → returns analysis_id + previews
  POST /analyze/{id}        runs the pipeline + synthesises a clinical report
  GET  /{id}                retrieves a past analysis (for longitudinal tracking)
  GET  /list                lists the user's past analyses
  POST /compare/{id1}/{id2} Patient Longitudinal Tracking — diff between two scans
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import io
import base64
import uuid
import zipfile
import asyncio
from datetime import datetime, timezone

import numpy as np
import pydicom
import cv2

from database import db, logger
from auth import get_current_user
from routes.rag import _ensure_initialized, _embed_texts, _llm_call, LANG_INSTRUCT
from routes import rag as rag_module

router = APIRouter(prefix="/api/dicom", tags=["dicom"])

# ═══════════════════════ HELPERS ═══════════════════════

def _apply_windowing(pixel_array: np.ndarray, ds: pydicom.Dataset) -> np.ndarray:
    """Convert raw DICOM pixels to 8-bit display image using WindowCenter/Width if present."""
    arr = pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
    arr = arr * slope + intercept

    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth", None)
    if isinstance(wc, pydicom.multival.MultiValue):
        wc = float(wc[0])
    if isinstance(ww, pydicom.multival.MultiValue):
        ww = float(ww[0])

    if wc is not None and ww is not None:
        lo = float(wc) - float(ww) / 2
        hi = float(wc) + float(ww) / 2
        arr = np.clip(arr, lo, hi)
        arr = (arr - lo) / max(hi - lo, 1e-6) * 255.0
    else:
        mn, mx = float(arr.min()), float(arr.max())
        arr = (arr - mn) / max(mx - mn, 1e-6) * 255.0

    if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
        arr = 255.0 - arr
    return np.clip(arr, 0, 255).astype(np.uint8)


def _read_dicoms_from_bytes(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Accepts a single .dcm or a .zip bundle of .dcm files. Returns ordered slice dicts."""
    slices: List[Dict[str, Any]] = []

    def _parse_one(data: bytes, name: str):
        try:
            ds = pydicom.dcmread(io.BytesIO(data), force=True)
            if not hasattr(ds, "pixel_array"):
                return
            px = ds.pixel_array
            # Skip RGB/multi-frame colour for MVP
            if px.ndim >= 3 and px.shape[-1] == 3:
                px = cv2.cvtColor(px.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            if px.ndim == 3:  # multi-frame → explode frames
                for fi in range(px.shape[0]):
                    slices.append({
                        "name": f"{name}#frame{fi}",
                        "ds": ds,
                        "pixels": px[fi],
                        "instance": int(getattr(ds, "InstanceNumber", 0) or 0) * 1000 + fi,
                    })
            else:
                slices.append({
                    "name": name,
                    "ds": ds,
                    "pixels": px,
                    "instance": int(getattr(ds, "InstanceNumber", 0) or 0),
                })
        except Exception as e:
            logger.warning(f"[DICOM] Skip {name}: {e}")

    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for n in z.namelist():
                if n.lower().endswith(".dcm") and not n.startswith("__MACOSX"):
                    _parse_one(z.read(n), os.path.basename(n))
    else:
        _parse_one(file_bytes, filename)

    # Sort by InstanceNumber for anatomical ordering
    slices.sort(key=lambda s: s["instance"])
    return slices


def _score_slice(img8: np.ndarray) -> Dict[str, float]:
    """Per-slice feature extraction — 100% CPU, no AI."""
    edges = cv2.Canny(img8, 50, 150)
    edge_density = float(edges.sum()) / (img8.size * 255)  # normalised 0–1
    variance = float(img8.var())
    # Shannon entropy — higher = more information / heterogeneity
    hist, _ = np.histogram(img8.ravel(), bins=256, range=(0, 256))
    p = hist / max(hist.sum(), 1)
    entropy = float(-np.sum(p[p > 0] * np.log2(p[p > 0])))
    # Count dense regions (potential lesions/haemorrhage/masses)
    _, thr = cv2.threshold(img8, 160, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_bright_regions = sum(1 for c in contours if cv2.contourArea(c) > 150)
    # Dark regions (potential fluid/air)
    _, thr_dark = cv2.threshold(img8, 40, 255, cv2.THRESH_BINARY_INV)
    contours_d, _ = cv2.findContours(thr_dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_dark_regions = sum(1 for c in contours_d if cv2.contourArea(c) > 200)
    # Upgraded saliency: edges + entropy + region counts
    saliency = edge_density * 1000 + entropy * 50 + large_bright_regions * 2 + large_dark_regions * 1.5
    return {
        "edge_density": round(edge_density, 5),
        "variance": round(variance, 2),
        "entropy": round(entropy, 3),
        "bright_regions": int(large_bright_regions),
        "dark_regions": int(large_dark_regions),
        "saliency": round(saliency, 2),
    }


def _png_thumbnail_b64(img8: np.ndarray, max_dim: int = 256) -> str:
    """Return base64-encoded PNG thumbnail."""
    h, w = img8.shape[:2]
    s = min(max_dim / max(h, w), 1.0)
    resized = cv2.resize(img8, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", resized)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _extract_dicom_header(ds: pydicom.Dataset) -> Dict[str, Any]:
    """Extract safe header fields (no PHI beyond what was uploaded)."""
    return {
        "modality": str(getattr(ds, "Modality", "") or ""),
        "body_part": str(getattr(ds, "BodyPartExamined", "") or ""),
        "study_description": str(getattr(ds, "StudyDescription", "") or ""),
        "series_description": str(getattr(ds, "SeriesDescription", "") or ""),
        "patient_age": str(getattr(ds, "PatientAge", "") or ""),
        "patient_sex": str(getattr(ds, "PatientSex", "") or ""),
        "rows": int(getattr(ds, "Rows", 0) or 0),
        "columns": int(getattr(ds, "Columns", 0) or 0),
    }


# ═══════════════════════ QUALITY GATE (upload-time) ═══════════════════════
# Rejects garbage input BEFORE it reaches the analysis pipeline.
# Principle: "Garbage in → Garbage out".

# Modalities that are NOT diagnostic-grade original scans
_SECONDARY_CAPTURE_MODALITIES = {
    "OT",   # Other (often screenshots)
    "SC",   # Secondary Capture (re-digitised from film, screenshots, etc.)
    "PR",   # Presentation State (overlay)
    "KO",   # Key Object Selection
    "SR",   # Structured Report
}

# Modalities where a single slice is legitimate (projection imaging)
_SINGLE_SLICE_OK_MODALITIES = {
    "CR",   # Computed Radiography (classic X-ray)
    "DX",   # Digital Radiography
    "MG",   # Mammography
    "XA",   # X-ray Angiography
    "RF",   # Radio-Fluoroscopy
    "US",   # Ultrasound (single still)
    "ES",   # Endoscopy
}

MIN_SLICES_FOR_CROSS_SECTIONAL = 5  # CT / MR below this are unreliable


def _check_quality_gate(slices: List[Dict]) -> Dict[str, Any]:
    """Validate uploaded DICOM meets diagnostic quality requirements.
    Returns {"valid": bool, "reason": str|None, "action": str|None, "code": str|None}."""
    if not slices:
        return {"valid": False, "reason": "Keine gültigen DICOM-Schichten gefunden", "action": "Gültige .dcm-Datei oder ZIP hochladen", "code": "no_slices"}

    first = slices[0]
    ds = first["ds"]
    modality = str(getattr(ds, "Modality", "") or "").upper()
    sop_class = str(getattr(ds, "SOPClassUID", "") or "")

    # 1) Reject Secondary Capture / Other / Presentation State
    if modality in _SECONDARY_CAPTURE_MODALITIES:
        return {
            "valid": False,
            "reason": f"Modalität '{modality}' ist kein diagnostischer Original-Scan (Secondary Capture).",
            "action": "Bitte Original-Bildgebung direkt vom Gerät hochladen (CT/MR/CR/DX/US).",
            "code": "secondary_capture",
        }

    # Also catch by SOP Class UID (some tools set Modality=CT but SOP=SecondaryCapture)
    if "secondary" in sop_class.lower() or sop_class == "1.2.840.10008.5.1.4.1.1.7":
        return {
            "valid": False,
            "reason": "SOP Class UID zeigt Secondary Capture Image — kein diagnostisches Bild.",
            "action": "Bitte Original-Scan hochladen.",
            "code": "secondary_capture_sop",
        }

    # 2) Check slice count vs modality
    if modality in ("CT", "MR", "PT", "NM") and len(slices) < MIN_SLICES_FOR_CROSS_SECTIONAL:
        return {
            "valid": False,
            "reason": f"Nur {len(slices)} Schicht(en) für {modality} — mindestens {MIN_SLICES_FOR_CROSS_SECTIONAL} erforderlich für verlässliche Diagnostik.",
            "action": "Komplette Serie (als ZIP) hochladen, nicht einzelne Schichten.",
            "code": "insufficient_slices",
        }

    # 3) Warn (but do not reject) if modality is empty — some exports strip it.
    if not modality:
        return {
            "valid": True,
            "reason": None,
            "action": None,
            "code": "modality_missing",  # soft warning; analysis can still proceed
            "warning": "Modalität nicht angegeben — automatische Körperregion-Erkennung könnte scheitern.",
        }

    return {"valid": True, "reason": None, "action": None, "code": "ok"}


def _select_top_slices(slices: List[Dict], top_k: int = 8) -> List[int]:
    """Return indices of top-K slices by saliency score."""
    ranked = sorted(range(len(slices)), key=lambda i: slices[i]["score"]["saliency"], reverse=True)
    return ranked[: min(top_k, len(slices))]


# ═══════════════════════ CONTEXT-AWARE (Phase 2) ═══════════════════════

# Maps detected body part to: allowed pathologies (guides prompt) + RAG category filter +
# allowed ICD-10 prefixes (validates LLM output) + blocklist (detects hallucinations).
BODY_PART_CONTEXT: Dict[str, Dict[str, Any]] = {
    "chest": {
        "allowed_conditions": [
            "Pneumonie", "Pneumothorax", "Hämatothorax", "Pleuraerguss", "Lungenembolie",
            "Lungenkarzinom", "COPD-Exazerbation", "ARDS", "Rippenfraktur", "Mediastinalverschiebung",
        ],
        "rag_categories": ["Pneumologie", "Notfallmedizin", "Kardiologie", "Chirurgie"],
        # Include respiratory R-codes (R05 cough, R06 dyspnea, R07 chest pain, R09 resp-other, R91 lung findings)
        "icd10_prefixes": ("J", "I2", "I3", "S2", "C34", "R05", "R06", "R07", "R09", "R91"),
        "forbidden_terms": ["Schlaganfall", "Hirninfarkt", "Hirnblutung", "Appendizitis", "Fraktur des Schädels"],
        "label_de": "Thorax",
    },
    "brain": {
        "allowed_conditions": [
            "Hirninfarkt", "Intrazerebrale Blutung", "Subarachnoidalblutung", "Subduralhämatom",
            "Epiduralhämatom", "Hirntumor", "Hirnabszess", "Hirnödem", "Hydrozephalus", "Commotio cerebri",
        ],
        "rag_categories": ["Neurologie", "Notfallmedizin"],
        # Include neuro R-codes (R51 headache, R55 syncope, R40-42 coma/mental)
        "icd10_prefixes": ("I6", "S06", "C71", "G", "I67", "R4", "R51", "R55"),
        "forbidden_terms": ["Pneumonie", "Hämatothorax", "Appendizitis", "Rippenfraktur"],
        "label_de": "Schädel/Gehirn",
    },
    "abdomen": {
        "allowed_conditions": [
            "Appendizitis", "Cholezystitis", "Pankreatitis", "Ileus", "Perforation",
            "Leberzirrhose", "Hepatozelluläres Karzinom", "Nephrolithiasis", "Divertikulitis", "Aortenaneurysma",
        ],
        "rag_categories": ["Gastroenterologie", "Chirurgie", "Urologie", "Notfallmedizin"],
        # Include abdominal R-codes (R10 pain, R14 flatulence, R19 other)
        "icd10_prefixes": ("K", "N", "I71", "R10", "R11", "R14", "R19", "C22"),
        "forbidden_terms": ["Hirninfarkt", "Pneumothorax", "Commotio"],
        "label_de": "Abdomen",
    },
    "limb": {
        "allowed_conditions": [
            "Fraktur", "Luxation", "Weichteilverletzung", "Kompartmentsyndrom",
            "tiefe Venenthrombose", "Osteomyelitis",
        ],
        "rag_categories": ["Chirurgie", "Notfallmedizin", "Orthopädie"],
        "icd10_prefixes": ("S4", "S5", "S6", "S7", "S8", "S9", "T", "M"),
        "forbidden_terms": ["Hirninfarkt", "Pneumonie", "Myokardinfarkt"],
        "label_de": "Extremität",
    },
    "pelvis": {
        "allowed_conditions": ["Beckenfraktur", "Harnblasenruptur", "Hüftgelenksluxation", "Sakrumfraktur"],
        "rag_categories": ["Chirurgie", "Urologie"],
        "icd10_prefixes": ("S3", "T"),
        "forbidden_terms": ["Hirninfarkt", "Pneumonie"],
        "label_de": "Becken",
    },
    "spine": {
        "allowed_conditions": ["Bandscheibenvorfall", "Wirbelkörperfraktur", "Spondylose", "Myelitis"],
        "rag_categories": ["Neurologie", "Chirurgie", "Orthopädie"],
        "icd10_prefixes": ("M5", "S1", "S2", "S3"),
        "forbidden_terms": ["Pneumonie", "Hirninfarkt"],
        "label_de": "Wirbelsäule",
    },
    "unknown": {
        "allowed_conditions": ["allgemeine Pathologien"],
        "rag_categories": [],
        "icd10_prefixes": (),
        "forbidden_terms": [],
        "label_de": "Unbekannte Region",
    },
}

# Keyword table for heuristic body-part detection from DICOM header / description
_BODY_KEYWORDS = [
    ("chest", ["chest", "thorax", "thora", "lung", "pulmon", "pleura", "mediastin", "cardiac", "heart"]),
    ("brain", ["brain", "head", "cerebr", "crani", "kopf", "schädel", "neuro", "ct-schädel"]),
    ("abdomen", ["abdomen", "abdom", "liver", "leber", "pancrea", "kidney", "niere", "gastro", "hepat"]),
    ("pelvis", ["pelvis", "becken", "bladder", "blase", "sacrum", "hip"]),
    ("spine", ["spine", "wirbel", "lumbar", "cervic", "thoracic spine", "ls-spine"]),
    ("limb", ["limb", "extrem", "foot", "ankle", "knee", "hand", "arm", "leg", "bein", "hand", "femur", "tibia", "fibula", "humerus", "radius", "ulna"]),
]


def _detect_body_part(header: Dict[str, Any], sample_shape: Optional[tuple] = None) -> Dict[str, Any]:
    """Hybrid detection — fastest path wins:
    1) DICOM BodyPartExamined (direct mapping)
    2) StudyDescription / SeriesDescription keyword match
    3) Image aspect-ratio heuristic (portrait = likely limb)
    Returns {"body_part", "method", "confidence"}."""
    bp_raw = (header.get("body_part") or "").strip().lower()
    # DICOM standard BodyPartExamined values
    direct_map = {
        "chest": "chest", "thorax": "chest", "heart": "chest", "lung": "chest",
        "head": "brain", "brain": "brain", "skull": "brain", "neck": "brain",
        "abdomen": "abdomen", "liver": "abdomen", "pancreas": "abdomen", "kidney": "abdomen",
        "pelvis": "pelvis", "hip": "pelvis",
        "spine": "spine", "lspine": "spine", "cspine": "spine", "tspine": "spine",
        "extremity": "limb", "leg": "limb", "arm": "limb", "foot": "limb", "hand": "limb",
        "knee": "limb", "shoulder": "limb", "elbow": "limb", "ankle": "limb", "wrist": "limb",
    }
    if bp_raw in direct_map:
        return {"body_part": direct_map[bp_raw], "method": "dicom_metadata", "confidence": 0.99}

    # Keyword match against descriptions
    blob = " ".join([
        bp_raw,
        (header.get("study_description") or "").lower(),
        (header.get("series_description") or "").lower(),
    ])
    for body, kws in _BODY_KEYWORDS:
        if any(k in blob for k in kws):
            return {"body_part": body, "method": "keyword_match", "confidence": 0.85}

    # Aspect-ratio heuristic (portrait/tall → likely limb)
    if sample_shape and len(sample_shape) >= 2:
        h, w = sample_shape[:2]
        if w > 0:
            ratio = h / w
            if ratio > 1.4:
                return {"body_part": "limb", "method": "aspect_heuristic", "confidence": 0.55}

    return {"body_part": "unknown", "method": "fallback", "confidence": 0.3}


def _validate_output_vs_body_part(structured: Dict[str, Any], body_part: str) -> Dict[str, Any]:
    """Check structured LLM output against body-part constraints.
    Returns {"valid": bool, "flags": [...]}."""
    ctx = BODY_PART_CONTEXT.get(body_part, BODY_PART_CONTEXT["unknown"])
    flags = []

    # 1) Forbidden terms in findings
    findings_blob = " ".join([
        str(structured.get("findings", "")).lower(),
        " ".join(structured.get("red_flags", [])).lower(),
        " ".join(structured.get("explainability", [])).lower(),
    ])
    for term in ctx.get("forbidden_terms", []):
        if term.lower() in findings_blob:
            flags.append(f"Forbidden term '{term}' detected for body_part={body_part}")

    # 2) ICD-10 prefix consistency (only enforced if we have prefixes for this body part)
    prefixes = ctx.get("icd10_prefixes", ())
    if prefixes:
        for code in structured.get("icd10", []) or []:
            if not any(str(code).upper().startswith(p) for p in prefixes):
                flags.append(f"ICD-10 '{code}' not typical for body_part={body_part}")

    return {"valid": len(flags) == 0, "flags": flags}


def _confidence_gate(structured: Dict[str, Any], min_conf: float = 0.5) -> Dict[str, Any]:
    """Downgrade uncertain outputs to LOW urgency with a clear warning."""
    try:
        conf = float(structured.get("confidence", 0))
    except Exception:
        conf = 0.0
    if conf < min_conf:
        structured = {
            **structured,
            "urgency": "LOW",
            "confidence": conf,
            "explainability": (structured.get("explainability") or [])
            + [f"Niedrige Modell-Konfidenz ({conf:.2f}) — manuelle ärztliche Prüfung empfohlen."],
        }
    return structured


# ═══════════════════════ MODELS ═══════════════════════

class AnalyzeRequest(BaseModel):
    patient_context: str = ""
    language: str = "de"
    top_k: int = 8
    model: str = "openai/gpt-oss-120b:free"
    # Manual override — user can force a body part when DICOM metadata is missing
    # (e.g., when uploading JPEG X-ray or when BodyPartExamined was not set)
    body_part_override: Optional[str] = None


class CompareRequest(BaseModel):
    language: str = "de"
    model: str = "openai/gpt-oss-120b:free"


# ═══════════════════════ ENDPOINTS ═══════════════════════

@router.post("/upload")
async def upload_dicom(
    file: UploadFile = File(...),
    patient_label: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """Upload .dcm or .zip and run smart sampling. Returns analysis_id + previews."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Leere Datei")

    loop = asyncio.get_event_loop()
    slices = await loop.run_in_executor(None, lambda: _read_dicoms_from_bytes(raw, file.filename or "upload.dcm"))
    if not slices:
        raise HTTPException(status_code=400, detail="Keine gültigen DICOM-Schichten gefunden")

    # ═══ QUALITY GATE — reject garbage input early ═══
    gate = _check_quality_gate(slices)
    if not gate["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "code": gate["code"],
                "reason": gate["reason"],
                "action": gate["action"],
                "modality": str(getattr(slices[0]["ds"], "Modality", "") or ""),
                "slice_count": len(slices),
            },
        )

    # Score each slice
    for s in slices:
        img8 = _apply_windowing(s["pixels"], s["ds"])
        s["img8"] = img8
        s["score"] = _score_slice(img8)

    selected_idx = _select_top_slices(slices, top_k=8)
    previews = []
    for idx in selected_idx:
        s = slices[idx]
        previews.append({
            "index": idx,
            "name": s["name"],
            "instance": s["instance"],
            "score": s["score"],
            "thumbnail": _png_thumbnail_b64(s["img8"]),
        })

    # Store compact meta in DB — NOT the full pixel arrays (too big)
    analysis_id = str(uuid.uuid4())
    header = _extract_dicom_header(slices[0]["ds"]) if slices else {}
    per_slice_compact = [
        {"index": i, "name": s["name"], "instance": s["instance"], "score": s["score"]}
        for i, s in enumerate(slices)
    ]

    await db.dicom_analyses.insert_one({
        "id": analysis_id,
        "user_id": user["id"],
        "filename": file.filename,
        "patient_label": patient_label or "",
        "header": header,
        "total_slices": len(slices),
        "per_slice_scores": per_slice_compact,
        "selected_indices": selected_idx,
        "previews": previews,
        "status": "uploaded",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "analysis_id": analysis_id,
        "filename": file.filename,
        "total_slices": len(slices),
        "selected_count": len(selected_idx),
        "header": header,
        "previews": previews,
        "quality_warning": gate.get("warning"),
    }


def _build_findings_summary(doc: dict) -> str:
    """Turn numerical scores into textual findings (no AI; deterministic)."""
    header = doc.get("header", {})
    scores = doc.get("per_slice_scores", [])
    selected = set(doc.get("selected_indices", []))
    total = len(scores)

    edge_vals = [s["score"]["edge_density"] for s in scores]
    bright = [s["score"]["bright_regions"] for s in scores]
    dark = [s["score"]["dark_regions"] for s in scores]

    max_bright_idx = max(range(len(scores)), key=lambda i: scores[i]["score"]["bright_regions"]) if scores else 0
    max_dark_idx = max(range(len(scores)), key=lambda i: scores[i]["score"]["dark_regions"]) if scores else 0

    lines = [
        f"Modalität: {header.get('modality') or 'unbekannt'}",
        f"Körperregion: {header.get('body_part') or header.get('study_description') or 'nicht spezifiziert'}",
        f"Patientenalter: {header.get('patient_age') or 'n. a.'}, Geschlecht: {header.get('patient_sex') or 'n. a.'}",
        f"Gesamt-Schichten: {total}, automatisch ausgewählt (hohe Auffälligkeit): {len(selected)}",
        f"Kantendichte — Mittel: {np.mean(edge_vals):.4f}, Max: {np.max(edge_vals):.4f}",
        f"Hyperdense Regionen — Summe: {sum(bright)} (Peak in Schicht {scores[max_bright_idx]['instance']}: {scores[max_bright_idx]['score']['bright_regions']} Regionen)",
        f"Hypodense/luftige Regionen — Summe: {sum(dark)} (Peak in Schicht {scores[max_dark_idx]['instance']}: {scores[max_dark_idx]['score']['dark_regions']} Regionen)",
    ]
    # Flag top-3 most salient slices
    top3 = sorted(scores, key=lambda s: s["score"]["saliency"], reverse=True)[:3]
    lines.append("Top-3 auffällige Schichten:")
    for s in top3:
        lines.append(
            f"  - Schicht #{s['instance']}: saliency={s['score']['saliency']}, "
            f"hell={s['score']['bright_regions']}, dunkel={s['score']['dark_regions']}"
        )
    return "\n".join(lines)


@router.post("/analyze/{analysis_id}")
async def analyze_dicom(analysis_id: str, req: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """Kick off analysis in background; returns immediately. Client polls GET /api/dicom/{id}."""
    doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user["id"]}, {"_id": 0, "id": 1, "status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    # If already analyzed or in-flight, return current state
    if doc.get("status") == "analyzing":
        return {"analysis_id": analysis_id, "status": "analyzing", "message": "Analyse läuft bereits"}

    await db.dicom_analyses.update_one(
        {"id": analysis_id, "user_id": user["id"]},
        {"$set": {"status": "analyzing", "analyze_error": None, "analyze_started_at": datetime.now(timezone.utc).isoformat()}},
    )

    # Fire-and-forget background task — survives ingress 60s timeout
    asyncio.create_task(_run_analysis_job(analysis_id, user["id"], req))

    return {"analysis_id": analysis_id, "status": "analyzing", "message": "Analyse gestartet; bitte Status pollen"}


async def _run_analysis_job(analysis_id: str, user_id: str, req: "AnalyzeRequest"):
    """Background worker: runs Context-Aware RAG+DeepSeek and writes result to MongoDB."""
    try:
        doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user_id}, {"_id": 0})
        if not doc:
            return

        # ═══ PHASE 2: Context-Aware Auto-Detection ═══
        header = doc.get("header", {})
        sample_shape = (header.get("rows", 0), header.get("columns", 0))
        detection = _detect_body_part(header, sample_shape)

        # ═══ GATEKEEPER: No context = No analysis ═══
        # Allow manual override when automatic detection fails
        override = (req.body_part_override or "").strip().lower()
        if override and override in BODY_PART_CONTEXT:
            detection = {"body_part": override, "method": "manual_override", "confidence": 1.0}

        body_part = detection["body_part"]

        # Hard-stop if still unknown — prevents hallucinated reports without anatomical context
        if body_part == "unknown":
            ctx = BODY_PART_CONTEXT["unknown"]
            await db.dicom_analyses.update_one(
                {"id": analysis_id, "user_id": user_id},
                {"$set": {
                    "status": "context_missing",
                    "analyze_error": "Körperregion konnte nicht bestimmt werden. Bitte manuell angeben (body_part_override).",
                    "analysis": {
                        "detection": detection,
                        "body_part": body_part,
                        "body_part_label": ctx["label_de"],
                        "report": "",
                        "structured": {
                            "findings": "Analyse abgebrochen — keine Region erkannt.",
                            "urgency": "UNKNOWN",
                            "confidence": 0.0,
                            "red_flags": [],
                            "explainability": [
                                "DICOM-Metadaten enthalten keine Region (BodyPartExamined leer).",
                                "StudyDescription / SeriesDescription geben keinen Hinweis.",
                                "Kein manueller Override angegeben.",
                            ],
                            "icd10": [],
                        },
                        "valid_regions": sorted([k for k in BODY_PART_CONTEXT.keys() if k != "unknown"]),
                    },
                }},
            )
            logger.warning(f"[DICOM] Analysis {analysis_id} aborted — body_part unknown, no override")
            return

        ctx = BODY_PART_CONTEXT.get(body_part, BODY_PART_CONTEXT["unknown"])
        logger.info(f"[DICOM] Analysis {analysis_id} body_part detected: {body_part} (method={detection['method']}, conf={detection['confidence']})")

        findings_text = _build_findings_summary(doc)

        await _ensure_initialized()

        # ═══ RAG query with body-part-aware focus ═══
        focus_conditions = ", ".join(ctx["allowed_conditions"][:6])
        query = f"{ctx['label_de']} {header.get('modality','')} {req.patient_context} {focus_conditions}".strip()
        loop = asyncio.get_event_loop()
        q_vec = await loop.run_in_executor(None, lambda: _embed_texts([query]))

        # Filter RAG by category if body part has preferred categories
        where_filter = None
        if ctx["rag_categories"]:
            where_filter = {"category": {"$in": ctx["rag_categories"]}}
        try:
            results = rag_module._collection.query(
                query_embeddings=q_vec,
                n_results=max(1, min(req.top_k, 8)),
                where=where_filter,
            )
            if not results.get("documents", [[]])[0] and where_filter:
                # No hits with filter — retry unfiltered
                results = rag_module._collection.query(query_embeddings=q_vec, n_results=max(1, min(req.top_k, 8)))
        except Exception:
            # Chroma may reject complex filters on older schemas — graceful fallback
            results = rag_module._collection.query(query_embeddings=q_vec, n_results=max(1, min(req.top_k, 8)))

        rag_docs = results.get("documents", [[]])[0]
        rag_metas = results.get("metadatas", [[]])[0]
        rag_sources = [{"content": d, "metadata": m} for d, m in zip(rag_docs, rag_metas)]

        sources_block = "\n\n".join(
            f"[{i+1}] ({s['metadata'].get('source','')} — {s['metadata'].get('code','')}): {s['content']}"
            for i, s in enumerate(rag_sources)
        )

        lang = LANG_INSTRUCT.get(req.language, LANG_INSTRUCT["de"])
        allowed_str = ", ".join(ctx["allowed_conditions"])
        forbidden_str = ", ".join(ctx["forbidden_terms"]) if ctx["forbidden_terms"] else "(keine Einschränkungen)"
        user_prompt = f"""{lang}

Du analysierst ein Bild der Region: **{ctx['label_de'].upper()}** ({body_part}).
Detektion: {detection['method']} (Konfidenz {detection['confidence']:.2f}).

KONZENTRIERE DICH AUSSCHLIESSLICH AUF PATHOLOGIEN, DIE ZUR ANGEGEBENEN REGION PASSEN:
Wahrscheinliche Diagnosen: {allowed_str}
NICHT ERLAUBT (anatomisch ausgeschlossen): {forbidden_str}

BILDGEBENDE BEFUNDE (automatisch extrahiert via OpenCV):
{findings_text}

PATIENTENKONTEXT:
{req.patient_context or '(nicht angegeben)'}

RELEVANTE LEITLINIEN (nummeriert, bereits nach Region gefiltert):
{sources_block}

Erstelle einen strukturierten klinischen Bericht. Verwende AUSSCHLIESSLICH die Zitat-Nummern [1], [2], [3] usw.,
die exakt zu den oben gelisteten Leitlinien-Nummern passen. Verwende NIEMALS [N1], [N2], [N3] oder Platzhalter.

WICHTIG — Ausgabeformat STRIKT einhalten:
Beginne die Antwort mit ZWEI JSON-Zeilen (ohne Code-Fences), danach der narrative Bericht:

STRUCTURED_JSON: {{"findings": "kurze Befund-Zusammenfassung in 1-2 Sätzen", "urgency": "LOW|MEDIUM|HIGH", "confidence": 0.85, "red_flags": ["Liste", "von", "konkreten Warnsymptomen"], "explainability": ["Warum Urgency: Grund 1 mit Slice-Referenz", "Grund 2", "Grund 3"], "icd10": ["passende ICD-10-Codes NUR für {ctx['label_de']}"]}}
CROSS_CHECK_JSON: {{"has_contradictions": false, "contradictions": [], "confidence": "high"}}

## 1) Technische Befunde
Interpretation der numerischen Auffälligkeiten.

## 2) Differenzialdiagnosen
Plausible Ursachen mit ICD-10, wenn möglich, mit Zitaten.

## 3) Empfehlung
Weiterführende Diagnostik + Therapievorschlag mit Zitaten.

## 4) Red Flags / Warnzeichen
Wann muss ein Arzt SOFORT benachrichtigt werden.

## 5) Pflegerische Hinweise (Nursing Care Plan)
Konkrete Anweisungen für Pflegepersonal: Lagerung, Vitalzeichen-Intervalle, Warnsymptome.

## 6) Cross-Verification
Prüfe INNERE WIDERSPRÜCHE zwischen Befunden und Empfehlungen.

Regeln für urgency:
- HIGH = lebensbedrohlich / Minuten-Notfall
- MEDIUM = zeitkritisch / Stunden
- LOW = kontrollbedürftig, aber nicht akut

Beachte: Die numerische Bildanalyse ersetzt KEINE ärztliche Beurteilung — sie liefert Hinweise."""

        system = (
            f"Du bist ein klinischer Entscheidungsunterstützungsassistent, spezialisiert auf {ctx['label_de']}-Bildgebung. "
            "Zitiere Leitlinien mit numerischen Indizes [1], [2] aus dem RELEVANTE LEITLINIEN-Block. "
            "Erfinde KEINE Diagnosen außerhalb der erlaubten Liste. "
            "Gib ZUERST die geforderten JSON-Zeilen aus, DANACH den narrativen Bericht."
        )
        report_raw = await _llm_call(system, user_prompt, model=req.model, max_tokens=1600)

        # Parse structured + cross-check JSON (at the TOP of response)
        import re as _re
        import json as _json
        cross_check = {"has_contradictions": False, "contradictions": [], "confidence": "low"}
        structured = {
            "findings": "", "urgency": "UNKNOWN", "confidence": 0.0,
            "red_flags": [], "explainability": [], "icd10": [],
        }

        m_st = _re.search(r"STRUCTURED_JSON:\s*(\{.*?\})(?=\s*\n|\s*CROSS_CHECK_JSON)", report_raw, _re.DOTALL)
        m_cc = _re.search(r"CROSS_CHECK_JSON:\s*(\{.*?\})(?=\s*\n|\s*##|\Z)", report_raw, _re.DOTALL)
        if m_st:
            try:
                structured = {**structured, **_json.loads(m_st.group(1))}
            except Exception:
                pass
        if m_cc:
            try:
                cross_check = _json.loads(m_cc.group(1))
            except Exception:
                pass

        # Strip JSON lines from displayed report (regex-based — indices-safe)
        report = report_raw
        report = _re.sub(r"STRUCTURED_JSON:\s*\{.*?\}(?=\s*(?:\n|CROSS_CHECK_JSON|##|\Z))", "", report, flags=_re.DOTALL)
        report = _re.sub(r"CROSS_CHECK_JSON:\s*\{.*?\}(?=\s*(?:\n|##|\Z))", "", report, flags=_re.DOTALL)
        report = _re.sub(r"^\s*(STRUCTURED_JSON|CROSS_CHECK_JSON):.*$", "", report, flags=_re.MULTILINE)
        report = _re.sub(r"\n{3,}", "\n\n", report).strip()

        # ═══ PHASE 2: Validation Layer ═══
        validation = _validate_output_vs_body_part(structured, body_part)
        if not validation["valid"]:
            # Soft-downgrade — flag but keep the report for human review
            structured = {
                **structured,
                "urgency": "LOW" if structured.get("urgency") == "HIGH" else structured.get("urgency", "LOW"),
                "explainability": (structured.get("explainability") or [])
                + [f"⚠ Validierung fehlgeschlagen: {f}" for f in validation["flags"]],
            }
            logger.warning(f"[DICOM] {analysis_id} validation flags: {validation['flags']}")

        # ═══ PHASE 2: Confidence Gate ═══
        structured = _confidence_gate(structured)

        result_doc = {
            "report": report,
            "findings_summary": findings_text,
            "sources": [
                {
                    "index": i + 1,
                    "source": s["metadata"].get("source", ""),
                    "code": s["metadata"].get("code", ""),
                    "category": s["metadata"].get("category", ""),
                    "excerpt": s["content"][:300],
                }
                for i, s in enumerate(rag_sources)
            ],
            "cross_check": cross_check,
            "structured": structured,
            "detection": detection,
            "body_part": body_part,
            "body_part_label": ctx["label_de"],
            "validation": validation,
            "model": req.model,
            "language": req.language,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        await db.dicom_analyses.update_one(
            {"id": analysis_id, "user_id": user_id},
            {"$set": {"status": "analyzed", "analysis": result_doc, "analyze_error": None}},
        )
        logger.info(f"[DICOM] Analysis {analysis_id} completed — body_part={body_part}, urgency={structured.get('urgency')}, valid={validation['valid']}")
    except Exception as e:
        logger.error(f"[DICOM] Analysis {analysis_id} failed: {e}")
        await db.dicom_analyses.update_one(
            {"id": analysis_id, "user_id": user_id},
            {"$set": {"status": "error", "analyze_error": str(e)[:500]}},
        )


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")
    return doc


@router.get("/list/mine")
async def list_my_analyses(user: dict = Depends(get_current_user), limit: int = 50):
    """List current user's DICOM analyses — feeds longitudinal tracking."""
    docs = await db.dicom_analyses.find(
        {"user_id": user["id"]},
        {"_id": 0, "analysis.report": 0, "previews": 0, "per_slice_scores": 0},
    ).sort("created_at", -1).limit(min(limit, 100)).to_list(min(limit, 100))
    return {"items": docs, "count": len(docs)}


@router.post("/compare/{id1}/{id2}")
async def compare_analyses(id1: str, id2: str, req: CompareRequest, user: dict = Depends(get_current_user)):
    """Patient Longitudinal Tracking — produce a progression report between two scans."""
    d1 = await db.dicom_analyses.find_one({"id": id1, "user_id": user["id"]}, {"_id": 0})
    d2 = await db.dicom_analyses.find_one({"id": id2, "user_id": user["id"]}, {"_id": 0})
    if not d1 or not d2:
        raise HTTPException(status_code=404, detail="Eine oder beide Analysen nicht gefunden")

    s1 = _build_findings_summary(d1)
    s2 = _build_findings_summary(d2)

    # Numerical delta
    scores1 = [s["score"] for s in d1.get("per_slice_scores", [])]
    scores2 = [s["score"] for s in d2.get("per_slice_scores", [])]
    mean_bright_1 = np.mean([s["bright_regions"] for s in scores1]) if scores1 else 0
    mean_bright_2 = np.mean([s["bright_regions"] for s in scores2]) if scores2 else 0
    mean_dark_1 = np.mean([s["dark_regions"] for s in scores1]) if scores1 else 0
    mean_dark_2 = np.mean([s["dark_regions"] for s in scores2]) if scores2 else 0

    delta = {
        "bright_change_pct": round(((mean_bright_2 - mean_bright_1) / max(mean_bright_1, 1)) * 100, 1),
        "dark_change_pct": round(((mean_dark_2 - mean_dark_1) / max(mean_dark_1, 1)) * 100, 1),
        "slice_count_change": len(scores2) - len(scores1),
        "days_between": (
            datetime.fromisoformat(d2["created_at"].replace("Z", "+00:00"))
            - datetime.fromisoformat(d1["created_at"].replace("Z", "+00:00"))
        ).days,
    }

    lang = LANG_INSTRUCT.get(req.language, LANG_INSTRUCT["de"])
    prompt = f"""{lang}

Vergleiche zwei aufeinanderfolgende bildgebende Untersuchungen desselben Patienten und erstelle einen Verlaufsbericht.

BEFUND 1 ({d1.get('created_at','')[:10]}):
{s1}

BEFUND 2 ({d2.get('created_at','')[:10]}):
{s2}

NUMERISCHE VERÄNDERUNG (Befund 2 vs. 1):
- Hyperdense Regionen: {delta['bright_change_pct']:+.1f} %
- Hypodense Regionen:  {delta['dark_change_pct']:+.1f} %
- Schichtanzahl: {delta['slice_count_change']:+d}
- Zeitraum: {delta['days_between']} Tage

Bitte verfasse:
1) **Progressionsbewertung** — Verbesserung / Stagnation / Verschlechterung mit Quantifizierung
2) **Klinische Interpretation** — was bedeutet die Veränderung medizinisch?
3) **Empfehlung** — nächste Schritte
4) **Vergleich zur erwarteten Heilungskurve** (falls anwendbar)"""

    system = "Du bist ein klinischer Verlaufs-Analyst. Interpretiere Veränderungen quantitativ und klinisch."
    progression_report = await _llm_call(system, prompt, model=req.model, max_tokens=1000)

    return {
        "id1": id1,
        "id2": id2,
        "delta": delta,
        "progression_report": progression_report,
        "language": req.language,
    }


# ═══════════════════════ PDF REPORT + TIMELINE ═══════════════════════

@router.get("/report-pdf/{analysis_id}")
async def download_report_pdf(analysis_id: str, user: dict = Depends(get_current_user)):
    """Download the clinical report as a styled PDF (fpdf2, Unicode-ready)."""
    from fastapi.responses import StreamingResponse
    from fpdf import FPDF

    doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")
    if doc.get("status") != "analyzed":
        raise HTTPException(status_code=400, detail="Analyse noch nicht abgeschlossen")

    analysis = doc.get("analysis", {})
    structured = analysis.get("structured", {})
    header = doc.get("header", {})

    # Use a Unicode font (DejaVu already in /app/backend/fonts)
    font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    font_regular = os.path.join(font_dir, "DejaVuSans.ttf")
    font_bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")

    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(font_regular):
        pdf.add_font("DejaVu", "", font_regular)
        pdf.set_font("DejaVu", size=11)
        has_bold = os.path.exists(font_bold)
        if has_bold:
            pdf.add_font("DejaVu", "B", font_bold)
    else:
        pdf.set_font("Helvetica", size=11)
        has_bold = True

    def _font(bold=False, size=11):
        if os.path.exists(font_regular):
            pdf.set_font("DejaVu", "B" if (bold and has_bold) else "", size)
        else:
            pdf.set_font("Helvetica", "B" if bold else "", size)

    # Header
    _font(bold=True, size=16)
    pdf.set_text_color(201, 168, 76)  # amber/gold
    pdf.cell(0, 10, "Prep Academy - DICOM Klinischer Bericht", ln=True)
    pdf.set_text_color(0, 0, 0)
    _font(size=9)
    pdf.cell(0, 6, f"Analyse-ID: {analysis_id}", ln=True)
    pdf.cell(0, 6, f"Erstellt: {analysis.get('analyzed_at','')[:19]}  |  Modell: {analysis.get('model','')}", ln=True)
    pdf.ln(4)

    # Patient / Study meta
    _font(bold=True, size=12)
    pdf.cell(0, 8, "Untersuchungsdetails", ln=True)
    _font(size=10)
    for label, val in [
        ("Modalität", header.get("modality", "-")),
        ("Körperregion", header.get("body_part") or header.get("study_description", "-")),
        ("Patient", f"{header.get('patient_age','-')} / {header.get('patient_sex','-')}"),
        ("Label", doc.get("patient_label", "-")),
        ("Schichten gesamt", str(doc.get("total_slices", "-"))),
        ("Schichten analysiert", str(len(doc.get("selected_indices", [])))),
    ]:
        pdf.cell(50, 6, f"{label}:")
        pdf.cell(0, 6, str(val), ln=True)
    pdf.ln(3)

    # Urgency banner
    urgency = (structured.get("urgency") or "UNKNOWN").upper()
    urgency_colors = {"HIGH": (220, 38, 38), "MEDIUM": (245, 158, 11), "LOW": (34, 197, 94), "UNKNOWN": (120, 120, 120)}
    pdf.set_fill_color(*urgency_colors.get(urgency, urgency_colors["UNKNOWN"]))
    pdf.set_text_color(255, 255, 255)
    _font(bold=True, size=12)
    conf = structured.get("confidence", 0)
    pdf.cell(0, 9, f"Dringlichkeit: {urgency}   |   Confidence: {conf:.0%}" if isinstance(conf, (int, float)) else f"Dringlichkeit: {urgency}", ln=True, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # Red flags
    rf = structured.get("red_flags", [])
    if rf:
        _font(bold=True, size=11)
        pdf.set_text_color(185, 28, 28)
        pdf.cell(0, 7, "Red Flags / Warnzeichen", ln=True)
        pdf.set_text_color(0, 0, 0)
        _font(size=10)
        for r in rf[:10]:
            pdf.multi_cell(0, 5, f"- {r}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Explainability
    expl = structured.get("explainability", [])
    if expl:
        _font(bold=True, size=11)
        pdf.cell(0, 7, "Begruendung (Explainability)", ln=True)
        _font(size=10)
        for e in expl[:8]:
            pdf.multi_cell(0, 5, f"- {e}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Full report
    _font(bold=True, size=12)
    pdf.cell(0, 8, "Vollstaendiger Befundbericht", ln=True)
    _font(size=10)
    report_text = (analysis.get("report", "") or "").replace("**", "")
    for line in report_text.split("\n"):
        if line.strip():
            pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(2)
    pdf.ln(3)

    # Sources
    _font(bold=True, size=11)
    pdf.cell(0, 7, "Quellen", ln=True)
    _font(size=9)
    for s in analysis.get("sources", []):
        pdf.multi_cell(0, 4, f"[{s['index']}] {s.get('source','')} ({s.get('code','')})", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, s.get("excerpt", "")[:250], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # Footer
    pdf.ln(4)
    _font(size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4, "HAFTUNGSAUSSCHLUSS: Dieser KI-generierte Bericht dient ausschliesslich der Unterstuetzung und ersetzt keine aerztliche Beurteilung. Finale diagnostische und therapeutische Entscheidungen muessen durch qualifiziertes medizinisches Fachpersonal erfolgen.", new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    filename = f"dicom_report_{analysis_id[:8]}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timeline/{patient_label}")
async def patient_timeline(patient_label: str, user: dict = Depends(get_current_user)):
    """Hospital Mode: aggregate all scans for a patient label, ordered chronologically."""
    docs = await db.dicom_analyses.find(
        {"user_id": user["id"], "patient_label": patient_label},
        {"_id": 0, "previews": 0, "per_slice_scores": 0, "analysis.report": 0, "analysis.findings_summary": 0},
    ).sort("created_at", 1).to_list(200)

    timeline = []
    for d in docs:
        a = d.get("analysis", {}) or {}
        st = a.get("structured", {}) or {}
        timeline.append({
            "id": d["id"],
            "date": d.get("created_at", "")[:10],
            "modality": d.get("header", {}).get("modality", ""),
            "body_part": d.get("header", {}).get("body_part", ""),
            "total_slices": d.get("total_slices", 0),
            "status": d.get("status", ""),
            "urgency": st.get("urgency", "UNKNOWN"),
            "confidence": st.get("confidence", 0),
            "icd10": st.get("icd10", []),
            "summary": st.get("findings", ""),
        })

    # Simple trend summary — counts per urgency
    urgency_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for item in timeline:
        urgency_counts[item["urgency"]] = urgency_counts.get(item["urgency"], 0) + 1

    return {
        "patient_label": patient_label,
        "scan_count": len(timeline),
        "timeline": timeline,
        "urgency_summary": urgency_counts,
    }
