"""Backend tests for the Medical RAG system (ChromaDB + BGE-M3 + DeepSeek V3)."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://doctor-readiness.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASS = "admin123"


# ───────────────────── Fixtures ─────────────────────
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def user_token():
    # Create regular user
    email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Test1234!"
    payload = {"email": email, "password": pwd, "name": "Test User"}
    rr = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    if rr.status_code not in (200, 201):
        # try alternative payload key
        rr = requests.post(f"{API}/auth/register", json={"email": email, "password": pwd, "username": "Test User"}, timeout=30)
    assert rr.status_code in (200, 201), f"Register failed: {rr.status_code} {rr.text}"
    data = rr.json()
    tok = data.get("token") or data.get("access_token")
    if not tok:
        # login fallback
        lr = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
        assert lr.status_code == 200
        tok = lr.json().get("token") or lr.json().get("access_token")
    assert tok
    return tok


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ───────────────────── /api/rag/status ─────────────────────
def test_status_public():
    r = requests.get(f"{API}/rag/status", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("ready", "model", "kb_document_count", "error"):
        assert k in data, f"Missing key: {k}"
    assert data["kb_document_count"] >= 17, f"Expected >=17 KB docs, got {data['kb_document_count']}"


# ───────────────────── /api/rag/query ─────────────────────
def test_query_requires_auth():
    r = requests.post(f"{API}/rag/query", json={"query": "test", "language": "de"}, timeout=30)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_query_german_haematopneumothorax(admin_token):
    payload = {"query": "Was ist die sofortige Therapie bei Hämatopneumothorax?", "language": "de", "top_k": 5}
    r = requests.post(f"{API}/rag/query", json=payload, headers=auth(admin_token), timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "answer" in data and len(data["answer"]) > 30
    assert "[" in data["answer"] and "]" in data["answer"], "No [N] citation in answer"
    sources = data.get("sources", [])
    assert len(sources) >= 1
    # Check at least one source contains WHO or ATLS in its 'source' field
    src_names = " ".join((s.get("source", "") or "") for s in sources)
    assert ("WHO" in src_names) or ("ATLS" in src_names), f"Expected WHO/ATLS in sources, got: {src_names}"
    # Check score > 0.3 for top source
    top_score = sources[0].get("score")
    assert top_score is not None and top_score > 0.3, f"Top score too low: {top_score}"


def test_query_arabic_stemi(admin_token):
    payload = {"query": "ما هو علاج الاحتشاء القلبي الحاد STEMI؟", "language": "ar", "top_k": 5}
    r = requests.post(f"{API}/rag/query", json=payload, headers=auth(admin_token), timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "answer" in data and len(data["answer"]) > 20
    assert "[" in data["answer"] and "]" in data["answer"]
    assert len(data.get("sources", [])) >= 1


# ───────────────────── /api/rag/analyzer ─────────────────────
def test_analyzer(admin_token):
    payload = {
        "finding": "Röntgen Thorax: einseitiger Pleuraerguss rechts mit verschobenem Mediastinum",
        "patient_context": "45-jähriger Patient nach Verkehrsunfall, Dyspnoe, abgeschwächtes Atemgeräusch rechts.",
        "language": "de",
    }
    r = requests.post(f"{API}/rag/analyzer", json=payload, headers=auth(admin_token), timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    rep = data.get("clinical_report", "")
    assert len(rep) > 50, "Empty clinical report"
    # Should include ICD-10 (likely S27 or similar) and a [N] citation
    assert "[" in rep and "]" in rep, "Missing [N] citations"
    # ICD-10 marker
    assert ("ICD" in rep) or ("S27" in rep) or ("S06" in rep), "No ICD-10 marker present"
    assert len(data.get("sources", [])) >= 1


# ───────────────────── /api/rag/ingest-text ─────────────────────
def test_ingest_text_admin(admin_token):
    src_name = f"TEST_src_{uuid.uuid4().hex[:6]}"
    payload = {
        "content": "Dies ist ein Test-Dokument für die Wissensbasis. Es enthält medizinischen Inhalt zur Validierung des Ingest-Endpunkts. " * 5,
        "source": src_name,
        "category": "Test",
        "language": "de",
    }
    # baseline count
    s0 = requests.get(f"{API}/rag/status", timeout=30).json()
    before = s0["kb_document_count"]

    r = requests.post(f"{API}/rag/ingest-text", json=payload, headers=auth(admin_token), timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("added_chunks", 0) >= 1
    assert data.get("total_kb_docs", 0) > before
    assert data.get("source") == src_name

    # cleanup
    requests.delete(f"{API}/rag/source/{src_name}", headers=auth(admin_token), timeout=60)


def test_ingest_text_non_admin_forbidden(user_token):
    payload = {"content": "Test content " * 50, "source": "TEST_blocked", "category": "Test", "language": "de"}
    r = requests.post(f"{API}/rag/ingest-text", json=payload, headers=auth(user_token), timeout=60)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


# ───────────────────── /api/rag/sources ─────────────────────
def test_list_sources(admin_token):
    r = requests.get(f"{API}/rag/sources", headers=auth(admin_token), timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "sources" in data and isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1
    s0 = data["sources"][0]
    for k in ("source", "category", "language", "chunks"):
        assert k in s0, f"Missing key {k} in source entry"


def test_list_sources_requires_auth():
    r = requests.get(f"{API}/rag/sources", timeout=30)
    assert r.status_code in (401, 403)


# ───────────────────── /api/rag/source/{name} DELETE ─────────────────────
def test_delete_source_admin(admin_token):
    src_name = f"TEST_del_{uuid.uuid4().hex[:6]}"
    # Ingest a doc
    payload = {"content": "Lösch-Test-Inhalt für DELETE-Endpunkt. " * 30, "source": src_name, "category": "Test", "language": "de"}
    rr = requests.post(f"{API}/rag/ingest-text", json=payload, headers=auth(admin_token), timeout=120)
    assert rr.status_code == 200
    total_before = rr.json()["total_kb_docs"]

    # Delete it
    dr = requests.delete(f"{API}/rag/source/{src_name}", headers=auth(admin_token), timeout=60)
    assert dr.status_code == 200, dr.text
    ddata = dr.json()
    assert ddata.get("deleted_source") == src_name
    assert ddata.get("remaining_docs", 0) < total_before


# ───────────────────── REGRESSION ─────────────────────
def test_regression_login():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200


def test_regression_quiz(admin_token):
    r = requests.get(f"{API}/questions/quiz?count=2", headers=auth(admin_token), timeout=60)
    # endpoint may be different; accept 200 or 404 not breaking
    assert r.status_code in (200, 422), f"Quiz endpoint unexpected: {r.status_code} {r.text[:200]}"


def test_regression_podcast_daily():
    r = requests.get(f"{API}/podcast/daily", timeout=60)
    # public or auth-required, just ensure it isn't 500
    assert r.status_code in (200, 401, 403, 404), f"Podcast endpoint failed: {r.status_code}"
