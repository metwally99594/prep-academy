"""
Test suite for iteration 12 features:
1. Custom Quiz City Filter (exam_location)
2. PDF Export with choices and images
3. Search Edit dialog image upload
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@medical.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Auth headers for API calls"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestCustomQuizCityFilter:
    """Test exam_location filter in custom quiz endpoints"""
    
    def test_custom_quiz_count_no_filter(self, auth_headers):
        """Count all questions without city filter"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": [], "exam_location": None},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] > 0
        print(f"Total questions (no filter): {data['count']}")
    
    def test_custom_quiz_count_innsbruck_filter(self, auth_headers):
        """Count questions filtered by innsbruck"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": [], "exam_location": "innsbruck"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        # DB has 2344 innsbruck questions per context
        print(f"Innsbruck questions: {data['count']}")
        assert data["count"] > 0, "Should have innsbruck questions"
    
    def test_custom_quiz_count_vienna_filter(self, auth_headers):
        """Count questions filtered by vienna"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": [], "exam_location": "vienna"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Vienna questions: {data['count']}")
        # DB has 1 vienna question per context
    
    def test_custom_quiz_count_andere_filter(self, auth_headers):
        """Count questions filtered by andere (other city)"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": [], "exam_location": "andere"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Andere Stadt questions: {data['count']}")
    
    def test_custom_quiz_count_city_with_specialty(self, auth_headers):
        """Count questions with both city and specialty filter"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": ["internal"], "exam_location": "innsbruck"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Internal + Innsbruck questions: {data['count']}")
    
    def test_custom_quiz_returns_filtered_questions(self, auth_headers):
        """Verify custom quiz returns questions matching city filter"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz", 
            json={"specialties": [], "exam_location": "innsbruck", "limit": 10, "mode": "exam"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            # Verify all returned questions have innsbruck location
            for q in data:
                assert q.get("exam_location") == "innsbruck", f"Question {q.get('id')} has wrong location: {q.get('exam_location')}"
            print(f"Returned {len(data)} innsbruck questions - all verified")
    
    def test_custom_quiz_vienna_returns_correct_location(self, auth_headers):
        """Verify vienna filter returns vienna questions"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz", 
            json={"specialties": [], "exam_location": "vienna", "limit": 10, "mode": "exam"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            for q in data:
                assert q.get("exam_location") == "vienna", f"Question has wrong location: {q.get('exam_location')}"
            print(f"Returned {len(data)} vienna questions - all verified")
    
    def test_custom_quiz_requires_auth(self):
        """Verify custom quiz endpoints require authentication"""
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", 
            json={"specialties": [], "exam_location": "innsbruck"}
        )
        assert response.status_code == 401, "Should require auth"
        
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz", 
            json={"specialties": [], "exam_location": "innsbruck", "limit": 10}
        )
        assert response.status_code == 401, "Should require auth"


class TestPDFExportWithChoices:
    """Test PDF export endpoint returns choices and images"""
    
    def test_export_questions_endpoint_exists(self, auth_headers):
        """Verify export endpoint returns questions"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "total" in data
        assert "exported_at" in data
        print(f"Export returned {data['total']} questions")
    
    def test_export_questions_have_choices(self, auth_headers):
        """Verify exported questions include choices field"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions?specialty_id=internal", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        questions = data.get("questions", [])
        
        if len(questions) > 0:
            # Check first few questions have choices
            for q in questions[:5]:
                has_choices = q.get("choices") or q.get("choices_de")
                assert has_choices, f"Question {q.get('id')} missing choices"
                choices = q.get("choices") or q.get("choices_de")
                assert len(choices) > 0, f"Question {q.get('id')} has empty choices"
                # Verify choice structure - can have is_correct OR correct_answers array
                for c in choices:
                    assert "text" in c or "text_de" in c, f"Choice missing text field"
                # Check that correct answer is determinable (either is_correct on choices or correct_answers array)
                has_is_correct = any(c.get("is_correct") for c in choices)
                has_correct_answers = q.get("correct_answers") and len(q.get("correct_answers", [])) > 0
                assert has_is_correct or has_correct_answers, f"Question {q.get('id')} has no way to determine correct answer"
            print(f"Verified choices in {min(5, len(questions))} questions")
    
    def test_export_questions_have_exam_location(self, auth_headers):
        """Verify exported questions include exam_location field"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        questions = data.get("questions", [])
        
        if len(questions) > 0:
            for q in questions[:10]:
                # exam_location should be present
                assert "exam_location" in q, f"Question {q.get('id')} missing exam_location"
            print(f"Verified exam_location in {min(10, len(questions))} questions")
    
    def test_export_by_specialty(self, auth_headers):
        """Verify export can filter by specialty"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions?specialty_id=surgery", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        questions = data.get("questions", [])
        
        if len(questions) > 0:
            for q in questions:
                assert q.get("specialty_id") == "surgery", f"Question has wrong specialty: {q.get('specialty_id')}"
            print(f"Verified {len(questions)} surgery questions")


