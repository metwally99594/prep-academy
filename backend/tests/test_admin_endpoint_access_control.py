import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import app


def test_batch_generator_extract_pdf_requires_admin_auth():
    response = TestClient(app).post(
        "/api/admin/batch-generator/extract-pdf",
        files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 401
