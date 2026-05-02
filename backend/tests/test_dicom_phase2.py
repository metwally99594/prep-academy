"""Phase 2 Context-Aware DICOM tests — body-part detection, validation, confidence gate."""
import os
import time
import io
import pytest
import requests
import numpy as np
import pydicom
from pydicom.dataset import FileDataset, Dataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://doctor-readiness.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASS = "admin123"


def _make_dcm(path, body, desc, h=256, w=256):
    meta = Dataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.Modality = "CT"
    ds.BodyPartExamined = body
    ds.StudyDescription = desc
    ds.SeriesDescription = "Axial"
    ds.PatientAge = "050Y"
    ds.PatientSex = "M"
    ds.Rows = h; ds.Columns = w
    ds.BitsAllocated = 16; ds.BitsStored = 16; ds.HighBit = 15
    ds.PixelRepresentation = 1; ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.InstanceNumber = 1
    img = np.random.randint(0, 500, (h, w), dtype=np.int16)
    ds.PixelData = img.tobytes()
    ds.WindowCenter = 40; ds.WindowWidth = 400
    ds.RescaleSlope = 1; ds.RescaleIntercept = 0
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.StudyDate = "20260501"
    ds.save_as(path, enforce_file_format=True)


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload_and_analyze(headers, dcm_path, patient_context="", timeout=180):
    with open(dcm_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/dicom/upload",
            files={"file": (os.path.basename(dcm_path), f, "application/dicom")},
            data={"patient_label": f"TEST_Phase2_{os.path.basename(dcm_path)}"},
            headers=headers, timeout=60,
        )
    assert r.status_code == 200, r.text
    aid = r.json()["analysis_id"]

    r = requests.post(
        f"{BASE_URL}/api/dicom/analyze/{aid}",
        json={"patient_context": patient_context, "language": "de"},
        headers=headers, timeout=20,
    )
    assert r.status_code == 200, r.text

    # Poll
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(4)
        g = requests.get(f"{BASE_URL}/api/dicom/{aid}", headers=headers, timeout=20)
        assert g.status_code == 200
        st = g.json().get("status")
        if st == "analyzed":
            return aid, g.json()
        if st == "error":
            pytest.fail(f"Analysis error: {g.json().get('analyze_error')}")
    pytest.fail("Timeout waiting for analyzed status")


# ============== Detection method tests ==============

class TestBodyPartDetection:
    def test_chest_dicom_metadata(self, headers, tmp_path):
        p = str(tmp_path / "chest.dcm")
        _make_dcm(p, "CHEST", "CT Thorax")
        aid, doc = _upload_and_analyze(headers, p)
        a = doc["analysis"]
        assert a["body_part"] == "chest"
        assert a["body_part_label"] == "Thorax"
        assert a["detection"]["method"] == "dicom_metadata"
        assert a["detection"]["confidence"] >= 0.95
        # ICD-10 should be chest-prefix dominated
        codes = a["structured"].get("icd10", [])
        if codes:
            chest_prefixes = ("J", "I2", "I3", "S2", "C34", "R09")
            valid_codes = [c for c in codes if str(c).upper().startswith(chest_prefixes)]
            assert len(valid_codes) >= 1, f"expected chest ICD-10, got {codes}"
        assert a["validation"]["valid"] is True, f"flags={a['validation']['flags']}"

    def test_brain_dicom_metadata_with_context(self, headers, tmp_path):
        p = str(tmp_path / "brain.dcm")
        _make_dcm(p, "HEAD", "CT Schädel")
        aid, doc = _upload_and_analyze(
            headers, p, patient_context="Frau 68J, akute Hemiparese links, Sprachstörung"
        )
        a = doc["analysis"]
        assert a["body_part"] == "brain"
        assert a["detection"]["method"] == "dicom_metadata"
        # Report should NOT contain chest forbidden terms
        report_blob = (a.get("report", "") + " " +
                       str(a["structured"].get("findings", "")) + " " +
                       " ".join(a["structured"].get("red_flags", []))).lower()
        assert "pneumothorax" not in report_blob, "Brain case should not mention Pneumothorax"
        assert "hämatothorax" not in report_blob, "Brain case should not mention Hämatothorax"
        assert a["validation"]["valid"] is True, f"flags={a['validation']['flags']}"

    def test_keyword_match_no_body_part(self, headers, tmp_path):
        p = str(tmp_path / "no_hint.dcm")
        _make_dcm(p, "", "Thorax CT")  # empty body part, but Thorax in study description
        aid, doc = _upload_and_analyze(headers, p)
        a = doc["analysis"]
        assert a["body_part"] == "chest"
        assert a["detection"]["method"] == "keyword_match"

    def test_aspect_ratio_heuristic(self, headers, tmp_path):
        p = str(tmp_path / "tall.dcm")
        _make_dcm(p, "", "", h=400, w=200)  # no metadata, tall aspect
        aid, doc = _upload_and_analyze(headers, p)
        a = doc["analysis"]
        # Accept aspect_heuristic-limb OR fallback-unknown
        assert a["detection"]["method"] in ("aspect_heuristic", "fallback")
        assert a["body_part"] in ("limb", "unknown")


# ============== Structure / regression tests ==============

class TestAnalysisStructure:
    def test_get_returns_phase2_fields(self, headers, tmp_path):
        p = str(tmp_path / "chest2.dcm")
        _make_dcm(p, "CHEST", "CT Thorax")
        aid, doc = _upload_and_analyze(headers, p)
        a = doc["analysis"]
        assert "body_part" in a
        assert "body_part_label" in a
        assert "detection" in a and {"body_part", "method", "confidence"} <= set(a["detection"].keys())
        assert "validation" in a and {"valid", "flags"} <= set(a["validation"].keys())

    def test_pdf_still_works(self, headers, tmp_path):
        p = str(tmp_path / "chest3.dcm")
        _make_dcm(p, "CHEST", "CT Thorax")
        aid, _ = _upload_and_analyze(headers, p)
        r = requests.get(f"{BASE_URL}/api/dicom/report-pdf/{aid}", headers=headers, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500

    def test_timeline_still_works(self, headers):
        r = requests.get(f"{BASE_URL}/api/dicom/timeline/TEST_Phase2_chest.dcm", headers=headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "timeline" in data and "urgency_summary" in data


# ============== Regression ==============

class TestRegression:
    def test_auth_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
        assert r.status_code == 200 and "token" in r.json()

    def test_rag_query(self, headers):
        r = requests.post(f"{BASE_URL}/api/rag/query",
                          json={"query": "Pneumonie Leitlinie", "top_k": 3, "language": "de"},
                          headers=headers, timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data or "response" in data or "sources" in data
