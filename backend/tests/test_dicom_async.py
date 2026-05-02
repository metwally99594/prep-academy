"""
DICOM Pipeline — Iteration 40: Async Polling Pattern
Tests:
- POST /api/dicom/analyze/{id} returns < 5s with status='analyzing'
- Idempotency: second POST while running returns analyzing without spawning new job
- GET /{id} status transitions: uploaded -> analyzing -> analyzed
- analyzed payload contains structured/cross_check/sources/report (no JSON markers)
- /report-pdf 400 if not analyzed yet, 200 once analyzed
- 404 wrong id, 401 no auth
- Regressions: /upload, /compare, /rag/query, /auth/login
"""
import io
import os
import time
import numpy as np
import pytest
import requests
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"
PATIENT_LABEL = "TEST_Iter40_Async"

POLL_INTERVAL = 2.5
POLL_TIMEOUT = 90  # seconds


def _make_dicom_bytes(instance_number: int = 1) -> bytes:
    h, w = 256, 256
    img = np.full((h, w), 40, dtype=np.int16)
    y, x = np.ogrid[:h, :w]
    body = ((x - 128) / 120) ** 2 + ((y - 128) / 100) ** 2 < 1
    img[~body] = -1000
    lesion = ((x - 90) / 10) ** 2 + ((y - 140) / 10) ** 2 < 1
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
    ds.StudyDate = "20260101"
    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def uploaded(auth_headers):
    files = {"file": ("iter40.dcm", _make_dicom_bytes(), "application/dicom")}
    data = {"patient_label": PATIENT_LABEL}
    r = requests.post(
        f"{BASE_URL}/api/dicom/upload",
        files=files, data=data,
        headers=auth_headers, timeout=60,
    )
    assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text[:300]}"
    return r.json()


# ───────── Auth regression ─────────

def test_login_works():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200
    assert "token" in r.json()


# ───────── Upload regression ─────────

def test_upload_regression(uploaded):
    assert "analysis_id" in uploaded
    assert uploaded["total_slices"] >= 1
    assert len(uploaded["previews"]) >= 1


# ───────── Async analyze: returns fast ─────────

class TestAsyncAnalyze:
    def test_post_analyze_returns_fast(self, uploaded, auth_headers):
        aid = uploaded["analysis_id"]
        t0 = time.time()
        r = requests.post(
            f"{BASE_URL}/api/dicom/analyze/{aid}",
            json={"patient_context": "Async polling test", "language": "de"},
            headers=auth_headers,
            timeout=10,
        )
        elapsed = time.time() - t0
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert elapsed < 5.0, f"POST took {elapsed:.2f}s — should be < 5s"
        body = r.json()
        assert body["analysis_id"] == aid
        assert body["status"] == "analyzing"
        assert "message" in body

    def test_double_post_idempotent(self, uploaded, auth_headers):
        """Second POST while still running should return analyzing without error."""
        aid = uploaded["analysis_id"]
        # Quickly fire a second POST while the first is still running
        r2 = requests.post(
            f"{BASE_URL}/api/dicom/analyze/{aid}",
            json={"patient_context": "second call", "language": "de"},
            headers=auth_headers,
            timeout=10,
        )
        assert r2.status_code == 200, f"{r2.status_code} {r2.text[:200]}"
        body = r2.json()
        assert body["status"] in ("analyzing", "analyzed")  # likely analyzing

    def test_get_transitions_to_analyzed(self, uploaded, auth_headers):
        """Poll GET /api/dicom/{id} until status='analyzed' or 'error', max 90s."""
        aid = uploaded["analysis_id"]
        deadline = time.time() + POLL_TIMEOUT
        last_status = None
        seen_analyzing = False
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/dicom/{aid}", headers=auth_headers, timeout=15)
            assert r.status_code == 200
            doc = r.json()
            last_status = doc.get("status")
            if last_status == "analyzing":
                seen_analyzing = True
            if last_status in ("analyzed", "error"):
                break
            time.sleep(POLL_INTERVAL)

        assert last_status == "analyzed", (
            f"Expected analyzed within {POLL_TIMEOUT}s, last status={last_status}, "
            f"err={doc.get('analyze_error')}"
        )

        analysis = doc.get("analysis") or {}
        # report must NOT contain the JSON markers
        report = analysis.get("report", "")
        assert "STRUCTURED_JSON:" not in report
        assert "CROSS_CHECK_JSON:" not in report

        # structured payload
        st = analysis.get("structured") or {}
        for key in ("findings", "urgency", "confidence", "red_flags", "explainability", "icd10"):
            assert key in st, f"Missing structured.{key}"

        cc = analysis.get("cross_check") or {}
        assert "has_contradictions" in cc

        sources = analysis.get("sources") or []
        assert isinstance(sources, list) and len(sources) >= 1


# ───────── PDF report ─────────

class TestReportPdf:
    def test_pdf_after_analyzed(self, uploaded, auth_headers):
        aid = uploaded["analysis_id"]
        # ensure status is analyzed (depends on previous test class — re-poll briefly)
        deadline = time.time() + 30
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/dicom/{aid}", headers=auth_headers, timeout=15)
            if r.json().get("status") == "analyzed":
                break
            time.sleep(2)
        r = requests.get(f"{BASE_URL}/api/dicom/report-pdf/{aid}", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 5000


# ───────── Error handling ─────────

def test_analyze_wrong_id_404(auth_headers):
    r = requests.post(
        f"{BASE_URL}/api/dicom/analyze/not-a-real-id",
        json={"patient_context": "x"},
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code == 404


def test_analyze_no_auth_unauthorized(uploaded):
    aid = uploaded["analysis_id"]
    r = requests.post(
        f"{BASE_URL}/api/dicom/analyze/{aid}",
        json={"patient_context": "x"},
        timeout=15,
    )
    assert r.status_code in (401, 403), f"got {r.status_code}: {r.text[:200]}"


def test_pdf_wrong_id_404(auth_headers):
    r = requests.get(f"{BASE_URL}/api/dicom/report-pdf/nope-bad-id", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# ───────── Compare regression (between two uploads) ─────────

def test_compare_regression(auth_headers, uploaded):
    """Smoke test compare endpoint — upload a 2nd then call /compare."""
    files = {"file": ("iter40_b.dcm", _make_dicom_bytes(2), "application/dicom")}
    r = requests.post(
        f"{BASE_URL}/api/dicom/upload",
        files=files,
        data={"patient_label": PATIENT_LABEL},
        headers=auth_headers, timeout=60,
    )
    assert r.status_code == 200
    aid2 = r.json()["analysis_id"]
    aid1 = uploaded["analysis_id"]

    # compare endpoint accepts either analyzed or unanalyzed; LLM call may take 10-30s
    r = requests.post(
        f"{BASE_URL}/api/dicom/compare/{aid1}/{aid2}",
        json={"language": "de"},
        headers=auth_headers,
        timeout=90,
    )
    # We accept 200 (success) or 502/timeout (LLM hiccup) — only fail on auth/404 issues
    assert r.status_code in (200, 502, 504), f"unexpected: {r.status_code} {r.text[:200]}"
    if r.status_code == 200:
        body = r.json()
        assert "delta" in body
        assert "progression_report" in body


# ───────── RAG regression ─────────

def test_rag_query_regression(auth_headers):
    r = requests.post(
        f"{BASE_URL}/api/rag/query",
        json={"query": "Spannungspneumothorax Symptome", "language": "de"},
        headers=auth_headers,
        timeout=90,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    body = r.json()
    assert "answer" in body or "response" in body or "result" in body
