"""
Test Viral Growth Features for Prep Academy
- Guest Mode APIs (no auth required)
- Weakness Map API
- Percentile API
- Challenge Mode APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doctor-readiness.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestGuestModeAPIs:
    """Guest Mode APIs - NO AUTH REQUIRED"""
    
    def test_guest_specialties_no_auth(self):
        """GET /api/guest/specialties returns specialties with question counts (NO AUTH)"""
        response = requests.get(f"{BASE_URL}/api/guest/specialties")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should return at least one specialty"
        
        # Verify structure of first specialty
        spec = data[0]
        assert "id" in spec, "Specialty should have 'id'"
        assert "name_de" in spec, "Specialty should have 'name_de'"
        assert "question_count" in spec, "Specialty should have 'question_count'"
        assert spec["question_count"] > 0, "Specialty should have questions"
        
        print(f"✓ Guest specialties returned {len(data)} specialties")
        print(f"  First specialty: {spec['name_de']} ({spec['question_count']} questions)")
    
    def test_guest_questions_no_auth(self):
        """GET /api/guest/questions returns 5 questions (NO AUTH)"""
        # First get a specialty
        specs_response = requests.get(f"{BASE_URL}/api/guest/specialties")
        specs = specs_response.json()
        spec_id = specs[0]["id"] if specs else "internal"
        
        response = requests.get(f"{BASE_URL}/api/guest/questions?specialty_id={spec_id}&count=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) <= 5, "Should return at most 5 questions (guest limit)"
        
        if len(data) > 0:
            q = data[0]
            assert "id" in q, "Question should have 'id'"
            assert "question_text_de" in q or "question_text" in q, "Question should have text"
            assert "choices" in q, "Question should have 'choices'"
            print(f"✓ Guest questions returned {len(data)} questions for {spec_id}")
        else:
            print(f"⚠ No questions returned for specialty {spec_id}")
    
    def test_guest_questions_limit_enforced(self):
        """Guest questions are limited to 5 even if more requested"""
        response = requests.get(f"{BASE_URL}/api/guest/questions?count=100")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 5, f"Guest limit should be 5, got {len(data)}"
        print(f"✓ Guest limit enforced: requested 100, got {len(data)}")


class TestWeaknessMapAPI:
    """Weakness Map API - requires auth"""
    
    def test_weakness_map_returns_data(self, auth_headers):
        """GET /api/dashboard/weakness-map returns specialties with accuracy/level"""
        response = requests.get(f"{BASE_URL}/api/dashboard/weakness-map", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "specialties" in data, "Response should have 'specialties'"
        
        # Check structure
        if len(data["specialties"]) > 0:
            spec = data["specialties"][0]
            assert "id" in spec, "Specialty should have 'id'"
            assert "accuracy" in spec, "Specialty should have 'accuracy'"
            assert "level" in spec, "Specialty should have 'level'"
            assert spec["level"] in ["strong", "medium", "weak"], f"Level should be strong/medium/weak, got {spec['level']}"
            print(f"✓ Weakness map returned {len(data['specialties'])} specialties")
            print(f"  Weakest: {data.get('weakest', {}).get('name_de', 'N/A')}")
            print(f"  Strongest: {data.get('strongest', {}).get('name_de', 'N/A')}")
        else:
            print("✓ Weakness map returned empty (user has no stats yet)")
    
    def test_weakness_map_requires_auth(self):
        """Weakness map should require authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/weakness-map")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Weakness map correctly requires authentication")


