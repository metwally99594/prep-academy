import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import get_current_user
from routes import dicom


OWNER = {"id": "owner-user", "is_admin": False}
OTHER_USER = {"id": "other-user", "is_admin": False}
ADMIN = {"id": "admin-user", "is_admin": True}


class _InsertResult:
    acknowledged = True


class _UpdateResult:
    modified_count = 1


class _Cursor:
    def __init__(self, items):
        self.items = items

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, _limit):
        return list(self.items)


class _Collection:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.inserted = []
        self.updated = []
        self.find_queries = []

    async def find_one(self, query, *_args, **_kwargs):
        for item in self.items:
            if all(item.get(key) == value for key, value in query.items()):
                return dict(item)
        return None

    async def insert_one(self, doc):
        self.inserted.append(dict(doc))
        return _InsertResult()

    async def update_one(self, query, update):
        self.updated.append((dict(query), dict(update)))
        return _UpdateResult()

    def find(self, query, *_args, **_kwargs):
        self.find_queries.append(dict(query))
        matches = [
            dict(item)
            for item in self.items
            if all(item.get(key) == value for key, value in query.items())
        ]
        return _Cursor(matches)


class _FakeDb:
    def __init__(self):
        self.dicom_analyses = _Collection(
            [
                {"id": "analysis-1", "user_id": OWNER["id"], "status": "analyzed"},
            ]
        )
        self.dicom_feedback = _Collection(
            [
                {
                    "analysis_id": "analysis-1",
                    "user_id": OWNER["id"],
                    "reviewer_id": OWNER["id"],
                    "feedback_text": "looks reasonable",
                }
            ]
        )
        self.dicom_review_queue = _Collection()
        self.audit_logs = _Collection()


def _client_for(user, monkeypatch):
    fake_db = _FakeDb()
    monkeypatch.setattr(dicom, "db", fake_db)

    app = FastAPI()
    app.include_router(dicom.router)
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    return client, fake_db


def test_non_owner_cannot_submit_dicom_review(monkeypatch):
    client, fake_db = _client_for(OTHER_USER, monkeypatch)

    response = client.post(
        "/api/dicom/review/analysis-1",
        json={"feedback_text": "attempted cross-user review"},
    )

    assert response.status_code == 404
    assert fake_db.dicom_feedback.inserted == []
    assert fake_db.dicom_review_queue.updated == []


def test_owner_can_submit_dicom_review(monkeypatch):
    client, fake_db = _client_for(OWNER, monkeypatch)

    response = client.post(
        "/api/dicom/review/analysis-1",
        json={"feedback_text": "owner review", "rating": 5},
    )

    assert response.status_code == 200
    assert fake_db.dicom_feedback.inserted[0]["reviewer_id"] == OWNER["id"]
    assert fake_db.dicom_feedback.inserted[0]["user_id"] == OWNER["id"]


def test_admin_can_submit_dicom_review_for_any_owner(monkeypatch):
    client, fake_db = _client_for(ADMIN, monkeypatch)

    response = client.post(
        "/api/dicom/review/analysis-1",
        json={"feedback_text": "admin review"},
    )

    assert response.status_code == 200
    assert fake_db.dicom_feedback.inserted[0]["reviewer_id"] == ADMIN["id"]
    assert fake_db.dicom_feedback.inserted[0]["user_id"] == OWNER["id"]


def test_non_owner_cannot_read_dicom_feedback(monkeypatch):
    client, fake_db = _client_for(OTHER_USER, monkeypatch)

    response = client.get("/api/dicom/feedback/analysis-1")

    assert response.status_code == 404
    assert fake_db.dicom_feedback.find_queries == []


def test_owner_can_read_dicom_feedback(monkeypatch):
    client, fake_db = _client_for(OWNER, monkeypatch)

    response = client.get("/api/dicom/feedback/analysis-1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert fake_db.dicom_feedback.find_queries == [{"analysis_id": "analysis-1"}]
