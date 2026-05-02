"""
Test suite for Admin Duplicates Feature
Tests the GET /api/admin/questions/duplicates endpoint and related functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


class TestDuplicatesEndpoint:
    """Tests for GET /api/admin/questions/duplicates"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def regular_user_token(self):
        """Create and get a regular user token"""
        import uuid
        email = f"test_dupe_user_{uuid.uuid4().hex[:8]}@test.com"
        # Register
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "testpass123",
            "name": "Test Dupe User"
        })
        if response.status_code == 200:
            return response.json()["token"]
        # If already exists, try login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": "testpass123"
        })
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Could not create regular user for testing")
    
    def test_duplicates_requires_authentication(self):
        """Test that duplicates endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_duplicates_requires_admin_role(self, regular_user_token):
        """Test that duplicates endpoint requires admin role"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_duplicates_returns_correct_structure(self, admin_token):
        """Test that duplicates endpoint returns correct response structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "groups" in data, "Response missing 'groups' field"
        assert "total_duplicate_groups" in data, "Response missing 'total_duplicate_groups' field"
        assert "total_extra_copies" in data, "Response missing 'total_extra_copies' field"
        
        # Check types
        assert isinstance(data["groups"], list), "groups should be a list"
        assert isinstance(data["total_duplicate_groups"], int), "total_duplicate_groups should be int"
        assert isinstance(data["total_extra_copies"], int), "total_extra_copies should be int"
        
        print(f"Found {data['total_duplicate_groups']} duplicate groups with {data['total_extra_copies']} extra copies")
    
    def test_duplicates_group_structure(self, admin_token):
        """Test that each duplicate group has correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["groups"]) > 0:
            group = data["groups"][0]
            
            # Check group structure
            assert "_id" in group, "Group missing '_id' (text key)"
            assert "count" in group, "Group missing 'count'"
            assert "questions" in group, "Group missing 'questions'"
            assert isinstance(group["questions"], list), "questions should be a list"
            assert group["count"] >= 2, "Duplicate group should have count >= 2"
            assert len(group["questions"]) == group["count"], "questions length should match count"
            
            # Check question structure in group
            question = group["questions"][0]
            assert "id" in question, "Question missing 'id'"
            assert "specialty_id" in question, "Question missing 'specialty_id'"
            
            print(f"First group has {group['count']} duplicates")
        else:
            print("No duplicate groups found - this is valid if DB has no duplicates")
    
    def test_duplicates_filter_by_specialty(self, admin_token):
        """Test filtering duplicates by specialty_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get all duplicates
        response_all = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=headers)
        assert response_all.status_code == 200
        data_all = response_all.json()
        
        # Filter by internal medicine
        response_internal = requests.get(
            f"{BASE_URL}/api/admin/questions/duplicates?specialty_id=internal", 
            headers=headers
        )
        assert response_internal.status_code == 200, f"Filter failed: {response_internal.text}"
        data_internal = response_internal.json()
        
        # Verify structure
        assert "groups" in data_internal
        assert "total_duplicate_groups" in data_internal
        assert "total_extra_copies" in data_internal
        
        # If there are internal duplicates, verify they're all internal
        if len(data_internal["groups"]) > 0:
            for group in data_internal["groups"]:
                for q in group["questions"]:
                    assert q["specialty_id"] == "internal", f"Expected internal, got {q['specialty_id']}"
        
        print(f"All: {data_all['total_duplicate_groups']} groups, Internal: {data_internal['total_duplicate_groups']} groups")
    
    def test_duplicates_filter_by_surgery(self, admin_token):
        """Test filtering duplicates by surgery specialty"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/admin/questions/duplicates?specialty_id=surgery", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "groups" in data
        assert "total_duplicate_groups" in data
        
        # If there are surgery duplicates, verify they're all surgery
        for group in data["groups"]:
            for q in group["questions"]:
                assert q["specialty_id"] == "surgery", f"Expected surgery, got {q['specialty_id']}"
        
        print(f"Surgery duplicates: {data['total_duplicate_groups']} groups")
    
    def test_duplicates_filter_by_nonexistent_specialty(self, admin_token):
        """Test filtering by non-existent specialty returns empty"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/admin/questions/duplicates?specialty_id=nonexistent_specialty", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_duplicate_groups"] == 0
        assert data["total_extra_copies"] == 0
        assert len(data["groups"]) == 0
    
    def test_duplicates_count_consistency(self, admin_token):
        """Test that total_extra_copies equals sum of (count-1) for all groups"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Calculate expected extra copies
        calculated_extra = sum(group["count"] - 1 for group in data["groups"])
        
        assert data["total_extra_copies"] == calculated_extra, \
            f"total_extra_copies ({data['total_extra_copies']}) != calculated ({calculated_extra})"
        
        assert data["total_duplicate_groups"] == len(data["groups"]), \
            f"total_duplicate_groups ({data['total_duplicate_groups']}) != groups length ({len(data['groups'])})"


class TestBulkDeleteWithDuplicates:
    """Test bulk delete endpoint works with duplicate question IDs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_bulk_delete_with_fake_ids(self, admin_token):
        """Test bulk delete with fake IDs returns deleted: 0"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        fake_ids = ["fake-id-1", "fake-id-2", "fake-id-3"]
        response = requests.post(
            f"{BASE_URL}/api/admin/questions/bulk-delete",
            json={"question_ids": fake_ids},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 0, f"Expected 0 deleted, got {data['deleted']}"
    
    def test_bulk_delete_empty_array(self, admin_token):
        """Test bulk delete with empty array returns 400"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/questions/bulk-delete",
            json={"question_ids": []},
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
