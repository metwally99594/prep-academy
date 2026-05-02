"""
DICOM Pipeline Backend Tests — iteration 38
Tests:
- /api/dicom/upload (single .dcm, .zip, no auth, empty body)
- /api/dicom/analyze/{id}
- /api/dicom/{id}
- /api/dicom/list/mine
- /api/dicom/compare/{id1}/{id2}
- Regressions: /api/rag/query, /api/auth/login, /api/questions/quiz
"""
import io
import os
import time
import zipfile

import numpy as np
import pydicom
import pytest
import requests
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://doctor-readiness.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


# ───────────────── Fixtures ─────────────────

def _make_dicom_bytes(instance_number: int = 1, lesion_size: int = 10) -> bytes:
    """Create an in-memory synthetic DICOM file."""
    h, w = 256, 256
    img = np.full((h, w), 40, dtype=np.int16)
    y, x = np.ogrid[:h, :w]
    body = ((x - 128) / 120) ** 2 + ((y - 128) / 100) ** 2 < 1
    img[~body] = -1000
    lesion = ((x - 90) / lesion_size) ** 2 + ((y - 140) / lesion_size) ** 2 < 1
    img[lesion] = 120

    meta = Dataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset("t.dcm", {}, file_meta=meta, preamble=b"\0" * 128)
    ds.Modality = "CT"
    ds.BodyPartExamined = "CHEST"
    ds.PatientAge = "045Y"
    ds.PatientSex = "M"
    ds.StudyDescription = "CT Thorax"
    ds.SeriesDescription = "Axial"
    ds.Rows = h
    ds.Columns = w
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.InstanceNumber = instance_number
    ds.PixelData = img.astype(np.int16).tobytes()
    ds.WindowCenter = 40
    ds.WindowWidth = 400
    ds.RescaleSlope = 1
    ds.RescaleIntercept = 0
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.StudyDate = "20260501"

    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


