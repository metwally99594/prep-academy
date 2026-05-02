"""
Test suite for health check and deployment readiness.
Tests that the server starts quickly and health endpoints respond within 2 seconds.
"""
import pytest
import requests
import os
import time

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doctor-readiness.preview.emergentagent.com').rstrip('/')

class TestHealthCheck:
    """Health check endpoint tests - critical for Kubernetes deployment"""
    
    def test_health_endpoint_responds_quickly(self):
        """GET /health must respond within 2 seconds"""
        # Test internal endpoint
        start = time.time()
        response = requests.get("http://localhost:8001/health", timeout=5)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        assert elapsed < 2.0, f"Health check took {elapsed:.2f}s, must be under 2s"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected status 'healthy', got {data}"
        print(f"✓ Health check responded in {elapsed*1000:.1f}ms")
    
    def test_root_endpoint_responds_quickly(self):
        """GET / must respond within 2 seconds"""
        start = time.time()
        response = requests.get("http://localhost:8001/", timeout=5)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Root endpoint failed with status {response.status_code}"
        assert elapsed < 2.0, f"Root endpoint took {elapsed:.2f}s, must be under 2s"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Expected status 'healthy', got {data}"
        assert data.get("app") == "Medical MCQ API", f"Expected app name, got {data}"
        print(f"✓ Root endpoint responded in {elapsed*1000:.1f}ms")
    
    def test_api_root_responds(self):
        """GET /api/ must respond with API info"""
        response = requests.get(f"{BASE_URL}/api/", timeout=5)
        
        assert response.status_code == 200, f"API root failed with status {response.status_code}"
        data = response.json()
        assert "message" in data or "version" in data, f"Expected API info, got {data}"
        print(f"✓ API root responded: {data}")


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_with_valid_credentials(self):
        """POST /api/auth/login with admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@medical.com", "password": "admin123"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Response missing token"
        assert "user" in data, "Response missing user"
        assert data["user"]["email"] == "admin@medical.com"
        assert data["user"]["is_admin"] == True
        print(f"✓ Login successful for admin@medical.com")
        return data["token"]
    
    def test_login_with_invalid_credentials(self):
        """POST /api/auth/login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@medical.com", "password": "wrongpassword"},
            timeout=10
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


class TestQuestionsEndpoint:
    """Questions endpoint tests"""
    
    def test_get_questions_by_specialty(self):
        """GET /api/questions?specialty_id=internal&limit=5"""
        response = requests.get(
            f"{BASE_URL}/api/questions",
            params={"specialty_id": "internal", "limit": 5},
            timeout=10
        )
        
        assert response.status_code == 200, f"Questions endpoint failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of questions"
        assert len(data) <= 5, f"Expected max 5 questions, got {len(data)}"
        
        # Verify question structure - fields may use German variants
        if len(data) > 0:
            q = data[0]
            assert "id" in q, "Question missing id"
            assert "specialty_id" in q, "Question missing specialty_id"
            # Check for either English or German question text
            has_text = q.get("question_text") or q.get("question_text_de")
            assert has_text, "Question missing both question_text and question_text_de"
            # Check for either English or German choices
            has_choices = q.get("choices") or q.get("choices_de")
            assert has_choices is not None, "Question missing both choices and choices_de"
        
        print(f"✓ Got {len(data)} internal medicine questions")


class TestAuthenticatedEndpoints:
    """Tests for endpoints requiring authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@medical.com", "password": "admin123"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_dashboard_stats(self, auth_token):
        """GET /api/dashboard/stats returns user dashboard stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.status_code}"
        data = response.json()
        
        # Verify expected fields
        assert "total_answered" in data, "Missing total_answered"
        assert "accuracy" in data, "Missing accuracy"
        assert "xp" in data, "Missing xp"
        assert "level" in data, "Missing level"
        assert "specialty_progress" in data, "Missing specialty_progress"
        
        print(f"✓ Dashboard stats: {data['total_answered']} answered, {data['accuracy']}% accuracy, {data['xp']} XP")
    
    def test_gamification_profile(self, auth_token):
        """GET /api/gamification/profile returns gamification profile"""
        response = requests.get(
            f"{BASE_URL}/api/gamification/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Gamification profile failed: {response.status_code}"
        data = response.json()
        
        # Verify expected fields
        assert "xp" in data, "Missing xp"
        assert "level" in data, "Missing level"
        assert "badges" in data, "Missing badges"
        assert "rank" in data, "Missing rank"
        assert "all_levels" in data, "Missing all_levels"
        
        print(f"✓ Gamification profile: {data['xp']} XP, Level {data['level']['level']} ({data['level']['name_de']}), Rank #{data['rank']}")
    
    def test_leaderboard(self, auth_token):
        """GET /api/gamification/leaderboard returns leaderboard data"""
        response = requests.get(
            f"{BASE_URL}/api/gamification/leaderboard",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Leaderboard failed: {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Expected list of users"
        if len(data) > 0:
            user = data[0]
            assert "rank" in user, "Missing rank"
            assert "xp" in user, "Missing xp"
            assert "level" in user, "Missing level"
        
        print(f"✓ Leaderboard: {len(data)} users")
    
    def test_heartbeat(self, auth_token):
        """POST /api/admin/activity/heartbeat works with auth token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/activity/heartbeat",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Heartbeat failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data}"
        
        print("✓ Heartbeat successful")
    
    def test_auth_me(self, auth_token):
        """GET /api/auth/me returns current user"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Auth me failed: {response.status_code}"
        data = response.json()
        assert data.get("email") == "admin@medical.com"
        assert data.get("is_admin") == True
        
        print(f"✓ Auth me: {data['email']}")


class TestUnauthorizedAccess:
    """Tests for endpoints without authentication"""
    
    def test_dashboard_stats_requires_auth(self):
        """GET /api/dashboard/stats without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Dashboard stats correctly requires auth")
    
    def test_gamification_profile_requires_auth(self):
        """GET /api/gamification/profile without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/gamification/profile", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Gamification profile correctly requires auth")
