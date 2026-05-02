"""
Test suite for Admin Reports 'Frage bearbeiten' link and Tags in Question Form
Iteration 27 - Testing:
1. GET /api/admin/questions/{id} - Admin endpoint to fetch single question for editing
2. PUT /api/questions/{id} with tags - Saving tags to questions
3. QuestionCreate/QuestionUpdate models accept 'tags' field
4. Tags tab still works (create, delete, list)
5. Custom Quiz tags filter still works
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminEditQuestionAndTags:
    """Test Admin Reports 'Frage bearbeiten' and Tags in Question Form"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print("Admin login successful")
    
    # ============ GET /api/admin/questions/{id} Tests ============
    
    def test_admin_get_single_question_success(self):
        """Test GET /api/admin/questions/{id} returns single question for editing"""
        # First get a question ID from the questions list
        questions_response = self.session.get(f"{BASE_URL}/api/questions?limit=1")
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert len(questions) > 0, "No questions in database"
        
        question_id = questions[0]["id"]
        
        # Now test the admin endpoint
        response = self.session.get(f"{BASE_URL}/api/admin/questions/{question_id}")
        assert response.status_code == 200, f"Failed to get question: {response.text}"
        
        question = response.json()
        assert question["id"] == question_id
        assert "specialty_id" in question
        assert "question_text" in question or "question_text_de" in question
        assert "choices" in question or "choices_de" in question
        print(f"Successfully fetched question {question_id} via admin endpoint")
    
    def test_admin_get_question_not_found(self):
        """Test GET /api/admin/questions/{id} returns 404 for non-existent question"""
        fake_id = str(uuid.uuid4())
        response = self.session.get(f"{BASE_URL}/api/admin/questions/{fake_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returns 404 for non-existent question")
    
    def test_admin_get_question_requires_admin(self):
        """Test GET /api/admin/questions/{id} requires admin authentication"""
        # Get a question ID first
        questions_response = self.session.get(f"{BASE_URL}/api/questions?limit=1")
        question_id = questions_response.json()[0]["id"]
        
        # Try without auth
        no_auth_session = requests.Session()
        response = no_auth_session.get(f"{BASE_URL}/api/admin/questions/{question_id}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Admin endpoint correctly requires authentication")
    
    # ============ Tags in Question Create/Update Tests ============
    
    def test_create_question_with_tags(self):
        """Test POST /api/questions with tags field"""
        # First get existing tags
        tags_response = self.session.get(f"{BASE_URL}/api/tags")
        assert tags_response.status_code == 200
        tags = tags_response.json()
        
        tag_ids = [t["id"] for t in tags[:2]] if len(tags) >= 2 else []
        
        # Create question with tags
        question_data = {
            "specialty_id": "internal",
            "year": 2025,
            "question_text": "TEST_Question with tags",
            "question_text_de": "TEST_Frage mit Tags",
            "choices": [
                {"id": "a", "text": "Option A", "text_de": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "text_de": "Option B", "is_correct": False},
                {"id": "c", "text": "Option C", "text_de": "Option C", "is_correct": False},
                {"id": "d", "text": "Option D", "text_de": "Option D", "is_correct": False},
                {"id": "e", "text": "Option E", "text_de": "Option E", "is_correct": False}
            ],
            "explanation": "Test explanation",
            "explanation_de": "Test Erklärung",
            "tags": tag_ids
        }
        
        response = self.session.post(f"{BASE_URL}/api/questions", json=question_data)
        assert response.status_code == 200, f"Failed to create question: {response.text}"
        
        created = response.json()
        assert "id" in created
        self.created_question_id = created["id"]
        
        # Verify tags were saved
        if tag_ids:
            assert "tags" in created or created.get("tags") == tag_ids
        print(f"Created question with tags: {tag_ids}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/questions/{self.created_question_id}")
    
    def test_update_question_with_tags(self):
        """Test PUT /api/questions/{id} with tags field"""
        # First create a question without tags
        question_data = {
            "specialty_id": "surgery",
            "year": 2025,
            "question_text": "TEST_Question for tag update",
            "question_text_de": "TEST_Frage für Tag-Update",
            "choices": [
                {"id": "a", "text": "Option A", "text_de": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "text_de": "Option B", "is_correct": False},
                {"id": "c", "text": "Option C", "text_de": "Option C", "is_correct": False},
                {"id": "d", "text": "Option D", "text_de": "Option D", "is_correct": False},
                {"id": "e", "text": "Option E", "text_de": "Option E", "is_correct": False}
            ],
            "tags": []
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/questions", json=question_data)
        assert create_response.status_code == 200
        question_id = create_response.json()["id"]
        
        # Get existing tags
        tags_response = self.session.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        tag_ids = [t["id"] for t in tags[:2]] if len(tags) >= 2 else []
        
        # Update question with tags
        update_data = {
            "tags": tag_ids
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/questions/{question_id}", json=update_data)
        assert update_response.status_code == 200, f"Failed to update question: {update_response.text}"
        
        updated = update_response.json()
        print(f"Updated question with tags: {tag_ids}")
        
        # Verify tags were saved by fetching the question
        get_response = self.session.get(f"{BASE_URL}/api/admin/questions/{question_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        
        if tag_ids:
            assert fetched.get("tags") == tag_ids, f"Tags not saved correctly. Expected {tag_ids}, got {fetched.get('tags')}"
        print("Tags persisted correctly after update")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/questions/{question_id}")
    
    # ============ Tags CRUD Tests (Regression) ============
    
    def test_get_all_tags(self):
        """Test GET /api/tags returns all tags"""
        response = self.session.get(f"{BASE_URL}/api/tags")
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, list)
        print(f"Found {len(tags)} tags: {[t['name'] for t in tags]}")
    
    def test_create_and_delete_tag(self):
        """Test POST /api/admin/tags and DELETE /api/admin/tags/{id}"""
        # Create tag
        tag_name = f"TEST_Tag_{uuid.uuid4().hex[:6]}"
        create_response = self.session.post(f"{BASE_URL}/api/admin/tags", json={
            "name": tag_name,
            "color": "#ff5733"
        })
        assert create_response.status_code == 200, f"Failed to create tag: {create_response.text}"
        
        created_tag = create_response.json()
        assert created_tag["name"] == tag_name
        assert created_tag["color"] == "#ff5733"
        tag_id = created_tag["id"]
        print(f"Created tag: {tag_name}")
        
        # Delete tag
        delete_response = self.session.delete(f"{BASE_URL}/api/admin/tags/{tag_id}")
        assert delete_response.status_code == 200
        print(f"Deleted tag: {tag_name}")
    
    # ============ Custom Quiz Tags Filter Tests (Regression) ============
    
    def test_custom_quiz_with_tags_filter(self):
        """Test POST /api/questions/custom-quiz with tags filter"""
        # Get existing tags
        tags_response = self.session.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        
        if not tags:
            pytest.skip("No tags available for testing")
        
        tag_id = tags[0]["id"]
        
        # Test custom quiz with tags filter
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "specialties": [],
            "tags": [tag_id],
            "limit": 50,
            "mode": "exam"
        })
        assert response.status_code == 200, f"Custom quiz failed: {response.text}"
        questions = response.json()
        print(f"Custom quiz with tag filter returned {len(questions)} questions")
    
    def test_custom_quiz_count_with_tags(self):
        """Test POST /api/questions/custom-quiz/count with tags filter"""
        tags_response = self.session.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        
        if not tags:
            pytest.skip("No tags available for testing")
        
        tag_id = tags[0]["id"]
        
        response = self.session.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "specialties": [],
            "tags": [tag_id]
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Custom quiz count with tag filter: {data['count']}")
    
    # ============ Reports Tests (Regression) ============
    
    def test_get_all_reports(self):
        """Test GET /api/admin/reports/all returns reports with question_id"""
        response = self.session.get(f"{BASE_URL}/api/admin/reports/all")
        assert response.status_code == 200
        reports = response.json()
        assert isinstance(reports, list)
        
        # Check that reports have question_id for the edit link
        if reports:
            report = reports[0]
            assert "question_id" in report, "Report missing question_id field"
            print(f"Found {len(reports)} reports, first has question_id: {report.get('question_id')}")
        else:
            print("No reports found")


