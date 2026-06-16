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
  GET  /list/mine            lists the user's past analyses
  POST /compare/{id1}/{id2} Patient Longitudinal Tracking — diff between two scans
  GET  /report-pdf/{id}     download clinical report as PDF
  GET  /timeline/{label}    Hospital Mode: aggregate all scans for a patient label
  POST /review/{id}         Human review queue — submit radiologist feedback
  GET  /review              List all items pending human review (admin)
  POST /feedback/{id}       Radiologist feedback loop — correct / validate AI output
  GET  /export-sr/{id}      DICOM Structured Report export
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import io
import base64
import uuid
import zipfile
import asyncio
import json
from datetime import datetime, timezone, timedelta
from uuid import UUID

import numpy as np
import pydicom
import cv2
from services.retrieval_orchestrator import RetrievalRequest, retrieve as unified_retrieve

try:
    import SimpleITK as sitk
    _SITK_AVAILABLE = True
except ImportError:
    sitk = None
    _SITK_AVAILABLE = False

from database import db, logger
from auth import get_current_user, get_admin_user
from routes.rag import _ensure_initialized, _embed_texts, _llm_call, LANG_INSTRUCT
from routes import rag as rag_module
from limiter import limiter

router = APIRouter(prefix="/api/dicom", tags=["dicom"])

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
MAX_UPLOAD_SIZE_MB = int(os.environ.get("DICOM_MAX_UPLOAD_MB", "200"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".dcm", ".zip"}
PHI_TAGS_TO_STRIP = {
    # Patient identification
    0x00100010,  # PatientName
    0x00100020,  # PatientID
    0x00100021,  # IssuerOfPatientID
    0x00100030,  # PatientBirthDate
    0x00100032,  # PatientBirthTime
    0x00100040,  # PatientSex
    0x00100050,  # PatientInsurancePlanCodeSequence
    0x00101000,  # OtherPatientIDs
    0x00101001,  # OtherPatientNames
    0x00101002,  # OtherPatientIDsSequence
    0x00101005,  # PatientBirthName
    0x00101010,  # PatientAge (keep for clinical use)
    0x00101040,  # PatientAddress
    0x00101050,  # InsurancePlanIdentification
    0x00101060,  # PatientMotherBirthName
    0x00101080,  # MilitaryRank
    0x00101081,  # BranchOfService
    0x00101090,  # MedicalRecordLocator
    0x00102000,  # MedicalAlerts
    0x00102150,  # CountryOfResidence
    0x00102152,  # RegionOfResidence
    0x00102154,  # PatientTelephoneNumbers
    0x00102160,  # EthnicGroup
    0x00104000,  # PatientComments
    # Study/Institution identification
    0x00080050,  # AccessionNumber
    0x00080080,  # InstitutionName
    0x00080081,  # InstitutionAddress
    0x00080090,  # ReferringPhysicianName
    0x00080092,  # ReferringPhysicianAddress
    0x00080094,  # ReferringPhysicianTelephoneNumbers
    0x00080096,  # ReferringPhysicianIdentificationSequence
    0x00081048,  # Physician(s)OfRecord
    0x00081050,  # PerformingPhysicianName
    0x00081060,  # NameOfPhysician(s)ReadingStudy
    0x00081070,  # OperatorsName
    0x00081080,  # AdmittingDiagnosesDescription
    0x00081084,  # AdmittingDiagnosesCodeSequence
    0x00081090,  # ManufacturerModelName
    # Device identification
    0x00181000,  # DeviceSerialNumber
    0x00181020,  # SoftwareVersion(s)
    0x00181030,  # ProtocolName
    0x00181040,  # ContrastBolusRoute
    0x00181050,  # SpatialResolution
    0x00181060,  # TriggerTime
    0x00181070,  # NominalInterval
    0x00181080,  # BeatRejectionFlag
    0x00181090,  # CardiacNumberOfImages
    0x00181100,  # TriggerWindow
    0x00181110,  # ReconstructionDiameter
    0x00181120,  # DistanceSourceToDetector
    0x00181130,  # DistanceSourceToPatient
    0x00181140,  # EstimatedRadiographicMagnificationFactor
    0x00181150,  # ExposureTime
    0x00181160,  # XRayTubeCurrent
    0x00181170,  # Exposure
    0x00181180,  # ExposureInuAs
    0x00181190,  # FocalSpot
}

# ═══════════════════════════════════════════════════════════════
# HELPER: Audit Log
# ═══════════════════════════════════════════════════════════════

async def _audit_log(action: str, actor_id: str, target_id: str, details: dict = None):
    """Write an immutable audit trail entry."""
    try:
        await db.audit_logs.insert_one({
            "action": action,
            "actor_id": actor_id,
            "target_id": target_id,
            "target_type": "dicom_analysis",
            "details": details or {},
            "ip": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"[AUDIT] Failed to write log: {e}")

# ═══════════════════════════════════════════════════════════════
# HELPER: AES-256 encrypted storage for DICOM files
# ═══════════════════════════════════════════════════════════════

_ENCRYPT_STORAGE = bool(os.environ.get("DICOM_ENCRYPTION_KEY"))
_STORE_RAW_DICOM = (
    os.environ.get("DICOM_STORE_RAW_ENCRYPTED", "false").strip().lower() == "true"
    and _ENCRYPT_STORAGE
)

if _ENCRYPT_STORAGE:
    _raw_key = os.environ["DICOM_ENCRYPTION_KEY"].encode("utf-8")
    if len(_raw_key) < 32:
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        _DICOM_ENCRYPTION_KEY = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None,
            info=b"dicom-aes256",
        ).derive(_raw_key)
    elif len(_raw_key) == 32:
        _DICOM_ENCRYPTION_KEY = _raw_key
    else:
        raise RuntimeError(
            f"DICOM_ENCRYPTION_KEY must be ≤ 32 bytes (got {len(_raw_key)}). "
            "Set a passphrase or exactly 32 raw bytes."
        )
    del _raw_key
else:
    _DICOM_ENCRYPTION_KEY = b""

def _encrypt_bytes(data: bytes) -> bytes:
    if not _ENCRYPT_STORAGE:
        raise RuntimeError("Encryption is enabled but _encrypt_bytes called without a key")
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(_DICOM_ENCRYPTION_KEY), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    ct = encryptor.update(padded) + encryptor.finalize()
    return iv + ct

def _decrypt_bytes(data: bytes) -> bytes:
    if not _ENCRYPT_STORAGE or not _DICOM_ENCRYPTION_KEY:
        raise RuntimeError("Decryption attempted but encryption is not configured")
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    iv = data[:16]
    ct = data[16:]
    cipher = Cipher(algorithms.AES(_DICOM_ENCRYPTION_KEY), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

# ═══════════════════════════════════════════════════════════════
# HELPERS — DICOM parsing
# ═══════════════════════════════════════════════════════════════

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


def _read_dicoms_sitk(dicom_bytes_list: List[bytes]) -> Optional[List[Dict[str, Any]]]:
    """Try reading a multi-file DICOM series via SimpleITK for better spatial metadata."""
    if not _SITK_AVAILABLE:
        return None
    import tempfile
    import os as _os
    tmpdir = tempfile.mkdtemp(prefix="sitk_")
    try:
        paths = []
        for i, data in enumerate(dicom_bytes_list):
            p = _os.path.join(tmpdir, f"img_{i:04d}.dcm")
            with open(p, "wb") as f:
                f.write(data)
            paths.append(p)
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(tmpdir)
        if not series_ids:
            return None
        reader.SetFileNames(reader.GetGDCMSeriesFileNames(tmpdir, series_ids[0]))
        reader.MetaDataDictionaryArrayUpdateOn()
        reader.LoadPrivateTagsOn()
        vol = reader.Execute()
        slices = []
        for i in range(vol.GetSize()[2]):
            arr = sitk.GetArrayFromImage(vol[:, :, i])
            ds = pydicom.dcmread(paths[i], force=True)
            origin = vol.GetOrigin()
            spacing = vol.GetSpacing()
            direction = vol.GetDirection()
            slices.append({
                "name": _os.path.basename(paths[i]),
                "ds": ds,
                "pixels": arr,
                "instance": int(getattr(ds, "InstanceNumber", 0) or 0),
                "sitk_origin": list(origin),
                "sitk_spacing": list(spacing),
                "sitk_direction": list(direction),
            })
        slices.sort(key=lambda s: s["instance"])
        return slices
    except Exception as e:
        logger.debug(f"[DICOM] SimpleITK series read failed, falling back: {e}")
        return None
    finally:
        import shutil
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


def _read_dicoms_from_bytes(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Accepts a single .dcm or a .zip bundle of .dcm files. Returns ordered slice dicts."""
    slices: List[Dict[str, Any]] = []

    def _parse_one(data: bytes, name: str):
        try:
            ds = pydicom.dcmread(io.BytesIO(data), force=True)
            if not hasattr(ds, "pixel_array"):
                return
            px = ds.pixel_array
            if px.ndim >= 3 and px.shape[-1] == 3:
                px = cv2.cvtColor(px.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            if px.ndim == 3:
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
        dcm_files = []
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            dcm_names = sorted(n for n in z.namelist() if n.lower().endswith(".dcm") and not n.startswith("__MACOSX"))
            dcm_files = [z.read(n) for n in dcm_names]
        sitk_result = _read_dicoms_sitk(dcm_files) if len(dcm_files) > 1 else None
        if sitk_result:
            return sitk_result
        for n, data in zip(dcm_names, dcm_files):
            _parse_one(data, os.path.basename(n))
    else:
        sitk_result = _read_dicoms_sitk([file_bytes])
        if sitk_result:
            return sitk_result
        _parse_one(file_bytes, filename)

    slices.sort(key=lambda s: s["instance"])
    return slices


def _strip_phi(ds: pydicom.Dataset) -> pydicom.Dataset:
    """Remove all PHI tags from a DICOM dataset."""
    for tag in PHI_TAGS_TO_STRIP:
        try:
            if tag in ds:
                del ds[tag]
        except Exception:
            pass
    # Also clear the meta-header info that may leak PHI
    if hasattr(ds, "file_meta"):
        for meta_tag in [0x00020003, 0x00020010, 0x00020016]:
            try:
                if meta_tag in ds.file_meta:
                    del ds.file_meta[meta_tag]
            except Exception:
                pass
    return ds


def _score_slice(img8: np.ndarray, window_preset: str = "standard") -> Dict[str, float]:
    """Per-slice feature extraction with multiple window presets."""
    if window_preset == "bone":
        _, thr = cv2.threshold(img8, 200, 255, cv2.THRESH_BINARY)
    elif window_preset == "lung":
        img8_proc = np.clip(img8.astype(np.float32) * 1.5, 0, 255).astype(np.uint8)
        _, thr = cv2.threshold(img8_proc, 80, 255, cv2.THRESH_BINARY)
    else:
        img8_proc = img8

    edges = cv2.Canny(img8, 50, 150)
    edge_density = float(edges.sum()) / (img8.size * 255)
    variance = float(img8.var())
    hist, _ = np.histogram(img8.ravel(), bins=256, range=(0, 256))
    p = hist / max(hist.sum(), 1)
    entropy = float(-np.sum(p[p > 0] * np.log2(p[p > 0])))
    _, thr_bright = cv2.threshold(img8, 160, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thr_bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_bright_regions = sum(1 for c in contours if cv2.contourArea(c) > 150)
    _, thr_dark = cv2.threshold(img8, 40, 255, cv2.THRESH_BINARY_INV)
    contours_d, _ = cv2.findContours(thr_dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_dark_regions = sum(1 for c in contours_d if cv2.contourArea(c) > 200)

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


# ═══════════════════════════════════════════════════════════════
# QUALITY GATE (upload-time)
# ═══════════════════════════════════════════════════════════════

_SECONDARY_CAPTURE_MODALITIES = {"OT", "SC", "PR", "KO", "SR"}
_SINGLE_SLICE_OK_MODALITIES = {"CR", "DX", "MG", "XA", "RF", "US", "ES"}
MIN_SLICES_FOR_CROSS_SECTIONAL = 5


def _check_quality_gate(slices: List[Dict]) -> Dict[str, Any]:
    """Validate uploaded DICOM meets diagnostic quality requirements."""
    if not slices:
        return {"valid": False, "reason": "Keine gültigen DICOM-Schichten gefunden", "action": "Gültige .dcm-Datei oder ZIP hochladen", "code": "no_slices"}

    first = slices[0]
    ds = first["ds"]
    modality = str(getattr(ds, "Modality", "") or "").upper()
    sop_class = str(getattr(ds, "SOPClassUID", "") or "")

    if modality in _SECONDARY_CAPTURE_MODALITIES:
        return {
            "valid": False,
            "reason": f"Modalität '{modality}' ist kein diagnostischer Original-Scan (Secondary Capture).",
            "action": "Bitte Original-Bildgebung direkt vom Gerät hochladen (CT/MR/CR/DX/US).",
            "code": "secondary_capture",
        }

    if "secondary" in sop_class.lower() or sop_class == "1.2.840.10008.5.1.4.1.1.7":
        return {
            "valid": False,
            "reason": "SOP Class UID zeigt Secondary Capture Image — kein diagnostisches Bild.",
            "action": "Bitte Original-Scan hochladen.",
            "code": "secondary_capture_sop",
        }

    if modality in ("CT", "MR", "PT", "NM") and len(slices) < MIN_SLICES_FOR_CROSS_SECTIONAL:
        return {
            "valid": False,
            "reason": f"Nur {len(slices)} Schicht(en) für {modality} — mindestens {MIN_SLICES_FOR_CROSS_SECTIONAL} erforderlich für verlässliche Diagnostik.",
            "action": "Komplette Serie (als ZIP) hochladen, nicht einzelne Schichten.",
            "code": "insufficient_slices",
        }

    if not modality:
        return {
            "valid": True,
            "reason": None,
            "action": None,
            "code": "modality_missing",
            "warning": "Modalität nicht angegeben — automatische Körperregion-Erkennung könnte scheitern.",
        }

    return {"valid": True, "reason": None, "action": None, "code": "ok"}


def _select_top_slices(slices: List[Dict], top_k: int = 8, window_preset: str = "standard") -> List[int]:
    """Return indices of top-K slices by saliency score, with optional window preset."""
    ranked = sorted(range(len(slices)), key=lambda i: slices[i]["score"]["saliency"], reverse=True)
    return ranked[: min(top_k, len(slices))]


# ═══════════════════════════════════════════════════════════════
# BODY-PART CONTEXT
# ═══════════════════════════════════════════════════════════════

BODY_PART_CONTEXT: Dict[str, Dict[str, Any]] = {
    "chest": {
        "allowed_conditions": [
            "Pneumonie", "Pneumothorax", "Hämatothorax", "Pleuraerguss", "Lungenembolie",
            "Lungenkarzinom", "COPD-Exazerbation", "ARDS", "Rippenfraktur", "Mediastinalverschiebung",
        ],
        "rag_categories": ["Pneumologie", "Notfallmedizin", "Kardiologie", "Chirurgie"],
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

_BODY_KEYWORDS = [
    ("chest", ["chest", "thorax", "thora", "lung", "pulmon", "pleura", "mediastin", "cardiac", "heart"]),
    ("brain", ["brain", "head", "cerebr", "crani", "kopf", "schädel", "neuro", "ct-schädel"]),
    ("abdomen", ["abdomen", "abdom", "liver", "leber", "pancrea", "kidney", "niere", "gastro", "hepat"]),
    ("pelvis", ["pelvis", "becken", "bladder", "blase", "sacrum", "hip"]),
    ("spine", ["spine", "wirbel", "lumbar", "cervic", "thoracic spine", "ls-spine"]),
    ("limb", ["limb", "extrem", "foot", "ankle", "knee", "hand", "arm", "leg", "bein", "hand", "femur", "tibia", "fibula", "humerus", "radius", "ulna"]),
]


def _detect_body_part(header: Dict[str, Any], sample_shape: Optional[tuple] = None) -> Dict[str, Any]:
    bp_raw = (header.get("body_part") or "").strip().lower()
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

    blob = " ".join([
        bp_raw,
        (header.get("study_description") or "").lower(),
        (header.get("series_description") or "").lower(),
    ])
    for body, kws in _BODY_KEYWORDS:
        if any(k in blob for k in kws):
            return {"body_part": body, "method": "keyword_match", "confidence": 0.85}

    if sample_shape and len(sample_shape) >= 2:
        h, w = sample_shape[:2]
        if w > 0:
            ratio = h / w
            if ratio > 1.4:
                return {"body_part": "limb", "method": "aspect_heuristic", "confidence": 0.55}

    return {"body_part": "unknown", "method": "fallback", "confidence": 0.3}


def _validate_output_vs_body_part(structured: Dict[str, Any], body_part: str) -> Dict[str, Any]:
    ctx = BODY_PART_CONTEXT.get(body_part, BODY_PART_CONTEXT["unknown"])
    flags = []

    findings_blob = " ".join([
        str(structured.get("findings", "")).lower(),
        " ".join(structured.get("red_flags", [])).lower(),
        " ".join(structured.get("explainability", [])).lower(),
        " ".join(structured.get("differential_diagnoses", [{}])[0].get("diagnosis", "") if isinstance(structured.get("differential_diagnoses"), list) and structured.get("differential_diagnoses") else "").lower(),
    ])
    for term in ctx.get("forbidden_terms", []):
        if term.lower() in findings_blob:
            flags.append(f"Forbidden term '{term}' detected for body_part={body_part}")

    prefixes = ctx.get("icd10_prefixes", ())
    if prefixes:
        for code in structured.get("icd10", []) or []:
            if not any(str(code).upper().startswith(p) for p in prefixes):
                flags.append(f"ICD-10 '{code}' not typical for body_part={body_part}")

    return {"valid": len(flags) == 0, "flags": flags}


def _confidence_gate(structured: Dict[str, Any], min_conf: float = 0.5) -> Dict[str, Any]:
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


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    patient_context: str = ""
    language: str = "de"
    top_k: int = 8
    model: str = "openai/gpt-oss-120b:free"
    body_part_override: Optional[str] = None
    window_preset: str = "standard"


class CompareRequest(BaseModel):
    language: str = "de"
    model: str = "openai/gpt-oss-120b:free"


class FeedbackRequest(BaseModel):
    feedback_text: str
    correct_urgency: Optional[str] = None
    correct_icd10: Optional[List[str]] = None
    rating: Optional[int] = None


class DICOMSRExportRequest(BaseModel):
    include_pixel_data: bool = True


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_dicom(
    request: Request,
    file: UploadFile = File(...),
    patient_label: Optional[str] = Form(None),
    window_preset: str = Form("standard"),
    user: dict = Depends(get_current_user),
):
    """Upload .dcm or .zip and run smart sampling. Returns analysis_id + previews."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Leere Datei")

    # File size validation
    if len(raw) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu groß ({len(raw) / 1024 / 1024:.1f} MB). Maximum: {MAX_UPLOAD_SIZE_MB} MB.",
        )

    # File type validation
    ext = os.path.splitext(file.filename or "upload.dcm")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp '{ext}' nicht erlaubt. Erlaubt: .dcm, .zip",
        )

    # DICOM magic bytes check for .dcm files
    if ext == ".dcm" and len(raw) >= 4:
        dicom_prefix = raw[:4]
        if dicom_prefix not in (b"DICM", bytes([0, 0, 0, 0])):
            raise HTTPException(
                status_code=400,
                detail="Datei hat keine gültige DICOM-Signatur. Bitte eine gültige .dcm-Datei hochladen.",
            )

    loop = asyncio.get_event_loop()
    slices = await loop.run_in_executor(None, lambda: _read_dicoms_from_bytes(raw, file.filename or "upload.dcm"))
    if not slices:
        await _audit_log("dicom_upload_failed", user["id"], file.filename or "?", {"reason": "no_valid_slices"})
        raise HTTPException(status_code=400, detail="Keine gültigen DICOM-Schichten gefunden")

    gate = _check_quality_gate(slices)
    if not gate["valid"]:
        await _audit_log("dicom_upload_rejected", user["id"], file.filename or "?", {"code": gate["code"], "reason": gate["reason"]})
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

    for s in slices:
        img8 = _apply_windowing(s["pixels"], s["ds"])
        score = _score_slice(img8, window_preset)
        s["img8"] = img8
        s["score"] = score

    selected_idx = _select_top_slices(slices, top_k=8, window_preset=window_preset)
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

    analysis_id = str(uuid.uuid4())
    header = _extract_dicom_header(slices[0]["ds"]) if slices else {}
    per_slice_compact = [
        {"index": i, "name": s["name"], "instance": s["instance"], "score": s["score"]}
        for i, s in enumerate(slices)
    ]

    # Raw DICOM persistence is disabled by default to avoid storing PHI-heavy
    # imaging payloads in MongoDB. Enable only with explicit encrypted storage.
    encrypted_data = _encrypt_bytes(raw) if _STORE_RAW_DICOM else None

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
        "window_preset": window_preset,
        "encrypted_data": encrypted_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await _audit_log("dicom_upload", user["id"], analysis_id, {
        "filename": file.filename,
        "total_slices": len(slices),
        "modality": header.get("modality"),
    })

    return {
        "analysis_id": analysis_id,
        "filename": file.filename,
        "total_slices": len(slices),
        "selected_count": len(selected_idx),
        "header": header,
        "previews": previews,
        "quality_warning": gate.get("warning"),
        "encryption_enabled": _ENCRYPT_STORAGE,
        "raw_storage_enabled": _STORE_RAW_DICOM,
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

    if doc.get("status") == "analyzing":
        return {"analysis_id": analysis_id, "status": "analyzing", "message": "Analyse läuft bereits"}

    await db.dicom_analyses.update_one(
        {"id": analysis_id, "user_id": user["id"]},
        {"$set": {"status": "analyzing", "analyze_error": None, "analyze_started_at": datetime.now(timezone.utc).isoformat()}},
    )

    await _audit_log("dicom_analyze_started", user["id"], analysis_id, {"model": req.model, "language": req.language})
    asyncio.create_task(_run_analysis_job(analysis_id, user["id"], req))

    return {"analysis_id": analysis_id, "status": "analyzing", "message": "Analyse gestartet; bitte Status pollen"}


async def _llm_call_with_retry(system: str, user_prompt: str, model: str = "openai/gpt-oss-120b:free", max_tokens: int = 1600, max_retries: int = 2) -> str:
    """Call LLM with automatic retry on transient failures."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await _llm_call(system, user_prompt, model=model, max_tokens=max_tokens)
        except HTTPException as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"[DICOM] LLM call attempt {attempt + 1} failed, retrying in {wait}s: {e.detail}")
                await asyncio.sleep(wait)
            else:
                raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"[DICOM] LLM call attempt {attempt + 1} failed with unexpected error, retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                raise
    raise last_error or HTTPException(status_code=503, detail="LLM-Aufruf nach mehreren Versuchen fehlgeschlagen")


async def _run_analysis_job(analysis_id: str, user_id: str, req: "AnalyzeRequest"):
    """Background worker: runs Context-Aware RAG+DeepSeek and writes result to MongoDB."""
    import re as _re
    import json as _json

    try:
        doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user_id}, {"_id": 0})
        if not doc:
            return

        header = doc.get("header", {})
        sample_shape = (header.get("rows", 0), header.get("columns", 0))
        detection = _detect_body_part(header, sample_shape)

        override = (req.body_part_override or "").strip().lower()
        if override and override in BODY_PART_CONTEXT:
            detection = {"body_part": override, "method": "manual_override", "confidence": 1.0}

        body_part = detection["body_part"]

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

        focus_conditions = ", ".join(ctx["allowed_conditions"][:6])
        query = f"{ctx['label_de']} {header.get('modality','')} {req.patient_context} {focus_conditions}".strip()
        retrieval = await unified_retrieve(RetrievalRequest(
            query=query,
            top_k=max(1, min(req.top_k, 8)),
            use_hybrid=True,
            use_reranker=True,
        ))
        rag_sources = [
            {
                "content": s.get("excerpt", ""),
                "metadata": {
                    "source": s.get("source", ""),
                    "code": "",
                    "category": s.get("category", ""),
                    "note_title": s.get("note_title", ""),
                    "vault_path": s.get("vault_path", ""),
                },
            }
            for s in retrieval.get("sources", [])
        ]

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
Beginne die Antwort mit DREI JSON-Zeilen (ohne Code-Fences), danach der narrative Bericht:

STRUCTURED_JSON: {{"findings": "kurze Befund-Zusammenfassung in 1-2 Sätzen", "urgency": "LOW|MEDIUM|HIGH", "confidence": 0.85, "red_flags": ["Liste", "von", "konkreten Warnsymptomen"], "explainability": ["Warum Urgency: Grund 1 mit Slice-Referenz", "Grund 2", "Grund 3"], "icd10": ["passende ICD-10-Codes NUR für {ctx['label_de']}"]}}
DIFFERENTIAL_JSON: {{"diagnoses": [{{"diagnosis": "Diagnose 1", "probability": "hoch", "icd10": "Code1", "rationale": "Begründung mit Zitat [N]"}}, {{"diagnosis": "Diagnose 2", "probability": "mittel", "icd10": "Code2", "rationale": "Begründung mit Zitat [N]"}}]}}
CROSS_CHECK_JSON: {{"has_contradictions": false, "contradictions": [], "confidence": "high"}}

## 1) Technische Befunde
Interpretation der numerischen Auffälligkeiten.

## 2) Differenzialdiagnosen (RANGLISTE — wahrscheinlichste zuerst)
Jede mit ICD-10, Wahrscheinlichkeit, Begründung und Zitat.

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

        # Use retry-aware LLM call
        report_raw = await _llm_call_with_retry(system, user_prompt, model=req.model, max_tokens=1600)

        cross_check = {"has_contradictions": False, "contradictions": [], "confidence": "low"}
        structured = {
            "findings": "", "urgency": "UNKNOWN", "confidence": 0.0,
            "red_flags": [], "explainability": [], "icd10": [],
        }
        differential = {"diagnoses": []}

        m_st = _re.search(r"STRUCTURED_JSON:\s*(\{.*?\})(?=\s*\n|\s*DIFFERENTIAL_JSON|\s*CROSS_CHECK_JSON)", report_raw, _re.DOTALL)
        m_dd = _re.search(r"DIFFERENTIAL_JSON:\s*(\{.*?\})(?=\s*\n|\s*CROSS_CHECK_JSON|\Z)", report_raw, _re.DOTALL)
        m_cc = _re.search(r"CROSS_CHECK_JSON:\s*(\{.*?\})(?=\s*\n|\s*##|\Z)", report_raw, _re.DOTALL)

        if m_st:
            try:
                structured = {**structured, **_json.loads(m_st.group(1))}
            except Exception:
                pass
        if m_dd:
            try:
                differential = _json.loads(m_dd.group(1))
                if isinstance(differential, dict) and "diagnoses" in differential:
                    # Sort diagnoses by probability (hoch > mittel > niedrig)
                    prob_order = {"hoch": 0, "mittel": 1, "niedrig": 2, "low": 2, "medium": 1, "high": 0}
                    differential["diagnoses"].sort(key=lambda d: prob_order.get(d.get("probability", "").lower(), 99))
            except Exception:
                pass
        if m_cc:
            try:
                cross_check = _json.loads(m_cc.group(1))
            except Exception:
                pass

        report = report_raw
        report = _re.sub(r"STRUCTURED_JSON:\s*\{.*?\}(?=\s*(?:\n|DIFFERENTIAL_JSON|CROSS_CHECK_JSON|##|\Z))", "", report, flags=_re.DOTALL)
        report = _re.sub(r"DIFFERENTIAL_JSON:\s*\{.*?\}(?=\s*(?:\n|CROSS_CHECK_JSON|##|\Z))", "", report, flags=_re.DOTALL)
        report = _re.sub(r"CROSS_CHECK_JSON:\s*\{.*?\}(?=\s*(?:\n|##|\Z))", "", report, flags=_re.DOTALL)
        report = _re.sub(r"^\s*(STRUCTURED_JSON|DIFFERENTIAL_JSON|CROSS_CHECK_JSON):.*$", "", report, flags=_re.MULTILINE)
        report = _re.sub(r"\n{3,}", "\n\n", report).strip()

        validation = _validate_output_vs_body_part(structured, body_part)
        if not validation["valid"]:
            structured = {
                **structured,
                "urgency": "LOW" if structured.get("urgency") == "HIGH" else structured.get("urgency", "LOW"),
                "explainability": (structured.get("explainability") or [])
                + [f"⚠ Validierung fehlgeschlagen: {f}" for f in validation["flags"]],
            }
            logger.warning(f"[DICOM] {analysis_id} validation flags: {validation['flags']}")

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
            "differential_diagnoses": differential.get("diagnoses", []),
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

        # High Urgency Alerting — real email + in-app notification
        urgency = structured.get("urgency", "UNKNOWN")
        if urgency == "HIGH":
            logger.warning(f"[DICOM] HIGH urgency alert for analysis {analysis_id}")
            await _audit_log("dicom_high_urgency", user_id, analysis_id, {
                "urgency": urgency,
                "confidence": structured.get("confidence"),
                "findings": structured.get("findings", "")[:200],
            })
            try:
                await db.high_urgency_alerts.insert_one({
                    "analysis_id": analysis_id,
                    "user_id": user_id,
                    "urgency": "HIGH",
                    "findings_preview": structured.get("findings", "")[:300],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "acknowledged": False,
                    "notified_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.error(f"[DICOM] Failed to create high urgency alert: {e}")

            # Real email notification
            try:
                from services.email_service import send_dicom_high_urgency_email
                user_doc = await db.users.find_one({"id": user_id}, {"email": 1, "name": 1})
                if user_doc:
                    asyncio.create_task(send_dicom_high_urgency_email(
                        user=user_doc,
                        analysis_id=analysis_id,
                        findings=structured.get("findings", ""),
                        body_part=body_part,
                        confidence=structured.get("confidence", 0.0),
                    ))
            except Exception as e:
                logger.error(f"[DICOM] Failed to send HIGH urgency email: {e}")

            # In-app notification
            try:
                from services.notification_service import create_notification
                asyncio.create_task(create_notification(
                    user_id=user_id,
                    notification_type="dicom_high_urgency",
                    title="🚨 HIGH Urgency Befund",
                    message=f"Potentiell lebensbedrohlicher Befund in {ctx['label_de']}: {structured.get('findings', '')[:200]}",
                    icon="alert-triangle",
                    data={"analysis_id": analysis_id, "urgency": "HIGH", "body_part": body_part},
                ))
            except Exception as e:
                logger.error(f"[DICOM] Failed to create in-app notification: {e}")

        # Human Review Queue: flag uncertain results
        should_review = (
            structured.get("confidence", 1.0) < 0.6
            or not validation["valid"]
            or urgency == "HIGH"
        )
        if should_review:
            try:
                await db.dicom_review_queue.insert_one({
                    "analysis_id": analysis_id,
                    "user_id": user_id,
                    "reason": "low_confidence" if structured.get("confidence", 1.0) < 0.6
                              else "validation_failed" if not validation["valid"]
                              else "high_urgency",
                    "urgency": urgency,
                    "confidence": structured.get("confidence"),
                    "reviewed": False,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "feedback": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"[DICOM] Added {analysis_id} to human review queue (reason=low_confidence/validation/high_urgency)")
            except Exception as e:
                logger.error(f"[DICOM] Failed to add to review queue: {e}")

        await _audit_log("dicom_analyze_completed", user_id, analysis_id, {
            "body_part": body_part,
            "urgency": urgency,
            "confidence": structured.get("confidence"),
            "validation_valid": validation["valid"],
        })
        logger.info(f"[DICOM] Analysis {analysis_id} completed — body_part={body_part}, urgency={urgency}, valid={validation['valid']}")

    except HTTPException as e:
        logger.error(f"[DICOM] Analysis {analysis_id} HTTP error: {e.detail}")
        await db.dicom_analyses.update_one(
            {"id": analysis_id, "user_id": user_id},
            {"$set": {"status": "error", "analyze_error": f"LLM-Fehler: {e.detail[:300]}"}},
        )
    except Exception as e:
        logger.error(f"[DICOM] Analysis {analysis_id} failed: {e}")
        await db.dicom_analyses.update_one(
            {"id": analysis_id, "user_id": user_id},
            {"$set": {"status": "error", "analyze_error": str(e)[:500]}},
        )


@router.get("/{analysis_id:uuid}")
async def get_analysis(analysis_id: UUID, user: dict = Depends(get_current_user)):
    doc = await db.dicom_analyses.find_one({"id": str(analysis_id), "user_id": user["id"]}, {"_id": 0, "encrypted_data": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")
    return doc


@router.get("/list/mine")
async def list_my_analyses(user: dict = Depends(get_current_user), limit: int = 50):
    """List current user's DICOM analyses — feeds longitudinal tracking."""
    docs = await db.dicom_analyses.find(
        {"user_id": user["id"]},
        {"_id": 0, "analysis.report": 0, "previews": 0, "per_slice_scores": 0, "encrypted_data": 0},
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
    progression_report = await _llm_call_with_retry(system, prompt, model=req.model, max_tokens=1000)

    return {
        "id1": id1,
        "id2": id2,
        "delta": delta,
        "progression_report": progression_report,
        "language": req.language,
    }


# ═══════════════════════════════════════════════════════════════
# PDF REPORT
# ═══════════════════════════════════════════════════════════════

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

    _font(bold=True, size=16)
    pdf.set_text_color(201, 168, 76)
    pdf.cell(0, 10, "Prep Academy - DICOM Klinischer Bericht", ln=True)
    pdf.set_text_color(0, 0, 0)
    _font(size=9)
    pdf.cell(0, 6, f"Analyse-ID: {analysis_id}", ln=True)
    pdf.cell(0, 6, f"Erstellt: {analysis.get('analyzed_at','')[:19]}  |  Modell: {analysis.get('model','')}", ln=True)
    pdf.ln(4)

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

    urgency = (structured.get("urgency") or "UNKNOWN").upper()
    urgency_colors = {"HIGH": (220, 38, 38), "MEDIUM": (245, 158, 11), "LOW": (34, 197, 94), "UNKNOWN": (120, 120, 120)}
    pdf.set_fill_color(*urgency_colors.get(urgency, urgency_colors["UNKNOWN"]))
    pdf.set_text_color(255, 255, 255)
    _font(bold=True, size=12)
    conf = structured.get("confidence", 0)
    pdf.cell(0, 9, f"Dringlichkeit: {urgency}   |   Confidence: {conf:.0%}" if isinstance(conf, (int, float)) else f"Dringlichkeit: {urgency}", ln=True, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

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

    dd = analysis.get("differential_diagnoses", [])
    if dd:
        _font(bold=True, size=11)
        pdf.cell(0, 7, "Differenzialdiagnosen (Rangliste)", ln=True)
        _font(size=10)
        for i, d in enumerate(dd):
            prob = d.get("probability", "?")
            diag = d.get("diagnosis", "?")
            code = d.get("icd10", "")
            rationale = d.get("rationale", "")[:200]
            pdf.multi_cell(0, 5, f"{i+1}. {diag} ({code}) — {prob}: {rationale}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    expl = structured.get("explainability", [])
    if expl:
        _font(bold=True, size=11)
        pdf.cell(0, 7, "Begruendung (Explainability)", ln=True)
        _font(size=10)
        for e in expl[:8]:
            pdf.multi_cell(0, 5, f"- {e}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

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

    _font(bold=True, size=11)
    pdf.cell(0, 7, "Quellen", ln=True)
    _font(size=9)
    for s in analysis.get("sources", []):
        pdf.multi_cell(0, 4, f"[{s['index']}] {s.get('source','')} ({s.get('code','')})", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, s.get("excerpt", "")[:250], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

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


# ═══════════════════════════════════════════════════════════════
# PATIENT TIMELINE (Hospital Mode)
# ═══════════════════════════════════════════════════════════════

@router.get("/timeline/{patient_label}")
async def patient_timeline(patient_label: str, user: dict = Depends(get_current_user)):
    """Hospital Mode: aggregate all scans for a patient label, ordered chronologically.
    Admins can see all; regular users see only their own."""
    query = {"patient_label": patient_label}
    if not user.get("is_admin"):
        query["user_id"] = user["id"]

    docs = await db.dicom_analyses.find(
        query,
        {"_id": 0, "previews": 0, "per_slice_scores": 0, "analysis.report": 0, "analysis.findings_summary": 0, "encrypted_data": 0},
    ).sort("created_at", 1).to_list(200)

    timeline = []
    for d in docs:
        a = d.get("analysis", {}) or {}
        st = a.get("structured", {}) or {}
        timeline.append({
            "id": d["id"],
            "user_id": d.get("user_id", ""),
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

    urgency_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for item in timeline:
        urgency_counts[item["urgency"]] = urgency_counts.get(item["urgency"], 0) + 1

    return {
        "patient_label": patient_label,
        "scan_count": len(timeline),
        "timeline": timeline,
        "urgency_summary": urgency_counts,
        "is_admin_view": user.get("is_admin", False),
    }


# ═══════════════════════════════════════════════════════════════
# HUMAN REVIEW QUEUE
# ═══════════════════════════════════════════════════════════════

@router.post("/review/{analysis_id}")
async def submit_review(analysis_id: str, feedback: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Submit radiologist feedback for a DICOM analysis (Human Review Queue update)."""
    query = {"id": analysis_id}
    if not user.get("is_admin"):
        query["user_id"] = user["id"]

    doc = await db.dicom_analyses.find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    review_entry = {
        "analysis_id": analysis_id,
        "user_id": doc.get("user_id"),
        "reviewer_id": user["id"],
        "feedback_text": feedback.feedback_text,
        "correct_urgency": feedback.correct_urgency,
        "correct_icd10": feedback.correct_icd10,
        "rating": feedback.rating,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dicom_feedback.insert_one(review_entry)

    # Update review queue if entry exists
    await db.dicom_review_queue.update_one(
        {"analysis_id": analysis_id},
        {"$set": {
            "reviewed": True,
            "reviewed_by": user["id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "feedback": feedback.feedback_text,
        }}
    )

    await _audit_log("dicom_review_submitted", user["id"], analysis_id, {
        "rating": feedback.rating,
        "urgency_correction": feedback.correct_urgency,
    })

    return {"success": True, "message": "Feedback gespeichert. Vielen Dank für Ihre ärztliche Bewertung."}


@router.get("/review")
async def list_review_queue(user: dict = Depends(get_admin_user)):
    """Admin: list all items pending human review."""
    items = await db.dicom_review_queue.find(
        {"reviewed": False},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"items": items, "count": len(items)}


# ═══════════════════════════════════════════════════════════════
# RADIOLOGIST FEEDBACK LOOP
# ═══════════════════════════════════════════════════════════════

@router.get("/feedback/{analysis_id}")
async def get_feedback(analysis_id: str, user: dict = Depends(get_current_user)):
    """Get all feedback entries for a given analysis."""
    query = {"id": analysis_id}
    if not user.get("is_admin"):
        query["user_id"] = user["id"]

    doc = await db.dicom_analyses.find_one(query, {"_id": 0, "id": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")

    feedbacks = await db.dicom_feedback.find(
        {"analysis_id": analysis_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"items": feedbacks, "count": len(feedbacks)}


@router.post("/feedback/{analysis_id}")
async def submit_feedback(analysis_id: str, feedback: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Radiologist feedback loop — correct / validate AI output."""
    return await submit_review(analysis_id, feedback, user)


# ═══════════════════════════════════════════════════════════════
# DICOM STRUCTURED REPORT EXPORT
# ═══════════════════════════════════════════════════════════════

@router.get("/export-sr/{analysis_id}")
async def export_dicom_sr(analysis_id: str, user: dict = Depends(get_current_user)):
    """Export a DICOM Structured Report (SR) from the analysis result."""
    from fastapi.responses import StreamingResponse

    doc = await db.dicom_analyses.find_one({"id": analysis_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden")
    if doc.get("status") != "analyzed":
        raise HTTPException(status_code=400, detail="Analyse noch nicht abgeschlossen")

    analysis = doc.get("analysis", {})
    structured = analysis.get("structured", {})
    report_text = analysis.get("report", "")[:2000]

    sr_dataset = pydicom.Dataset()
    sr_dataset.SOPClassUID = "1.2.840.10008.5.1.4.1.1.88.22"
    sr_dataset.SOPInstanceUID = pydicom.uid.generate_uid()
    sr_dataset.PatientName = ""
    sr_dataset.PatientID = analysis_id[:16]
    sr_dataset.StudyInstanceUID = pydicom.uid.generate_uid()
    sr_dataset.SeriesInstanceUID = pydicom.uid.generate_uid()
    sr_dataset.Modality = "SR"
    sr_dataset.ConversionType = "SYN"
    sr_dataset.StudyDate = datetime.now(timezone.utc).strftime("%Y%m%d")
    sr_dataset.StudyTime = datetime.now(timezone.utc).strftime("%H%M%S")
    sr_dataset.Manufacturer = "Prep Academy DICOM Pipeline"

    content_sequence = []
    findings_text = structured.get("findings", "") or ""
    if findings_text:
        content_sequence.append({
            "RelationshipType": "CONTAINS",
            "ValueType": "TEXT",
            "ConceptNameCodeSequence": [{"CodeValue": "111000", "CodingSchemeDesignator": "DCM", "CodeMeaning": "Findings"}],
            "TextValue": findings_text,
        })

    urgency = structured.get("urgency", "UNKNOWN")
    content_sequence.append({
        "RelationshipType": "CONTAINS",
        "ValueType": "TEXT",
        "ConceptNameCodeSequence": [{"CodeValue": "111001", "CodingSchemeDesignator": "DCM", "CodeMeaning": "Urgency"}],
        "TextValue": urgency,
    })

    for diag in analysis.get("differential_diagnoses", []):
        content_sequence.append({
            "RelationshipType": "CONTAINS",
            "ValueType": "TEXT",
            "ConceptNameCodeSequence": [{"CodeValue": "111002", "CodingSchemeDesignator": "DCM", "CodeMeaning": "Differential Diagnosis"}],
            "TextValue": f"{diag.get('diagnosis', '')} ({diag.get('icd10', '')}) — {diag.get('probability', '')}",
        })

    sr_dataset.ContentSequence = content_sequence
    sr_dataset.NumberOfPixels = len(findings_text)

    buf = io.BytesIO()
    pydicom.dcmwrite(buf, sr_dataset)
    buf.seek(0)

    filename = f"dicom_sr_{analysis_id[:8]}.dcm"
    return StreamingResponse(
        buf,
        media_type="application/dicom",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE VERSIONING INFO
# ═══════════════════════════════════════════════════════════════

@router.get("/kb-info")
async def kb_info(user: dict = Depends(get_current_user)):
    """Get knowledge base version and stats."""
    status_info = {"ready": False, "model": "", "error": "", "kb_document_count": 0}

    if rag_module._collection is not None:
        try:
            count = rag_module._collection.count()
            status_info["kb_document_count"] = count
        except Exception:
            pass

    status_info["ready"] = rag_module._init_state.get("ready", False)
    status_info["model"] = rag_module._init_state.get("model", "")
    status_info["error"] = rag_module._init_state.get("error", "")

    version_info = await db.kb_versions.find_one({}, {"_id": 0})
    if not version_info:
        version_info = {
            "version": "1.0.0",
            "last_updated": None,
            "seed_count": rag_module._collection.count() if rag_module._collection else 0,
        }

    return {
        "kb_status": status_info,
        "version": version_info.get("version", "1.0.0"),
        "last_updated": version_info.get("last_updated"),
        "chunks": status_info["kb_document_count"],
    }
