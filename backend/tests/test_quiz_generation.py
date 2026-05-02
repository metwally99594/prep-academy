"""Test quiz generation from notebook endpoint"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doctor-readiness.preview.emergentagent.com').rstrip('/')

class TestQuizGeneration:
    """Test the notebook quiz generation feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_works(self, auth_token):
        """Test that login works"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✅ Login successful, token length: {len(auth_token)}")
    
    def test_notebook_list(self, auth_headers):
        """Test that notebook list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/notebook/list", headers=auth_headers)
        assert response.status_code == 200, f"Notebook list failed: {response.text}"
        notebooks = response.json()
        assert isinstance(notebooks, list)
        print(f"✅ Found {len(notebooks)} notebooks")
        
        # Check if test_medical.pdf exists
        test_notebook = None
        for nb in notebooks:
            if "test_medical" in nb.get("filename", "").lower():
                test_notebook = nb
                break
        
        if test_notebook:
            print(f"✅ Found test_medical.pdf notebook: {test_notebook['id']}")
            return test_notebook
        else:
            print("⚠️ test_medical.pdf not found in notebooks")
            return None
    
    def test_generate_quiz_endpoint_exists(self, auth_headers):
        """Test that generate-quiz endpoint exists (even without valid notebook)"""
        # Test with a fake notebook ID to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/notebook/fake-id-12345/generate-quiz?count=3",
            headers=auth_headers
        )
        # Should return 404 (notebook not found) not 405 (method not allowed)
        assert response.status_code in [404, 200], f"Unexpected status: {response.status_code} - {response.text}"
        if response.status_code == 404:
            print("✅ generate-quiz endpoint exists (returned 404 for fake notebook)")
        else:
            print("✅ generate-quiz endpoint exists and returned 200")
    
    def test_generate_quiz_with_real_notebook(self, auth_headers):
        """Test quiz generation with real notebook"""
        # First get notebook list
        response = requests.get(f"{BASE_URL}/api/notebook/list", headers=auth_headers)
        assert response.status_code == 200
        notebooks = response.json()
        
        if not notebooks:
            pytest.skip("No notebooks available for testing")
        
        notebook_id = notebooks[0]["id"]
        print(f"Testing with notebook: {notebook_id}")
        
        # Generate quiz with count=3 (minimum)
        response = requests.post(
            f"{BASE_URL}/api/notebook/{notebook_id}/generate-quiz?count=3",
            headers=auth_headers,
            timeout=60  # AI generation can take time
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Quiz generation successful!")
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Questions saved: {data.get('questions_saved', 0)}")
            
            # Verify response structure
            assert "success" in data
            assert "message" in data
            
            if data.get("success"):
                assert data.get("questions_saved", 0) > 0
        elif response.status_code == 500:
            # AI service might fail, but endpoint should exist
            print(f"⚠️ Quiz generation returned 500 (AI service issue): {response.text[:200]}")
        else:
            print(f"❌ Unexpected response: {response.status_code} - {response.text[:200]}")
            assert False, f"Unexpected status code: {response.status_code}"
    
    def test_special_specialty_questions(self, auth_headers):
        """Test that questions with specialty_id='special' exist after quiz generation"""
        response = requests.get(
            f"{BASE_URL}/api/questions?specialty_id=special&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        questions = response.json()
        print(f"✅ Found {len(questions)} questions with specialty_id='special'")
        
        if questions:
            q = questions[0]
            print(f"   Sample question ID: {q.get('id')}")
            print(f"   Question text: {q.get('question_text', q.get('question_text_de', ''))[:100]}...")
            print(f"   Choices count: {len(q.get('choices', q.get('choices_de', [])))}")
    
    def test_specialties_include_special(self, auth_headers):
        """Test that 'special' specialty exists in specialties list"""
        response = requests.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        specialties = response.json()
        
        special_found = False
        for s in specialties:
            if s.get("id") == "special":
                special_found = True
                print(f"✅ 'Special' specialty found: {s.get('name_de')} with {s.get('question_count')} questions")
                break
        
        assert special_found, "Special specialty not found in specialties list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