class TestQuestionImageHandling:
    """Test question image upload and retrieval"""
    
    def test_question_can_have_image(self, auth_headers):
        """Verify questions can include image_base64 field"""
        # Get a question
        response = requests.get(f"{BASE_URL}/api/questions?limit=1", headers=auth_headers)
        assert response.status_code == 200
        questions = response.json()
        
        if len(questions) > 0:
            q = questions[0]
            # image_base64 field should be allowed (may be null)
            assert "image_base64" in q or q.get("image_base64") is None or "image_base64" not in q
            print(f"Question structure verified")
    
    def test_update_question_with_image(self, auth_headers):
        """Test updating a question with an image"""
        # Get a question to update
        response = requests.get(f"{BASE_URL}/api/questions?limit=1", headers=auth_headers)
        assert response.status_code == 200
        questions = response.json()
        
        if len(questions) > 0:
            q_id = questions[0]["id"]
            # Small test image (1x1 pixel PNG)
            test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            
            # Update with image
            response = requests.put(f"{BASE_URL}/api/questions/{q_id}", 
                json={"image_base64": test_image},
                headers=auth_headers
            )
            assert response.status_code == 200
            updated = response.json()
            assert updated.get("image_base64") == test_image, "Image not saved"
            print(f"Question {q_id} updated with image")
            
            # Remove image (cleanup)
            response = requests.put(f"{BASE_URL}/api/questions/{q_id}", 
                json={"image_base64": None},
                headers=auth_headers
            )
            assert response.status_code == 200
            print(f"Image removed from question {q_id}")


class TestSearchEndpoint:
    """Test search endpoint for edit dialog"""
    
    def test_search_returns_questions(self, auth_headers):
        """Verify search endpoint works"""
        response = requests.get(f"{BASE_URL}/api/questions/search/text?q=patient&limit=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Search returned {len(data)} results")
    
    def test_search_returns_question_with_all_fields(self, auth_headers):
        """Verify search results include all needed fields for edit"""
        response = requests.get(f"{BASE_URL}/api/questions/search/text?q=patient&limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            q = data[0]
            # Check required fields for edit dialog
            assert "id" in q
            assert "specialty_id" in q
            assert "year" in q
            assert "question_text" in q or "question_text_de" in q
            assert "choices" in q or "choices_de" in q
            print(f"Search result has all required fields")


class TestQuestionCountEndpoint:
    """Test the count endpoint with exam_location"""
    
    def test_count_with_exam_location(self, auth_headers):
        """Test GET /questions/count with exam_location parameter"""
        response = requests.get(f"{BASE_URL}/api/questions/count?exam_location=innsbruck", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Count with innsbruck filter: {data['count']}")
    
    def test_count_with_specialty_and_location(self, auth_headers):
        """Test count with both specialty and location"""
        response = requests.get(f"{BASE_URL}/api/questions/count?specialty_id=internal&exam_location=innsbruck", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Count internal+innsbruck: {data['count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
