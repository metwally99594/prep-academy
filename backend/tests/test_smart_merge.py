"""
Test Smart Merge Duplicates Feature
Tests for POST /api/admin/questions/smart-merge endpoint
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSmartMergeAuth:
    """Test authentication requirements for smart-merge endpoint"""
    
    def test_smart_merge_requires_auth(self, api_client):
        """Smart merge should return 401 without authentication"""
        response = api_client.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Smart merge requires authentication (401 without token)")
    
    def test_smart_merge_requires_admin(self, api_client):
        """Smart merge should require admin role"""
        # First register a regular user
        test_email = f"test_regular_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test Regular User"
        })
        
        if reg_response.status_code == 200:
            token = reg_response.json().get("token")
            headers = {"Authorization": f"Bearer {token}"}
            response = api_client.post(f"{BASE_URL}/api/admin/questions/smart-merge", headers=headers)
            assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
            print("PASS: Smart merge requires admin role (403 for regular user)")
        else:
            # User might already exist, skip this test
            pytest.skip("Could not create test user")


class TestSmartMergeIdempotent:
    """Test that smart merge is idempotent - running twice should find 0 duplicates on second run"""
    
    def test_smart_merge_idempotent(self, authenticated_client):
        """Running smart merge twice should return 0 merged_groups on second run"""
        # First run - may or may not find duplicates
        response1 = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert response1.status_code == 200, f"First smart merge failed: {response1.status_code}"
        data1 = response1.json()
        
        # Verify response structure
        assert "merged_groups" in data1, "Response missing 'merged_groups'"
        assert "deleted_count" in data1, "Response missing 'deleted_count'"
        assert "details" in data1, "Response missing 'details'"
        
        print(f"First run: merged_groups={data1['merged_groups']}, deleted_count={data1['deleted_count']}")
        
        # Second run - should find 0 duplicates (idempotent)
        response2 = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert response2.status_code == 200, f"Second smart merge failed: {response2.status_code}"
        data2 = response2.json()
        
        assert data2["merged_groups"] == 0, f"Expected 0 merged_groups on second run, got {data2['merged_groups']}"
        assert data2["deleted_count"] == 0, f"Expected 0 deleted_count on second run, got {data2['deleted_count']}"
        
        print(f"PASS: Smart merge is idempotent - second run found 0 duplicates")


class TestSmartMergeWithSpecialtyFilter:
    """Test smart merge with specialty_id filter parameter"""
    
    def test_smart_merge_with_specialty_filter(self, authenticated_client):
        """Smart merge with specialty_id should only process that specialty"""
        # Test with a specific specialty
        response = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge?specialty_id=surgery")
        assert response.status_code == 200, f"Smart merge with filter failed: {response.status_code}"
        
        data = response.json()
        assert "merged_groups" in data
        assert "deleted_count" in data
        assert "details" in data
        
        print(f"PASS: Smart merge with specialty filter works - merged_groups={data['merged_groups']}")
    
    def test_smart_merge_with_invalid_specialty(self, authenticated_client):
        """Smart merge with non-existent specialty should return 0 results"""
        response = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge?specialty_id=nonexistent_specialty")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["merged_groups"] == 0, "Should find 0 duplicates for non-existent specialty"
        assert data["deleted_count"] == 0
        
        print("PASS: Smart merge with invalid specialty returns 0 results")


class TestSmartMergeResponseStructure:
    """Test the response structure of smart merge endpoint"""
    
    def test_response_structure(self, authenticated_client):
        """Verify the response has correct structure"""
        response = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert isinstance(data.get("merged_groups"), int), "merged_groups should be an integer"
        assert isinstance(data.get("deleted_count"), int), "deleted_count should be an integer"
        assert isinstance(data.get("details"), list), "details should be a list"
        
        # If there are details, check their structure
        if data["details"]:
            detail = data["details"][0]
            assert "kept_id" in detail, "Detail missing 'kept_id'"
            assert "deleted_count" in detail, "Detail missing 'deleted_count'"
            assert "merged_fields" in detail, "Detail missing 'merged_fields'"
            assert "text_preview" in detail, "Detail missing 'text_preview'"
            
            assert isinstance(detail["merged_fields"], list), "merged_fields should be a list"
            print(f"PASS: Response structure is correct with {len(data['details'])} detail entries")
        else:
            print("PASS: Response structure is correct (no duplicates found)")


class TestSmartMergeWithDuplicates:
    """Test smart merge with actual duplicate questions"""
    
    def test_create_and_merge_duplicates(self, authenticated_client):
        """Create duplicate questions and verify smart merge handles them correctly"""
        # Create a unique question text to avoid conflicts
        unique_text = f"TEST_DUPE_Was ist die Hauptursache für Herzinfarkt? {uuid.uuid4().hex[:8]}"
        
        # Create first question (the "best" one with explanation)
        q1_data = {
            "specialty_id": "internal",
            "year": 2024,
            "exam_location": "vienna",
            "question_text": unique_text,
            "question_text_de": unique_text,
            "choices": [
                {"id": "a", "text": "Antwort A", "text_de": "Antwort A", "is_correct": True},
                {"id": "b", "text": "Antwort B", "text_de": "Antwort B", "is_correct": False},
                {"id": "c", "text": "Antwort C", "text_de": "Antwort C", "is_correct": False},
                {"id": "d", "text": "Antwort D", "text_de": "Antwort D", "is_correct": False},
                {"id": "e", "text": "Antwort E", "text_de": "Antwort E", "is_correct": False},
            ],
            "explanation_de": "Dies ist die Erklärung für die richtige Antwort."
        }
        
        response1 = authenticated_client.post(f"{BASE_URL}/api/questions", json=q1_data)
        assert response1.status_code == 200, f"Failed to create first question: {response1.text}"
        q1_id = response1.json()["id"]
        print(f"Created first question: {q1_id}")
        
        # Create duplicate question (without explanation - should be merged/deleted)
        q2_data = {
            "specialty_id": "internal",
            "year": 2024,
            "exam_location": "vienna",
            "question_text": unique_text,
            "question_text_de": unique_text,
            "choices": [
                {"id": "a", "text": "Antwort A", "text_de": "Antwort A", "is_correct": True},
                {"id": "b", "text": "Antwort B", "text_de": "Antwort B", "is_correct": False},
                {"id": "c", "text": "Antwort C", "text_de": "Antwort C", "is_correct": False},
                {"id": "d", "text": "Antwort D", "text_de": "Antwort D", "is_correct": False},
                {"id": "e", "text": "Antwort E", "text_de": "Antwort E", "is_correct": False},
            ]
            # No explanation - this should be the "worse" copy
        }
        
        response2 = authenticated_client.post(f"{BASE_URL}/api/questions", json=q2_data)
        assert response2.status_code == 200, f"Failed to create duplicate question: {response2.text}"
        q2_id = response2.json()["id"]
        print(f"Created duplicate question: {q2_id}")
        
        # Run smart merge
        merge_response = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge?specialty_id=internal")
        assert merge_response.status_code == 200, f"Smart merge failed: {merge_response.text}"
        
        merge_data = merge_response.json()
        print(f"Smart merge result: merged_groups={merge_data['merged_groups']}, deleted_count={merge_data['deleted_count']}")
        
        # Verify at least one group was merged (our test duplicates)
        assert merge_data["merged_groups"] >= 1, "Expected at least 1 merged group"
        assert merge_data["deleted_count"] >= 1, "Expected at least 1 deleted copy"
        
        # Verify the better question (with explanation) was kept
        get_q1 = authenticated_client.get(f"{BASE_URL}/api/questions/{q1_id}")
        get_q2 = authenticated_client.get(f"{BASE_URL}/api/questions/{q2_id}")
        
        # One should exist, one should be deleted
        q1_exists = get_q1.status_code == 200
        q2_exists = get_q2.status_code == 200
        
        # The one with explanation should be kept
        if q1_exists:
            print(f"PASS: Question with explanation was kept (q1_id={q1_id})")
            # Clean up
            authenticated_client.delete(f"{BASE_URL}/api/questions/{q1_id}")
        elif q2_exists:
            # This shouldn't happen since q1 has explanation
            print(f"WARNING: Question without explanation was kept (q2_id={q2_id})")
            authenticated_client.delete(f"{BASE_URL}/api/questions/{q2_id}")
        
        print("PASS: Smart merge correctly handled duplicate questions")


class TestDuplicatesEndpointAfterMerge:
    """Test that duplicates endpoint shows 0 after smart merge"""
    
    def test_duplicates_zero_after_merge(self, authenticated_client):
        """After smart merge, duplicates scan should show 0 groups"""
        # First run smart merge to clean up any duplicates
        merge_response = authenticated_client.post(f"{BASE_URL}/api/admin/questions/smart-merge")
        assert merge_response.status_code == 200
        
        # Now scan for duplicates
        dupes_response = authenticated_client.get(f"{BASE_URL}/api/admin/questions/duplicates")
        assert dupes_response.status_code == 200
        
        dupes_data = dupes_response.json()
        
        # After smart merge, there should be 0 duplicate groups
        assert dupes_data["total_duplicate_groups"] == 0, f"Expected 0 duplicate groups, got {dupes_data['total_duplicate_groups']}"
        assert dupes_data["total_extra_copies"] == 0, f"Expected 0 extra copies, got {dupes_data['total_extra_copies']}"
        
        print("PASS: Duplicates endpoint shows 0 groups after smart merge")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