def _make_zip_of_dicoms(n: int = 5) -> bytes:
    """Create a zip with N DICOM slices."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i in range(n):
            data = _make_dicom_bytes(instance_number=i + 1, lesion_size=8 + i)
            z.writestr(f"slice_{i + 1:03d}.dcm", data)
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def single_dicom_bytes():
    return _make_dicom_bytes()


@pytest.fixture(scope="module")
def zip_dicom_bytes():
    return _make_zip_of_dicoms(5)


# ───────────────── Upload tests ─────────────────

class TestDicomUpload:
    def test_upload_no_auth(self, single_dicom_bytes):
        files = {"file": ("test.dcm", single_dicom_bytes, "application/dicom")}
        r = requests.post(f"{BASE_URL}/api/dicom/upload", files=files, timeout=60)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_upload_empty_body(self, auth_headers):
        files = {"file": ("empty.dcm", b"", "application/dicom")}
        r = requests.post(f"{BASE_URL}/api/dicom/upload", files=files, headers=auth_headers, timeout=60)
        # Empty body should be 400 (or 422 if FastAPI rejects empty)
        assert r.status_code == 400, f"Expected 400, got {r.status_code} - {r.text[:200]}"

    def test_upload_single_dcm(self, auth_headers, single_dicom_bytes, request):
        files = {"file": ("test.dcm", single_dicom_bytes, "application/dicom")}
        data = {"patient_label": "TEST_Patient_A"}
        r = requests.post(f"{BASE_URL}/api/dicom/upload", files=files, data=data, headers=auth_headers, timeout=60)
        assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert "analysis_id" in body
        assert body["total_slices"] >= 1
        assert body["selected_count"] >= 1
        assert "header" in body
        h = body["header"]
        assert h["modality"] == "CT"
        assert h["body_part"] == "CHEST"
        assert h["rows"] == 256 and h["columns"] == 256
        assert isinstance(body["previews"], list) and len(body["previews"]) >= 1
        p0 = body["previews"][0]
        assert "thumbnail" in p0 and len(p0["thumbnail"]) > 100
        score = p0["score"]
        for k in ("edge_density", "variance", "bright_regions", "dark_regions", "saliency"):
            assert k in score
        # Cache for next test
        request.config.cache.set("dicom/single_id", body["analysis_id"])

    def test_upload_zip_series(self, auth_headers, zip_dicom_bytes, request):
        files = {"file": ("series.zip", zip_dicom_bytes, "application/zip")}
        data = {"patient_label": "TEST_Patient_A"}
        r = requests.post(f"{BASE_URL}/api/dicom/upload", files=files, data=data, headers=auth_headers, timeout=90)
        assert r.status_code == 200, f"ZIP upload failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body["total_slices"] == 5
        assert body["selected_count"] == 5  # capped at 8, but only 5 slices
        assert len(body["previews"]) == 5
        request.config.cache.set("dicom/zip_id", body["analysis_id"])


# ───────────────── Analyze, Get, List ─────────────────

class TestDicomAnalyze:
    def test_analyze_wrong_id(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/dicom/analyze/00000000-0000-0000-0000-000000000000",
            json={"patient_context": "test", "language": "de"},
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def test_analyze_single(self, auth_headers, request):
        analysis_id = request.config.cache.get("dicom/single_id", None)
        assert analysis_id, "No analysis_id from upload test"
        payload = {"patient_context": "45 Jahre alter Mann mit Brustschmerzen", "language": "de"}
        r = requests.post(
            f"{BASE_URL}/api/dicom/analyze/{analysis_id}",
            json=payload,
            headers=auth_headers,
            timeout=180,
        )
        # K8s ingress has a 60s timeout but backend continues. Fallback: poll GET endpoint.
        if r.status_code == 502:
            for _ in range(20):
                time.sleep(5)
                g = requests.get(f"{BASE_URL}/api/dicom/{analysis_id}", headers=auth_headers, timeout=30)
                if g.status_code == 200 and g.json().get("status") == "analyzed":
                    body = g.json().get("analysis", {})
                    body["report"] = body.get("report", "")
                    break
            else:
                pytest.fail("Analyze 502 from ingress AND backend never persisted analyzed status")
        else:
            assert r.status_code == 200, f"Analyze failed: {r.status_code} {r.text[:500]}"
            body = r.json()
        assert "report" in body and len(body["report"]) > 100
        # Citations may appear as [1] or [N1] — the prompt says "[N]" generically
        import re as _re
        assert _re.search(r"\[N?\d+\]", body["report"]), "Report should contain [N] or [1] citations"
        assert "findings_summary" in body and len(body["findings_summary"]) > 50
        assert "sources" in body and len(body["sources"]) >= 1
        s0 = body["sources"][0]
        assert "source" in s0 and "code" in s0 and "excerpt" in s0
        assert "cross_check" in body
        cc = body["cross_check"]
        assert "has_contradictions" in cc
        assert "confidence" in cc
        # ICD-10 mention check (heuristic)
        report_lower = body["report"].lower()
        assert any(c in body["report"] for c in ["ICD", "icd", "S2", "J1", "J9", "I2", "Z"]), \
            "Report should mention ICD-10 or similar codes"

    def test_get_by_id(self, auth_headers, request):
        analysis_id = request.config.cache.get("dicom/single_id", None)
        assert analysis_id
        r = requests.get(f"{BASE_URL}/api/dicom/{analysis_id}", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == analysis_id
        assert body.get("status") in ("uploaded", "analyzed")

    def test_list_mine(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/dicom/list/mine", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "count" in body
        assert isinstance(body["items"], list)
        assert body["count"] >= 1
        # Compact listing should NOT contain previews / per_slice_scores / report
        for item in body["items"]:
            assert "previews" not in item
            assert "per_slice_scores" not in item
            if "analysis" in item:
                assert "report" not in (item.get("analysis") or {})


# ───────────────── Compare ─────────────────

class TestDicomCompare:
    def test_compare(self, auth_headers, request):
        id1 = request.config.cache.get("dicom/single_id", None)
        id2 = request.config.cache.get("dicom/zip_id", None)
        assert id1 and id2
        r = requests.post(
            f"{BASE_URL}/api/dicom/compare/{id1}/{id2}",
            json={"language": "de"},
            headers=auth_headers,
            timeout=120,
        )
        # Allow one retry on 502 (ingress timeout per task notes)
        if r.status_code == 502:
            time.sleep(3)
            r = requests.post(
                f"{BASE_URL}/api/dicom/compare/{id1}/{id2}",
                json={"language": "de"},
                headers=auth_headers,
                timeout=120,
            )
        assert r.status_code == 200, f"Compare failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert "delta" in body
        d = body["delta"]
        for k in ("bright_change_pct", "dark_change_pct", "slice_count_change", "days_between"):
            assert k in d
        assert "progression_report" in body and len(body["progression_report"]) > 50


# ───────────────── Regressions ─────────────────

class TestRegressions:
    def test_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_rag_query(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/rag/query",
            json={"query": "Was ist STEMI?", "language": "de", "top_k": 3},
            headers=auth_headers,
            timeout=120,
        )
        assert r.status_code == 200, f"RAG query failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert "answer" in body and len(body["answer"]) > 20

    def test_questions_quiz(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/questions/quiz?count=3", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        # Could be {"questions": [...]} or list
        if isinstance(body, dict):
            assert "questions" in body or "items" in body
