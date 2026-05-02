"""
Test suite for verifying bulk question import functionality.
Tests the 1,506 questions imported across 4 specialties:
- Surgery: 565
- Internal Medicine: 519
- Ophthalmology: 267
- ENT: 153
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestQuestionCounts:
    """Verify correct question counts per specialty after bulk import"""
    
    def test_surgery_question_count(self, api_client):
        """Surgery should have 565 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        surgery = next((s for s in data if s["id"] == "surgery"), None)
        assert surgery is not None, "Surgery specialty not found"
        assert surgery["question_count"] == 565, f"Expected 565 surgery questions, got {surgery['question_count']}"
    
    def test_internal_medicine_question_count(self, api_client):
        """Internal Medicine should have 519 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        internal = next((s for s in data if s["id"] == "internal"), None)
        assert internal is not None, "Internal Medicine specialty not found"
        assert internal["question_count"] == 519, f"Expected 519 internal questions, got {internal['question_count']}"
    
    def test_ophthalmology_question_count(self, api_client):
        """Ophthalmology should have 267 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        ophthalmology = next((s for s in data if s["id"] == "ophthalmology"), None)
        assert ophthalmology is not None, "Ophthalmology specialty not found"
        assert ophthalmology["question_count"] == 267, f"Expected 267 ophthalmology questions, got {ophthalmology['question_count']}"
    
    def test_ent_question_count(self, api_client):
        """ENT (HNO) should have 153 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        ent = next((s for s in data if s["id"] == "ent"), None)
        assert ent is not None, "ENT specialty not found"
        assert ent["question_count"] == 153, f"Expected 153 ENT questions, got {ent['question_count']}"
    
    def test_total_question_count(self, api_client):
        """Total questions should be at least 1506"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        total = sum(s["question_count"] for s in data)
        assert total >= 1506, f"Expected at least 1506 total questions, got {total}"


class TestQuestionFormat:
    """Verify questions have correct format after import"""
    
    def test_surgery_questions_format(self, authenticated_client):
        """Surgery questions have correct format with German text and choices"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=surgery&limit=5")
        assert response.status_code == 200
        questions = response.json()
        
        assert len(questions) > 0, "No surgery questions returned"
        
        for q in questions:
            assert "id" in q, "Question missing id"
            assert "specialty_id" in q, "Question missing specialty_id"
            assert q["specialty_id"] == "surgery", f"Wrong specialty_id: {q['specialty_id']}"
            assert "question_text_de" in q, "Question missing question_text_de"
            assert "choices" in q, "Question missing choices"
            assert len(q["choices"]) >= 2, "Question should have at least 2 choices"
            
            # Verify at least one choice is correct
            correct_choices = [c for c in q["choices"] if c.get("is_correct")]
            assert len(correct_choices) >= 1, "Question should have at least one correct choice"
    
    def test_internal_questions_format(self, authenticated_client):
        """Internal Medicine questions have correct format"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=internal&limit=5")
        assert response.status_code == 200
        questions = response.json()
        
        assert len(questions) > 0, "No internal medicine questions returned"
        
        for q in questions:
            assert q["specialty_id"] == "internal"
            assert "question_text_de" in q
            assert "choices" in q
            
            # Verify choices have text_de
            for choice in q["choices"]:
                assert "id" in choice
                assert "is_correct" in choice
    
    def test_ophthalmology_questions_format(self, authenticated_client):
        """Ophthalmology questions have correct format"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=ophthalmology&limit=5")
        assert response.status_code == 200
        questions = response.json()
        
        assert len(questions) > 0, "No ophthalmology questions returned"
        
        for q in questions:
            assert q["specialty_id"] == "ophthalmology"
            assert "question_text_de" in q
            assert "choices" in q
    
    def test_ent_questions_format(self, authenticated_client):
        """ENT questions have correct format"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=ent&limit=5")
        assert response.status_code == 200
        questions = response.json()
        
        assert len(questions) > 0, "No ENT questions returned"
        
        for q in questions:
            assert q["specialty_id"] == "ent"
            assert "question_text_de" in q
            assert "choices" in q


class TestQuestionRetrieval:
    """Test question retrieval endpoints"""
    
    def test_get_questions_with_limit(self, authenticated_client):
        """Can retrieve questions with limit parameter"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=10")
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) <= 10
    
    def test_get_questions_by_specialty_surgery(self, authenticated_client):
        """Can filter questions by surgery specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=surgery&limit=50")
        assert response.status_code == 200
        questions = response.json()
        
        for q in questions:
            assert q["specialty_id"] == "surgery"
    
    def test_get_questions_by_specialty_internal(self, authenticated_client):
        """Can filter questions by internal medicine specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=internal&limit=50")
        assert response.status_code == 200
        questions = response.json()
        
        for q in questions:
            assert q["specialty_id"] == "internal"
    
    def test_get_questions_by_specialty_ent(self, authenticated_client):
        """Can filter questions by ENT specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=ent&limit=50")
        assert response.status_code == 200
        questions = response.json()
        
        for q in questions:
            assert q["specialty_id"] == "ent"
    
    def test_get_single_question(self, authenticated_client):
        """Can retrieve a single question by ID"""
        # First get a question ID
        response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        assert response.status_code == 200
        questions = response.json()
        
        if len(questions) == 0:
            pytest.skip("No questions available")
        
        question_id = questions[0]["id"]
        
        # Get single question
        response = authenticated_client.get(f"{BASE_URL}/api/questions/{question_id}")
        assert response.status_code == 200
        question = response.json()
        assert question["id"] == question_id


class TestDashboardEndpoints:
    """Test dashboard endpoints work with imported questions"""
    
    def test_dashboard_stats(self, authenticated_client):
        """Dashboard stats endpoint returns data"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_answered" in data
        assert "accuracy" in data
        assert "specialty_progress" in data
        
        # Verify specialty progress includes imported specialties
        specialty_ids = [s["id"] for s in data["specialty_progress"]]
        assert "surgery" in specialty_ids
        assert "internal" in specialty_ids
        assert "ophthalmology" in specialty_ids
        assert "ent" in specialty_ids
    
    def test_weekly_activity(self, authenticated_client):
        """Weekly activity endpoint returns data"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/weekly-activity")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 7  # 7 days


class TestAdminEndpoints:
    """Test admin endpoints work with imported questions"""
    
    def test_admin_stats(self, authenticated_client):
        """Admin stats shows correct question counts"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_questions" in data
        assert data["total_questions"] >= 1506
        
        assert "questions_by_specialty" in data
        specialty_counts = data["questions_by_specialty"]
        
        # Verify counts match expected
        assert specialty_counts.get("surgery", 0) == 565
        assert specialty_counts.get("internal", 0) == 519
        assert specialty_counts.get("ophthalmology", 0) == 267
        assert specialty_counts.get("ent", 0) == 153
    
    def test_admin_export_questions(self, authenticated_client):
        """Admin can export questions"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/export/questions?specialty_id=surgery")
        assert response.status_code == 200
        data = response.json()
        
        assert "questions" in data
        assert "total" in data
        assert data["total"] == 565  # All surgery questions


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@medical.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client