class TestQuestionTagsIntegration:
    """Integration tests for question tags workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_full_edit_question_workflow(self):
        """Test full workflow: Create question -> Edit with tags -> Verify persistence"""
        # 1. Create question
        question_data = {
            "specialty_id": "neurology",
            "year": 2025,
            "question_text": "TEST_Full workflow question",
            "question_text_de": "TEST_Vollständiger Workflow Frage",
            "choices": [
                {"id": "a", "text": "A", "text_de": "A", "is_correct": True},
                {"id": "b", "text": "B", "text_de": "B", "is_correct": False},
                {"id": "c", "text": "C", "text_de": "C", "is_correct": False},
                {"id": "d", "text": "D", "text_de": "D", "is_correct": False},
                {"id": "e", "text": "E", "text_de": "E", "is_correct": False}
            ],
            "tags": []
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/questions", json=question_data)
        assert create_response.status_code == 200
        question_id = create_response.json()["id"]
        print(f"1. Created question: {question_id}")
        
        # 2. Fetch question via admin endpoint (simulating ?edit= URL param)
        get_response = self.session.get(f"{BASE_URL}/api/admin/questions/{question_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["id"] == question_id
        print(f"2. Fetched question via admin endpoint")
        
        # 3. Get tags and update question with tags
        tags_response = self.session.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        tag_ids = [t["id"] for t in tags[:2]] if len(tags) >= 2 else []
        
        update_response = self.session.put(f"{BASE_URL}/api/questions/{question_id}", json={
            "tags": tag_ids
        })
        assert update_response.status_code == 200
        print(f"3. Updated question with tags: {tag_ids}")
        
        # 4. Verify tags persisted
        verify_response = self.session.get(f"{BASE_URL}/api/admin/questions/{question_id}")
        assert verify_response.status_code == 200
        verified = verify_response.json()
        
        if tag_ids:
            assert verified.get("tags") == tag_ids, f"Tags not persisted. Expected {tag_ids}, got {verified.get('tags')}"
        print(f"4. Verified tags persisted correctly")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/questions/{question_id}")
        print("5. Cleaned up test question")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
