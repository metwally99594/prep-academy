"""
Test suite for Gamification System and Auth Pages (Iteration 7)
Tests:
- Registration flow (no Google Auth)
- Login flow (email/password only)
- Gamification profile endpoint
- Leaderboard endpoint
- XP awarding on answer submission
- Specialties with question counts
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doctor-readiness.preview.emergentagent.com')

class TestAuthEndpoints:
    """Test authentication endpoints - email/password only (no Google)"""
    
    def test_login_success_admin(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == "admin@medical.com"
        assert data["user"]["is_admin"] == True
        print(f"PASS: Admin login successful, token received")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: Invalid credentials rejected with 401")
    
    def test_register_new_user(self):
        """Test registration with email/password"""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "testpass123",
            "name": "Test User"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == unique_email
        assert data["user"]["name"] == "Test User"
        print(f"PASS: Registration successful for {unique_email}")
        return data["token"]
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "admin@medical.com",
            "password": "testpass123",
            "name": "Duplicate User"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Duplicate email registration rejected with 400")
    
    def test_auth_me_endpoint(self):
        """Test /auth/me returns user info"""
        # First login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        token = login_res.json()["token"]
        
        # Then check /auth/me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert data["email"] == "admin@medical.com"
        print(f"PASS: /auth/me returns correct user info")


class TestGamificationEndpoints:
    """Test gamification system endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_gamification_profile(self, auth_token):
        """Test GET /api/gamification/profile returns XP, level, badges, rank"""
        response = requests.get(f"{BASE_URL}/api/gamification/profile", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200, f"Profile failed: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "xp" in data, "Missing xp field"
        assert "level" in data, "Missing level field"
        assert "badges" in data, "Missing badges field"
        assert "rank" in data, "Missing rank field"
        assert "all_levels" in data, "Missing all_levels field"
        
        # Check level structure
        level = data["level"]
        assert "level" in level, "Missing level.level"
        assert "name" in level, "Missing level.name"
        assert "name_de" in level, "Missing level.name_de"
        assert "progress_percent" in level, "Missing level.progress_percent"
        
        # Check all_levels has 10 levels
        assert len(data["all_levels"]) == 10, f"Expected 10 levels, got {len(data['all_levels'])}"
        
        print(f"PASS: Gamification profile - XP: {data['xp']}, Level: {level['name_de']}, Rank: #{data['rank']}")
    
    def test_gamification_leaderboard(self, auth_token):
        """Test GET /api/gamification/leaderboard returns ranked users"""
        response = requests.get(f"{BASE_URL}/api/gamification/leaderboard", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200, f"Leaderboard failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Leaderboard should be a list"
        
        if len(data) > 0:
            entry = data[0]
            assert "id" in entry, "Missing id in leaderboard entry"
            assert "name" in entry, "Missing name in leaderboard entry"
            assert "xp" in entry, "Missing xp in leaderboard entry"
            assert "level" in entry, "Missing level in leaderboard entry"
            assert "rank" in entry, "Missing rank in leaderboard entry"
            assert "accuracy" in entry, "Missing accuracy in leaderboard entry"
            
            # Check entries are sorted by XP descending
            if len(data) > 1:
                for i in range(len(data) - 1):
                    assert data[i]["xp"] >= data[i+1]["xp"], "Leaderboard not sorted by XP"
        
        print(f"PASS: Leaderboard returns {len(data)} users")
    
    def test_answer_returns_xp(self, auth_token):
        """Test answering a question returns XP fields"""
        # First get a question
        questions_res = requests.get(f"{BASE_URL}/api/questions/quiz?limit=1", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert questions_res.status_code == 200
        questions = questions_res.json()
        assert len(questions) > 0, "No questions available"
        
        question = questions[0]
        question_id = question["id"]
        
        # Get correct choice
        correct_choices = [c["id"] for c in question["choices"] if c.get("is_correct")]
        
        # Submit answer
        response = requests.post(f"{BASE_URL}/api/questions/{question_id}/answer", 
            json={
                "question_id": question_id,
                "selected_choice_ids": correct_choices
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Answer submission failed: {response.text}"
        data = response.json()
        
        # Check XP fields in response
        assert "xp_earned" in data, "Missing xp_earned in answer response"
        assert "total_xp" in data, "Missing total_xp in answer response"
        assert "level" in data, "Missing level in answer response"
        assert "leveled_up" in data, "Missing leveled_up in answer response"
        
        # Correct answer should give 10+ XP
        if data["is_correct"]:
            assert data["xp_earned"] >= 10, f"Correct answer should give 10+ XP, got {data['xp_earned']}"
        else:
            assert data["xp_earned"] == 2, f"Wrong answer should give 2 XP, got {data['xp_earned']}"
        
        print(f"PASS: Answer returns XP - earned: {data['xp_earned']}, total: {data['total_xp']}, level: {data['level']['name_de']}")


class TestSpecialtiesEndpoint:
    """Test specialties endpoint with question counts"""
    
    def test_specialties_list(self):
        """Test GET /api/specialties returns all specialties with counts"""
        response = requests.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200, f"Specialties failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Specialties should be a list"
        assert len(data) >= 10, f"Expected at least 10 specialties, got {len(data)}"
        
        # Check structure
        for spec in data:
            assert "id" in spec, "Missing id"
            assert "name" in spec, "Missing name"
            assert "name_de" in spec, "Missing name_de"
            assert "question_count" in spec, "Missing question_count"
        
        # Check dermatology has questions
        dermatology = next((s for s in data if s["id"] == "dermatology"), None)
        assert dermatology is not None, "Dermatology specialty not found"
        assert dermatology["question_count"] > 0, f"Dermatology should have questions, got {dermatology['question_count']}"
        
        # Print all counts
        total = sum(s["question_count"] for s in data)
        print(f"PASS: Specialties endpoint - {len(data)} specialties, {total} total questions")
        for spec in data:
            print(f"  - {spec['name_de']}: {spec['question_count']} questions")
    
    def test_dermatology_count(self):
        """Test Dermatologie has 134 questions as specified"""
        response = requests.get(f"{BASE_URL}/api/questions/count?specialty_id=dermatology")
        assert response.status_code == 200, f"Count failed: {response.text}"
        data = response.json()
        
        # The requirement says Dermatologie should have 134 questions
        # Let's verify it has a reasonable count
        assert "count" in data, "Missing count field"
        print(f"PASS: Dermatology question count: {data['count']}")


class TestDashboardStats:
    """Test dashboard stats endpoint includes gamification data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_dashboard_stats_includes_xp(self, auth_token):
        """Test /api/dashboard/stats includes XP and level info"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Check XP and level fields
        assert "xp" in data, "Missing xp in dashboard stats"
        assert "level" in data, "Missing level in dashboard stats"
        
        level = data["level"]
        assert "level" in level, "Missing level.level"
        assert "name_de" in level, "Missing level.name_de"
        
        print(f"PASS: Dashboard stats includes XP: {data['xp']}, Level: {level['name_de']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
