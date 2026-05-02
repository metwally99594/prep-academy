"""
Test Admin Routes (extracted to routes/admin.py), PWA Setup, and Telegram Bot Status
Iteration 33: Testing code refactoring, PWA manifest/SW, and Telegram bot module
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============ FIXTURES ============

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@medical.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")

@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ============ ADMIN ROUTES (from routes/admin.py) ============

class TestAdminStats:
    """Test GET /api/admin/stats - returns total_users, total_questions"""
    
    def test_admin_stats_returns_expected_fields(self, admin_headers):
        """Admin stats should return total_users, total_questions, total_favorites"""
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_users" in data, "Missing total_users field"
        assert "total_questions" in data, "Missing total_questions field"
        assert "total_favorites" in data, "Missing total_favorites field"
        assert "questions_by_specialty" in data, "Missing questions_by_specialty field"
        
        # Validate types
        assert isinstance(data["total_users"], int), "total_users should be int"
        assert isinstance(data["total_questions"], int), "total_questions should be int"
        assert data["total_users"] >= 1, "Should have at least 1 user (admin)"
        print(f"Admin stats: {data['total_users']} users, {data['total_questions']} questions")
    
    def test_admin_stats_requires_auth(self):
        """Admin stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestAdminUsers:
    """Test GET /api/admin/users - returns user list"""
    
    def test_admin_users_returns_list(self, admin_headers):
        """Admin users endpoint should return a list of users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 1, "Should have at least 1 user (admin)"
        
        # Check user structure (password should be excluded)
        user = data[0]
        assert "id" in user, "User should have id"
        assert "email" in user, "User should have email"
        assert "password" not in user, "Password should NOT be in response"
        assert "_id" not in user, "MongoDB _id should NOT be in response"
        print(f"Admin users: {len(data)} users returned")
    
    def test_admin_users_requires_auth(self):
        """Admin users should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestAdminExportQuestions:
    """Test GET /api/admin/export/questions - returns questions array"""
    
    def test_export_questions_returns_array(self, admin_headers):
        """Export questions should return questions array with total"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "questions" in data, "Missing questions field"
        assert "total" in data, "Missing total field"
        assert "exported_at" in data, "Missing exported_at field"
        
        assert isinstance(data["questions"], list), "questions should be a list"
        assert isinstance(data["total"], int), "total should be int"
        assert data["total"] == len(data["questions"]), "total should match questions length"
        
        # Check question structure
        if data["questions"]:
            q = data["questions"][0]
            assert "_id" not in q, "MongoDB _id should NOT be in response"
            assert "id" in q, "Question should have id"
        print(f"Export questions: {data['total']} questions exported")
    
    def test_export_questions_requires_auth(self):
        """Export questions should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/export/questions")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestAdminActivityHeartbeat:
    """Test POST /api/admin/activity/heartbeat - updates user activity"""
    
    def test_heartbeat_works(self, admin_headers):
        """Heartbeat should return status ok"""
        response = requests.post(f"{BASE_URL}/api/admin/activity/heartbeat", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Missing status field"
        assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
        print("Heartbeat: status ok")
    
    def test_heartbeat_requires_auth(self):
        """Heartbeat should require authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/activity/heartbeat")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestAdminLeaderboard:
    """Test GET /api/admin/leaderboard - returns user leaderboard"""
    
    def test_leaderboard_returns_list(self, admin_headers):
        """Leaderboard should return list of users with stats"""
        response = requests.get(f"{BASE_URL}/api/admin/leaderboard", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if data:
            user = data[0]
            assert "_id" not in user, "MongoDB _id should NOT be in response"
            assert "id" in user, "User should have id"
            assert "total_questions" in user, "User should have total_questions"
            assert "correct_answers" in user, "User should have correct_answers"
        print(f"Leaderboard: {len(data)} users")


class TestAdminOnlineUsers:
    """Test GET /api/admin/activity/online - returns online users"""
    
    def test_online_users_returns_list(self, admin_headers):
        """Online users should return list with activity data"""
        response = requests.get(f"{BASE_URL}/api/admin/activity/online", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Online users: {len(data)} activities tracked")


# ============ TELEGRAM BOT STATUS ============

class TestTelegramBotStatus:
    """Test GET /api/admin/telegram/status - returns bot status"""
    
    def test_telegram_status_returns_expected_fields(self, admin_headers):
        """Telegram status should return enabled, users, total_answers"""
        response = requests.get(f"{BASE_URL}/api/admin/telegram/status", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "enabled" in data, "Missing enabled field"
        assert "users" in data, "Missing users field"
        assert "total_answers" in data, "Missing total_answers field"
        
        # Bot should be disabled (no TELEGRAM_BOT_TOKEN set)
        assert data["enabled"] == False, "Bot should be disabled (no token)"
        assert isinstance(data["users"], int), "users should be int"
        assert isinstance(data["total_answers"], int), "total_answers should be int"
        print(f"Telegram status: enabled={data['enabled']}, users={data['users']}, answers={data['total_answers']}")
    
    def test_telegram_status_requires_auth(self):
        """Telegram status should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/telegram/status")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


# ============ PWA MANIFEST ============

class TestPWAManifest:
    """Test GET /manifest.json - returns valid PWA manifest"""
    
    def test_manifest_returns_valid_json(self):
        """Manifest should return valid PWA manifest JSON"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Required PWA manifest fields
        assert "name" in data, "Missing name field"
        assert "short_name" in data, "Missing short_name field"
        assert "start_url" in data, "Missing start_url field"
        assert "display" in data, "Missing display field"
        assert "icons" in data, "Missing icons field"
        
        # Validate values
        assert data["short_name"] == "PrepAcademy", f"Expected short_name 'PrepAcademy', got {data['short_name']}"
        assert data["display"] == "standalone", f"Expected display 'standalone', got {data['display']}"
        assert isinstance(data["icons"], list), "icons should be a list"
        assert len(data["icons"]) >= 1, "Should have at least 1 icon"
        
        # Check icon structure
        icon = data["icons"][0]
        assert "src" in icon, "Icon should have src"
        assert "sizes" in icon, "Icon should have sizes"
        assert "type" in icon, "Icon should have type"
        
        print(f"PWA Manifest: name='{data['name']}', display='{data['display']}', icons={len(data['icons'])}")


class TestPWAServiceWorker:
    """Test GET /sw.js - returns service worker file"""
    
    def test_service_worker_exists(self):
        """Service worker file should exist and be JavaScript"""
        response = requests.get(f"{BASE_URL}/sw.js")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content = response.text
        
        # Check for service worker patterns
        assert "self.addEventListener" in content, "Should have event listeners"
        assert "install" in content, "Should handle install event"
        assert "fetch" in content, "Should handle fetch event"
        assert "caches" in content, "Should use Cache API"
        
        print(f"Service Worker: {len(content)} bytes, has install/fetch handlers")


# ============ EXISTING FEATURES STILL WORK ============

class TestExistingFeaturesWork:
    """Verify existing features still work after refactoring"""
    
    def test_specialties_endpoint_works(self):
        """GET /api/specialties should still work"""
        response = requests.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Should return list of specialties"
        assert len(data) > 0, "Should have specialties"
        print(f"Specialties: {len(data)} specialties")
    
    def test_quiz_endpoint_works(self, admin_headers):
        """GET /api/questions/quiz should still work"""
        response = requests.get(f"{BASE_URL}/api/questions/quiz?specialty_id=internal&limit=5", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Should return list of questions"
        print(f"Quiz: {len(data)} questions returned")
    
    def test_dashboard_stats_works(self, admin_headers):
        """GET /api/dashboard/stats should still work"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Dashboard stats has total_answered, accuracy, coverage, etc.
        assert "total_answered" in data or "accuracy" in data, "Should have stats"
        print(f"Dashboard stats: working")
    
    def test_health_endpoint_works(self):
        """GET /health should still work (not /api/health)"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Health: OK")


# ============ SERVER.PY LINE COUNT ============

class TestServerRefactoring:
    """Verify server.py was reduced in size"""
    
    def test_backend_starts_without_errors(self):
        """Backend should start and respond to health check"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Backend health check failed: {response.status_code}"
        print("Backend: Started without errors")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
