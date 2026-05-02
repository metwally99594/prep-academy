"""
Test Custom Quiz Feature - Eigene Auswahl
Tests for POST /api/questions/custom-quiz and POST /api/questions/custom-quiz/count endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCustomQuizFeature:
    """Tests for Custom Quiz (Eigene Auswahl) feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as admin to get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # ============ COUNT ENDPOINT TESTS ============
    
    def test_custom_quiz_count_no_filters(self):
        """Test count endpoint with no filters - should return total questions"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200, f"Count failed: {response.text}"
        data = response.json()
        assert "count" in data
        assert data["count"] > 0, "Should have questions in database"
        print(f"Total questions (no filter): {data['count']}")
    
    def test_custom_quiz_count_single_specialty(self):
        """Test count with single specialty filter"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": ["internal"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] > 0, "Should have internal medicine questions"
        print(f"Internal medicine questions: {data['count']}")
    
    def test_custom_quiz_count_multiple_specialties(self):
        """Test count with multiple specialties filter"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": ["internal", "surgery", "pediatrics"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] > 0, "Should have questions from multiple specialties"
        print(f"Questions from internal+surgery+pediatrics: {data['count']}")
    
    def test_custom_quiz_count_year_range(self):
        """Test count with year range filter"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "text_search": None,
            "year_from": 2020,
            "year_to": 2024,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Questions from 2020-2024: {data['count']}")
    
    def test_custom_quiz_count_text_search(self):
        """Test count with text search filter"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "text_search": "Patient",
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Questions containing 'Patient': {data['count']}")
    
    def test_custom_quiz_count_favorites_only_empty(self):
        """Test count with favorites_only when user has no favorites"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": True,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        # May be 0 if no favorites
        print(f"Favorite questions: {data['count']}")
    
    def test_custom_quiz_count_combined_filters(self):
        """Test count with multiple filters combined"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": ["internal", "surgery"],
            "text_search": None,
            "year_from": 2015,
            "year_to": 2025,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Combined filter count: {data['count']}")
    
    # ============ CUSTOM QUIZ ENDPOINT TESTS ============
    
    def test_custom_quiz_returns_questions(self):
        """Test custom quiz endpoint returns questions"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 10,
            "mode": "exam"
        })
        assert response.status_code == 200, f"Custom quiz failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return a list of questions"
        assert len(data) <= 10, "Should respect limit"
        if len(data) > 0:
            # Verify question structure
            q = data[0]
            assert "id" in q, "Question should have id"
            assert "specialty_id" in q, "Question should have specialty_id"
            print(f"Returned {len(data)} questions")
    
    def test_custom_quiz_single_specialty(self):
        """Test custom quiz with single specialty"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": ["surgery"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 20,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All questions should be from surgery
        for q in data:
            assert q["specialty_id"] == "surgery", f"Expected surgery, got {q['specialty_id']}"
        print(f"Surgery questions returned: {len(data)}")
    
    def test_custom_quiz_multiple_specialties(self):
        """Test custom quiz with multiple specialties"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": ["internal", "neurology"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 30,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All questions should be from internal or neurology
        for q in data:
            assert q["specialty_id"] in ["internal", "neurology"], f"Unexpected specialty: {q['specialty_id']}"
        print(f"Internal+Neurology questions: {len(data)}")
    
    def test_custom_quiz_year_range_filter(self):
        """Test custom quiz with year range"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": 2022,
            "year_to": 2024,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All questions should be within year range
        for q in data:
            assert 2022 <= q["year"] <= 2024, f"Year {q['year']} outside range"
        print(f"Questions from 2022-2024: {len(data)}")
    
    def test_custom_quiz_text_search(self):
        """Test custom quiz with text search"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": "Herz",
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 20,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Questions containing 'Herz': {len(data)}")
    
    def test_custom_quiz_study_mode(self):
        """Test custom quiz in study mode (returns all matching, not random)"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": ["dermatology"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 100,
            "mode": "study"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Study mode dermatology questions: {len(data)}")
    
    def test_custom_quiz_exam_mode(self):
        """Test custom quiz in exam mode (random sampling)"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50, "Should respect limit in exam mode"
        print(f"Exam mode questions: {len(data)}")
    
    def test_custom_quiz_limit_respected(self):
        """Test that limit parameter is respected"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 5,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5, f"Expected max 5 questions, got {len(data)}"
        print(f"Limit 5 test: got {len(data)} questions")
    
    def test_custom_quiz_max_limit(self):
        """Test custom quiz with max limit (200)"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 200,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 200, f"Expected max 200 questions, got {len(data)}"
        print(f"Max limit test: got {len(data)} questions")
    
    # ============ AUTH TESTS ============
    
    def test_custom_quiz_requires_auth(self):
        """Test that custom quiz endpoints require authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        # Test count endpoint
        response = no_auth_session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Test quiz endpoint
        response = no_auth_session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Auth required test: PASS")
    
    # ============ EDGE CASES ============
    
    def test_custom_quiz_empty_specialties_array(self):
        """Test with empty specialties array (should return all)"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 10,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Empty specialties array: {len(data)} questions")
    
    def test_custom_quiz_nonexistent_specialty(self):
        """Test with non-existent specialty"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": ["nonexistent_specialty"],
            "text_search": None,
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 10,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0, "Should return empty for non-existent specialty"
        print("Non-existent specialty test: PASS (empty result)")
    
    def test_custom_quiz_short_text_search(self):
        """Test with short text search (< 2 chars should be ignored)"""
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "text_search": "a",
            "year_from": None,
            "year_to": None,
            "favorites_only": False,
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200
        data = response.json()
        # Short search should be ignored, returning all questions
        print(f"Short text search count: {data['count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
