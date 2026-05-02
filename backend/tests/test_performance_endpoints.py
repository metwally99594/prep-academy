"""
Test Performance Optimized Endpoints
Tests for: /api/questions/quiz, /api/questions/count, /api/questions/years/list
and specialty question counts
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestQuizEndpoint:
    """Test /api/questions/quiz endpoint with server-side $sample"""
    
    def test_quiz_returns_random_questions(self, authenticated_client):
        """Quiz endpoint returns random questions for specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        # Verify all questions are from surgery specialty
        for q in data:
            assert q["specialty_id"] == "surgery"
    
    def test_quiz_respects_limit(self, authenticated_client):
        """Quiz endpoint respects limit parameter"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_quiz_with_year_filter(self, authenticated_client):
        """Quiz endpoint filters by year"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&year=2024&limit=5")
        assert response.status_code == 200
        data = response.json()
        for q in data:
            assert q["year"] == 2024
    
    def test_quiz_with_exam_location_filter(self, authenticated_client):
        """Quiz endpoint filters by exam location"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&exam_location=innsbruck&limit=5")
        assert response.status_code == 200
        data = response.json()
        for q in data:
            assert q["exam_location"] == "innsbruck"
    
    def test_quiz_returns_different_questions(self, authenticated_client):
        """Quiz endpoint returns different random questions on each call"""
        response1 = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&limit=10")
        response2 = authenticated_client.get(f"{BASE_URL}/api/questions/quiz?specialty_id=surgery&limit=10")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        ids1 = set(q["id"] for q in response1.json())
        ids2 = set(q["id"] for q in response2.json())
        
        # With 505 questions and 10 samples, very unlikely to get same set
        # Allow some overlap but not complete match
        assert ids1 != ids2 or len(ids1) < 5, "Quiz should return different random questions"


class TestCountEndpoint:
    """Test /api/questions/count endpoint"""
    
    def test_count_surgery_questions(self, api_client):
        """Count endpoint returns correct count for surgery (505)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=surgery")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == 505
    
    def test_count_obgyn_questions(self, api_client):
        """Count endpoint returns correct count for obgyn (828)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=obgyn")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 828
    
    def test_count_internal_questions(self, api_client):
        """Count endpoint returns correct count for internal (519)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=internal")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 519
    
    def test_count_neurology_questions(self, api_client):
        """Count endpoint returns correct count for neurology (578)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=neurology")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 578
    
    def test_count_ophthalmology_questions(self, api_client):
        """Count endpoint returns correct count for ophthalmology (300)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=ophthalmology")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 300
    
    def test_count_ent_questions(self, api_client):
        """Count endpoint returns correct count for ent (153)"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=ent")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 153
    
    def test_count_with_year_filter(self, api_client):
        """Count endpoint filters by year"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=surgery&year=2024")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
    
    def test_count_with_exam_location_filter(self, api_client):
        """Count endpoint filters by exam location"""
        response = api_client.get(f"{BASE_URL}/api/questions/count?specialty_id=surgery&exam_location=vienna")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


class TestYearsListEndpoint:
    """Test /api/questions/years/list endpoint"""
    
    def test_years_list_returns_array(self, authenticated_client):
        """Years list endpoint returns array of years"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/years/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_years_list_by_specialty(self, authenticated_client):
        """Years list endpoint filters by specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/years/list?specialty_id=surgery")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Surgery has questions from 2024
        assert 2024 in data


class TestSpecialtiesQuestionCounts:
    """Test that specialties endpoint returns correct question counts"""
    
    def test_specialties_have_question_counts(self, api_client):
        """All specialties have question_count field"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        for specialty in data:
            assert "question_count" in specialty
            assert isinstance(specialty["question_count"], int)
    
    def test_surgery_specialty_count(self, api_client):
        """Surgery specialty shows 505 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        surgery = next((s for s in data if s["id"] == "surgery"), None)
        assert surgery is not None
        assert surgery["question_count"] == 505
    
    def test_obgyn_specialty_count(self, api_client):
        """Obgyn (Gynäkologie) specialty shows 828 questions"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        obgyn = next((s for s in data if s["id"] == "obgyn"), None)
        assert obgyn is not None
        assert obgyn["question_count"] == 828
        assert obgyn["name_de"] == "Gynäkologie"
    
    def test_total_questions_count(self, api_client):
        """Total questions across all specialties is 2884"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        total = sum(s["question_count"] for s in data)
        assert total == 2884, f"Expected 2884 total questions, got {total}"


class TestSingleSpecialtyEndpoint:
    """Test /api/specialties/{specialty_id} endpoint"""
    
    def test_get_surgery_specialty(self, authenticated_client):
        """Get surgery specialty returns correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/specialties/surgery")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "surgery"
        assert data["name_de"] == "Chirurgie"
        assert data["question_count"] == 505
    
    def test_get_obgyn_specialty(self, authenticated_client):
        """Get obgyn specialty returns correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/specialties/obgyn")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "obgyn"
        assert data["name_de"] == "Gynäkologie"
        assert data["question_count"] == 828


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
