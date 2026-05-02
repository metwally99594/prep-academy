"""
Test bulk delete functionality for admin questions management.
Tests:
- POST /api/admin/questions/bulk-delete endpoint
- Requires admin authentication
- Returns error for empty array
- Works with valid question IDs (using fake IDs to avoid deleting real data)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBulkDelete:
    """Test bulk delete questions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
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
    
    def test_bulk_delete_requires_auth(self):
        """Test that bulk delete requires authentication"""
        # Create a new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": ["fake-id-1"]
        })
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Bulk delete requires auth: {response.status_code}")
    
    def test_bulk_delete_requires_admin(self):
        """Test that bulk delete requires admin role"""
        # Register a regular user
        test_email = f"test_regular_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test Regular User"
        }, headers={"Content-Type": "application/json"})
        
        if reg_response.status_code == 200:
            regular_token = reg_response.json()["token"]
            
            # Try bulk delete with regular user
            response = requests.post(
                f"{BASE_URL}/api/admin/questions/bulk-delete",
                json={"question_ids": ["fake-id-1"]},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {regular_token}"
                }
            )
            
            # Should return 403 (forbidden)
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print(f"✓ Bulk delete requires admin role: {response.status_code}")
        else:
            # User might already exist, skip this test
            pytest.skip("Could not create regular user for test")
    
    def test_bulk_delete_empty_array_returns_error(self):
        """Test that empty question_ids array returns error"""
        response = self.session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": []
        })
        
        # Should return 400 (bad request)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        print(f"✓ Empty array returns error: {response.status_code} - {data.get('detail')}")
    
    def test_bulk_delete_with_fake_ids(self):
        """Test bulk delete with fake IDs (should return 0 deleted)"""
        fake_ids = [
            f"fake-test-id-{uuid.uuid4().hex}",
            f"fake-test-id-{uuid.uuid4().hex}",
            f"fake-test-id-{uuid.uuid4().hex}"
        ]
        
        response = self.session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": fake_ids
        })
        
        # Should return 200 with deleted count of 0
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "deleted" in data, "Response should contain 'deleted' count"
        assert data["deleted"] == 0, f"Expected 0 deleted (fake IDs), got {data['deleted']}"
        print(f"✓ Bulk delete with fake IDs: deleted={data['deleted']}")
    
    def test_bulk_delete_response_format(self):
        """Test that bulk delete returns correct response format"""
        response = self.session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": ["nonexistent-id"]
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict), "Response should be a dict"
        assert "deleted" in data, "Response should have 'deleted' key"
        assert isinstance(data["deleted"], int), "'deleted' should be an integer"
        print(f"✓ Response format correct: {data}")


class TestBulkDeleteIntegration:
    """Integration tests - create test question, bulk delete it, verify deletion"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
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
    
    def test_create_and_bulk_delete_question(self):
        """Create a test question, then bulk delete it"""
        # Create a test question
        test_question = {
            "specialty_id": "surgery",
            "year": 2025,
            "exam_location": "vienna",
            "question_text": "TEST_BULK_DELETE: This is a test question for bulk delete",
            "question_text_de": "TEST_BULK_DELETE: Dies ist eine Testfrage für Massenlöschung",
            "choices": [
                {"id": "a", "text": "Option A", "text_de": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "text_de": "Option B", "is_correct": False},
                {"id": "c", "text": "Option C", "text_de": "Option C", "is_correct": False},
                {"id": "d", "text": "Option D", "text_de": "Option D", "is_correct": False},
                {"id": "e", "text": "Option E", "text_de": "Option E", "is_correct": False}
            ],
            "explanation": "Test explanation",
            "explanation_de": "Test Erklärung"
        }
        
        # Create the question
        create_response = self.session.post(f"{BASE_URL}/api/questions", json=test_question)
        assert create_response.status_code == 200, f"Failed to create question: {create_response.text}"
        created_question = create_response.json()
        question_id = created_question["id"]
        print(f"✓ Created test question: {question_id}")
        
        # Verify question exists
        get_response = self.session.get(f"{BASE_URL}/api/questions/{question_id}")
        assert get_response.status_code == 200, f"Question not found after creation"
        print(f"✓ Verified question exists")
        
        # Bulk delete the question
        delete_response = self.session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": [question_id]
        })
        assert delete_response.status_code == 200, f"Bulk delete failed: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data["deleted"] == 1, f"Expected 1 deleted, got {delete_data['deleted']}"
        print(f"✓ Bulk deleted question: deleted={delete_data['deleted']}")
        
        # Verify question no longer exists
        verify_response = self.session.get(f"{BASE_URL}/api/questions/{question_id}")
        assert verify_response.status_code == 404, f"Question should be deleted, got {verify_response.status_code}"
        print(f"✓ Verified question is deleted")
    
    def test_bulk_delete_multiple_questions(self):
        """Create multiple test questions, then bulk delete them all"""
        created_ids = []
        
        # Create 3 test questions
        for i in range(3):
            test_question = {
                "specialty_id": "internal",
                "year": 2025,
                "exam_location": "innsbruck",
                "question_text": f"TEST_BULK_DELETE_MULTI_{i}: Test question {i}",
                "question_text_de": f"TEST_BULK_DELETE_MULTI_{i}: Testfrage {i}",
                "choices": [
                    {"id": "a", "text": "A", "text_de": "A", "is_correct": True},
                    {"id": "b", "text": "B", "text_de": "B", "is_correct": False},
                    {"id": "c", "text": "C", "text_de": "C", "is_correct": False},
                    {"id": "d", "text": "D", "text_de": "D", "is_correct": False},
                    {"id": "e", "text": "E", "text_de": "E", "is_correct": False}
                ]
            }
            
            create_response = self.session.post(f"{BASE_URL}/api/questions", json=test_question)
            assert create_response.status_code == 200, f"Failed to create question {i}"
            created_ids.append(create_response.json()["id"])
        
        print(f"✓ Created {len(created_ids)} test questions")
        
        # Bulk delete all questions
        delete_response = self.session.post(f"{BASE_URL}/api/admin/questions/bulk-delete", json={
            "question_ids": created_ids
        })
        assert delete_response.status_code == 200, f"Bulk delete failed: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data["deleted"] == 3, f"Expected 3 deleted, got {delete_data['deleted']}"
        print(f"✓ Bulk deleted {delete_data['deleted']} questions")
        
        # Verify all questions are deleted
        for qid in created_ids:
            verify_response = self.session.get(f"{BASE_URL}/api/questions/{qid}")
            assert verify_response.status_code == 404, f"Question {qid} should be deleted"
        print(f"✓ Verified all questions are deleted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
