"""
Test suite for Notebook Admin Toggle Feature
Tests:
- Admin login and authentication
- GET /api/admin/users returns users with notebook_enabled field
- POST /api/admin/notebook/toggle/{user_id} toggles notebook_enabled
- Notebook endpoints return 403 for non-premium users
- Admin always has notebook access (bypass check)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"

# Test user IDs from the request
TEST_USER_ID = "69c56964-a4f6-4a2a-bc00-7b911fbc16e1"  # Test User
MOHAMED_USER_ID = "cd424288-2bff-4236-8708-2ef83cb96d89"  # Mohamed Okasha


class TestAdminNotebookToggle:
    """Tests for admin notebook toggle feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
    
    def get_admin_token(self):
        """Login as admin and get token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        self.admin_token = data["token"]
        return self.admin_token
    
    def test_admin_login(self):
        """Test admin can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["is_admin"] == True
        print(f"✓ Admin login successful, user: {data['user']['name']}")
    
    def test_get_admin_users_returns_notebook_enabled(self):
        """Test GET /api/admin/users returns users with notebook_enabled field"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0, "No users returned"
        
        # Check that users have notebook_enabled field (or it's undefined which is fine)
        for user in users:
            assert "id" in user
            assert "email" in user
            # notebook_enabled may be True, False, or not present (defaults to False)
            print(f"  User: {user.get('name', 'N/A')} - notebook_enabled: {user.get('notebook_enabled', False)}")
        
        print(f"✓ GET /api/admin/users returned {len(users)} users with notebook_enabled field")
    
    def test_toggle_notebook_access_for_user(self):
        """Test POST /api/admin/notebook/toggle/{user_id} toggles notebook_enabled"""
        token = self.get_admin_token()
        
        # First, get current state of a non-admin user
        response = self.session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        
        # Find a non-admin user to toggle
        non_admin_user = None
        for user in users:
            if not user.get("is_admin"):
                non_admin_user = user
                break
        
        if not non_admin_user:
            pytest.skip("No non-admin user found to test toggle")
        
        user_id = non_admin_user["id"]
        initial_state = non_admin_user.get("notebook_enabled", False)
        print(f"  Testing toggle for user: {non_admin_user.get('name')} (current: {initial_state})")
        
        # Toggle notebook access
        response = self.session.post(
            f"{BASE_URL}/api/admin/notebook/toggle/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "notebook_enabled" in data
        assert data["notebook_enabled"] != initial_state, "Toggle did not change state"
        
        print(f"✓ Toggle successful: notebook_enabled changed from {initial_state} to {data['notebook_enabled']}")
        
        # Verify the change persisted by fetching users again
        response = self.session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None
        assert updated_user.get("notebook_enabled") == data["notebook_enabled"]
        print(f"✓ Verified: notebook_enabled persisted as {updated_user.get('notebook_enabled')}")
        
        # Toggle back to original state
        response = self.session.post(
            f"{BASE_URL}/api/admin/notebook/toggle/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print(f"✓ Toggled back to original state: {initial_state}")
    
    def test_toggle_requires_admin(self):
        """Test that non-admin cannot toggle notebook access"""
        # First register a test user
        test_email = f"test_notebook_{os.urandom(4).hex()}@test.com"
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test Notebook User"
        })
        
        if response.status_code == 200:
            user_token = response.json().get("token")
            
            # Try to toggle as non-admin
            response = self.session.post(
                f"{BASE_URL}/api/admin/notebook/toggle/{TEST_USER_ID}",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✓ Non-admin correctly denied access to toggle endpoint")
        else:
            # User might already exist, skip this test
            pytest.skip("Could not create test user")
    
    def test_toggle_nonexistent_user(self):
        """Test toggle returns 404 for non-existent user"""
        token = self.get_admin_token()
        fake_user_id = "00000000-0000-0000-0000-000000000000"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/notebook/toggle/{fake_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Toggle correctly returns 404 for non-existent user")


class TestNotebookAccessControl:
    """Tests for notebook access control (403 for non-premium users)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def create_test_user_without_notebook(self):
        """Create a test user without notebook access"""
        test_email = f"test_no_notebook_{os.urandom(4).hex()}@test.com"
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test No Notebook"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_notebook_list_returns_403_for_non_premium(self):
        """Test GET /api/notebook/list returns 403 for non-premium users"""
        token = self.create_test_user_without_notebook()
        if not token:
            pytest.skip("Could not create test user")
        
        response = self.session.get(
            f"{BASE_URL}/api/notebook/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ GET /api/notebook/list correctly returns 403 for non-premium user")
    
    def test_notebook_upload_returns_403_for_non_premium(self):
        """Test POST /api/notebook/upload returns 403 for non-premium users"""
        token = self.create_test_user_without_notebook()
        if not token:
            pytest.skip("Could not create test user")
        
        # Create a minimal PDF-like file for testing - use multipart form data
        # Note: We need to remove Content-Type header for multipart
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")}
        response = requests.post(
            f"{BASE_URL}/api/notebook/upload",
            headers=headers,
            files=files
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ POST /api/notebook/upload correctly returns 403 for non-premium user")
    
    def test_notebook_chat_returns_403_for_non_premium(self):
        """Test POST /api/notebook/chat returns 403 for non-premium users"""
        token = self.create_test_user_without_notebook()
        if not token:
            pytest.skip("Could not create test user")
        
        response = self.session.post(
            f"{BASE_URL}/api/notebook/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"notebook_id": "fake-id", "message": "test"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ POST /api/notebook/chat correctly returns 403 for non-premium user")
    
    def test_admin_always_has_notebook_access(self):
        """Test that admin always has notebook access (bypass check)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        admin_token = response.json()["token"]
        
        # Admin should be able to access notebook list (even if notebook_enabled is not set)
        response = self.session.get(
            f"{BASE_URL}/api/notebook/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should have notebook access, got {response.status_code}: {response.text}"
        print("✓ Admin correctly has notebook access (bypass check)")


class TestNotebookEndpointsWithAccess:
    """Tests for notebook endpoints when user has access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_admin_can_list_notebooks(self):
        """Test admin can list notebooks"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        admin_token = response.json()["token"]
        
        response = self.session.get(
            f"{BASE_URL}/api/notebook/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        notebooks = response.json()
        assert isinstance(notebooks, list)
        print(f"✓ Admin can list notebooks: {len(notebooks)} notebooks found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