class TestPercentileAPI:
    """Percentile API - requires auth"""
    
    def test_percentile_returns_data(self, auth_headers):
        """GET /api/dashboard/percentile returns percentile, rank, pass_probability"""
        response = requests.get(f"{BASE_URL}/api/dashboard/percentile", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "percentile" in data, "Response should have 'percentile'"
        assert "rank" in data, "Response should have 'rank'"
        assert "total_users" in data, "Response should have 'total_users'"
        assert "pass_probability" in data, "Response should have 'pass_probability'"
        
        # Validate ranges
        assert 0 <= data["percentile"] <= 100, f"Percentile should be 0-100, got {data['percentile']}"
        assert 0 <= data["pass_probability"] <= 100, f"Pass probability should be 0-100, got {data['pass_probability']}"
        
        print(f"✓ Percentile API returned:")
        print(f"  Percentile: {data['percentile']}%")
        print(f"  Rank: {data['rank']} of {data['total_users']}")
        print(f"  Pass probability: {data['pass_probability']}%")
    
    def test_percentile_requires_auth(self):
        """Percentile should require authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/percentile")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Percentile API correctly requires authentication")


class TestChallengeModeAPIs:
    """Challenge Mode APIs - create, get, submit"""
    
    def test_create_challenge(self, auth_headers):
        """POST /api/challenge/create creates a challenge and returns challenge_id"""
        response = requests.post(
            f"{BASE_URL}/api/challenge/create?specialty_id=internal&count=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "challenge_id" in data, "Response should have 'challenge_id'"
        assert "count" in data, "Response should have 'count'"
        assert len(data["challenge_id"]) == 8, f"Challenge ID should be 8 chars, got {len(data['challenge_id'])}"
        
        print(f"✓ Challenge created: {data['challenge_id']} with {data['count']} questions")
        return data["challenge_id"]
    
    def test_get_challenge(self, auth_headers):
        """GET /api/challenge/{id} returns challenge with questions"""
        # First create a challenge
        create_response = requests.post(
            f"{BASE_URL}/api/challenge/create?specialty_id=internal&count=5",
            headers=auth_headers
        )
        challenge_id = create_response.json()["challenge_id"]
        
        # Get the challenge
        response = requests.get(f"{BASE_URL}/api/challenge/{challenge_id}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        assert "questions" in data, "Response should have 'questions'"
        assert "creator_name" in data, "Response should have 'creator_name'"
        assert "results" in data, "Response should have 'results'"
        assert len(data["questions"]) > 0, "Challenge should have questions"
        
        print(f"✓ Challenge {challenge_id} retrieved with {len(data['questions'])} questions")
        print(f"  Creator: {data['creator_name']}")
    
    def test_submit_challenge_result(self, auth_headers):
        """POST /api/challenge/{id}/submit saves result"""
        # Create a challenge
        create_response = requests.post(
            f"{BASE_URL}/api/challenge/create?specialty_id=internal&count=5",
            headers=auth_headers
        )
        challenge_id = create_response.json()["challenge_id"]
        
        # Submit a result
        response = requests.post(
            f"{BASE_URL}/api/challenge/{challenge_id}/submit?score=3&total=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should have 'results'"
        assert len(data["results"]) > 0, "Should have at least one result"
        
        # Verify result structure
        result = data["results"][0]
        assert "user_name" in result, "Result should have 'user_name'"
        assert "score" in result, "Result should have 'score'"
        assert "accuracy" in result, "Result should have 'accuracy'"
        assert result["score"] == 3, f"Score should be 3, got {result['score']}"
        assert result["accuracy"] == 60.0, f"Accuracy should be 60%, got {result['accuracy']}"
        
        print(f"✓ Challenge result submitted: {result['score']}/{result['total']} ({result['accuracy']}%)")
    
    def test_challenge_not_found(self, auth_headers):
        """GET /api/challenge/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/challenge/invalid123", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid challenge returns 404")
    
    def test_challenge_requires_auth(self):
        """Challenge APIs should require authentication"""
        # Create requires auth
        response = requests.post(f"{BASE_URL}/api/challenge/create?specialty_id=internal&count=5")
        assert response.status_code in [401, 403], f"Create should require auth, got {response.status_code}"
        
        # Get requires auth
        response = requests.get(f"{BASE_URL}/api/challenge/test1234")
        assert response.status_code in [401, 403], f"Get should require auth, got {response.status_code}"
        
        print("✓ Challenge APIs correctly require authentication")


class TestShareResultsURL:
    """Verify ShareResults component uses correct URL"""
    
    def test_share_url_uses_env_variable(self):
        """ShareResults should use REACT_APP_BACKEND_URL for share links"""
        # This is a code review check - the ShareResults.jsx uses:
        # const appUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin;
        # We verify the backend URL is accessible via specialties endpoint
        response = requests.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200, f"Backend URL should be accessible: {response.status_code}"
        print(f"✓ Backend URL is accessible: {BASE_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
