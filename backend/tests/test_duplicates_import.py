"""
Test suite for duplicate scanner, smart merge, and import functionality.
Tests the three bugs that were fixed:
1. GET /api/admin/questions/duplicates - route collision fixed
2. POST /api/admin/questions/smart-merge - route collision fixed
3. POST /api/admin/import-questions - unified choices format
"""
import pytest
import requests
import os
import json
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestDuplicateScanner:
    """Tests for GET /api/admin/questions/duplicates endpoint"""
    
    def test_duplicates_endpoint_returns_200(self, admin_headers):
        """Test that duplicates endpoint is accessible (route collision fixed)"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_duplicates_returns_correct_structure(self, admin_headers):
        """Test that duplicates endpoint returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have groups, total_duplicate_groups, total_extra_copies
        assert "groups" in data, "Response should have 'groups' field"
        assert "total_duplicate_groups" in data, "Response should have 'total_duplicate_groups' field"
        assert "total_extra_copies" in data, "Response should have 'total_extra_copies' field"
        assert isinstance(data["groups"], list), "groups should be a list"
        
    def test_duplicates_with_specialty_filter(self, admin_headers):
        """Test duplicates endpoint with specialty filter"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates?specialty_id=internal", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        
    def test_duplicates_requires_admin(self):
        """Test that duplicates endpoint requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates")
        assert response.status_code == 401, "Should require authentication"


class TestSmartMerge:
    """Tests for POST /api/admin/questions/smart-merge endpoint"""
    
    def test_smart_merge_endpoint_returns_200(self, admin_headers):
        """Test that smart merge endpoint is accessible (route collision fixed)"""
        response = requests.post(f"{BASE_URL}/api/admin/questions/smart-merge", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_smart_merge_returns_correct_structure(self, admin_headers):
        """Test that smart merge returns expected structure"""
        response = requests.post(f"{BASE_URL}/api/admin/questions/smart-merge", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have merged_groups, deleted_count, details
        assert "merged_groups" in data, "Response should have 'merged_groups' field"
        assert "deleted_count" in data, "Response should have 'deleted_count' field"
        assert "details" in data, "Response should have 'details' field"
        
    def test_smart_merge_with_specialty_filter(self, admin_headers):
        """Test smart merge with specialty filter"""
        response = requests.post(f"{BASE_URL}/api/admin/questions/smart-merge?specialty_id=internal", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "merged_groups" in data
        
    def test_smart_merge_requires_admin(self):
        """Test that smart merge requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert response.status_code == 401, "Should require authentication"


class TestImportQuestions:
    """Tests for POST /api/admin/import-questions endpoint"""
    
    def test_import_with_choices_de_format(self, admin_headers):
        """Test import with choices_de format (the format that was causing issues)"""
        # Create test questions with choices_de format
        test_questions = [
            {
                "specialty_id": "internal",
                "question_text_de": f"Test Import Frage {uuid.uuid4().hex[:8]}",
                "choices_de": [
                    {"id": "a", "text": "Antwort A", "is_correct": False},
                    {"id": "b", "text": "Antwort B", "is_correct": True},
                    {"id": "c", "text": "Antwort C", "is_correct": False},
                    {"id": "d", "text": "Antwort D", "is_correct": False},
                    {"id": "e", "text": "Antwort E", "is_correct": False}
                ],
                "correct_answers": ["b"],
                "year": 2024,
                "exam_location": "vienna",
                "explanation_de": "Test Erklärung"
            }
        ]
        
        # Create JSON file content
        json_content = json.dumps(test_questions)
        files = {'file': ('test_import.json', json_content, 'application/json')}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/import-questions",
            headers=admin_headers,
            files=files
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "imported" in data, "Response should have 'imported' field"
        assert "skipped" in data, "Response should have 'skipped' field"
        assert "total_in_db" in data, "Response should have 'total_in_db' field"
        
    def test_import_requires_admin(self):
        """Test that import requires admin auth"""
        test_questions = [{"question_text_de": "Test"}]
        json_content = json.dumps(test_questions)
        files = {'file': ('test.json', json_content, 'application/json')}
        
        response = requests.post(f"{BASE_URL}/api/admin/import-questions", files=files)
        assert response.status_code == 401, "Should require authentication"


class TestQuestionsUnifiedFormat:
    """Tests to verify questions have unified choices format"""
    
    def test_questions_have_choices_array(self, admin_headers):
        """Test that questions have choices array with text_de and is_correct"""
        response = requests.get(f"{BASE_URL}/api/questions?limit=5", headers=admin_headers)
        assert response.status_code == 200
        questions = response.json()
        
        assert len(questions) > 0, "Should have at least one question"
        
        for q in questions:
            # Check that choices exist
            choices = q.get("choices", [])
            if choices:  # Some questions might have choices_de instead
                for choice in choices:
                    # Each choice should have text_de and is_correct
                    assert "text_de" in choice or "text" in choice, f"Choice should have text_de or text: {choice}"
                    assert "is_correct" in choice or q.get("correct_answers"), f"Choice should have is_correct or question should have correct_answers: {choice}"
                    
    def test_admin_get_question_for_editing(self, admin_headers):
        """Test that admin can get a single question for editing"""
        # First get a question ID
        response = requests.get(f"{BASE_URL}/api/questions?limit=1", headers=admin_headers)
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) > 0, "Should have at least one question"
        
        question_id = questions[0]["id"]
        
        # Now get via admin endpoint
        response = requests.get(f"{BASE_URL}/api/admin/questions/{question_id}", headers=admin_headers)
        assert response.status_code == 200, f"Admin get question failed: {response.text}"
        
        question = response.json()
        assert question["id"] == question_id
        
        # Check choices format
        choices = question.get("choices", [])
        if choices:
            for choice in choices:
                # Verify unified format
                assert "id" in choice, "Choice should have id"


class TestRouteOrdering:
    """Tests to verify route ordering is correct (duplicates before {question_id})"""
    
    def test_duplicates_not_caught_by_question_id_route(self, admin_headers):
        """Test that /duplicates is not caught by /{question_id} route"""
        # This was the original bug - GET /admin/questions/duplicates was caught by GET /admin/questions/{question_id}
        # because it was defined later. The fix moved duplicates route before the parameterized route.
        
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=admin_headers)
        
        # Should NOT return 404 "Question not found" (which would happen if caught by {question_id} route)
        assert response.status_code == 200, f"Route collision still exists: {response.text}"
        
        # Should return duplicate groups structure, not a single question
        data = response.json()
        assert "groups" in data, "Should return duplicate groups, not a single question"
        assert "id" not in data, "Should not return a single question object"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
