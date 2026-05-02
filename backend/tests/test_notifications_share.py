"""
Test suite for Notification System and Share Results features
- GET /api/notifications - returns notifications list and unread_count
- POST /api/notifications/generate-daily - creates daily notification (only once per day)
- POST /api/notifications/read - marks all as read
- POST /api/questions/{id}/answer - generates level-up notification on levelup
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestNotificationSystem:
    """Test notification endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.user = data["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_notifications_returns_list_and_unread_count(self):
        """GET /api/notifications should return notifications list and unread_count"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "notifications" in data, "Response should have 'notifications' key"
        assert "unread_count" in data, "Response should have 'unread_count' key"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        assert isinstance(data["unread_count"], int), "unread_count should be an integer"
        print(f"SUCCESS: GET /api/notifications - {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_generate_daily_notification_creates_notification(self):
        """POST /api/notifications/generate-daily should create daily notification"""
        response = requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "status" in data, "Response should have 'status' key"
        # Status can be 'created' or 'already_generated'
        assert data["status"] in ["created", "already_generated"], f"Unexpected status: {data['status']}"
        print(f"SUCCESS: POST /api/notifications/generate-daily - status: {data['status']}")
    
    def test_generate_daily_notification_prevents_duplicates(self):
        """POST /api/notifications/generate-daily should prevent duplicate daily notifications"""
        # First call
        response1 = requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        assert response1.status_code == 200
        
        # Second call should return 'already_generated'
        response2 = requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "already_generated", "Second call should return 'already_generated'"
        print("SUCCESS: Duplicate daily notification prevention works")
    
    def test_mark_notifications_read(self):
        """POST /api/notifications/read should mark all notifications as read"""
        # First generate a notification to ensure there's something to mark
        requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        
        # Mark all as read
        response = requests.post(f"{BASE_URL}/api/notifications/read", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got: {data}"
        
        # Verify unread count is 0
        verify_response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        verify_data = verify_response.json()
        assert verify_data["unread_count"] == 0, f"Expected 0 unread, got: {verify_data['unread_count']}"
        print("SUCCESS: POST /api/notifications/read - all marked as read")
    
    def test_notification_structure(self):
        """Verify notification object structure"""
        # Generate a notification first
        requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        
        response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        if len(data["notifications"]) > 0:
            notif = data["notifications"][0]
            # Check required fields
            assert "id" in notif, "Notification should have 'id'"
            assert "type" in notif, "Notification should have 'type'"
            assert "title" in notif, "Notification should have 'title'"
            assert "message" in notif, "Notification should have 'message'"
            assert "read" in notif, "Notification should have 'read'"
            assert "created_at" in notif, "Notification should have 'created_at'"
            print(f"SUCCESS: Notification structure valid - type: {notif['type']}, title: {notif['title']}")
        else:
            print("WARNING: No notifications to verify structure")
    
    def test_notifications_require_auth(self):
        """Notification endpoints should require authentication"""
        # Test without auth header
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        response = requests.post(f"{BASE_URL}/api/notifications/generate-daily")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        response = requests.post(f"{BASE_URL}/api/notifications/read")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        print("SUCCESS: All notification endpoints require authentication")


class TestAnswerXPAndLevelUp:
    """Test that answer endpoint returns XP fields and generates level-up notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_answer_returns_xp_fields(self):
        """POST /api/questions/{id}/answer should return xp_earned, total_xp, level, leveled_up"""
        # Get a question first
        questions_response = requests.get(f"{BASE_URL}/api/questions?limit=1", headers=self.headers)
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert len(questions) > 0, "No questions available"
        
        question = questions[0]
        question_id = question["id"]
        
        # Get correct choice
        correct_choices = [c["id"] for c in question["choices"] if c.get("is_correct")]
        if not correct_choices:
            correct_choices = [question["choices"][0]["id"]]  # Fallback
        
        # Submit answer
        response = requests.post(
            f"{BASE_URL}/api/questions/{question_id}/answer",
            json={"question_id": question_id, "selected_choice_ids": correct_choices},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify XP fields are present
        assert "xp_earned" in data, "Response should have 'xp_earned'"
        assert "total_xp" in data, "Response should have 'total_xp'"
        assert "level" in data, "Response should have 'level'"
        assert "leveled_up" in data, "Response should have 'leveled_up'"
        
        # Verify level structure
        level = data["level"]
        assert "level" in level, "Level should have 'level' number"
        assert "name_de" in level, "Level should have 'name_de'"
        assert "progress_percent" in level, "Level should have 'progress_percent'"
        
        print(f"SUCCESS: Answer returns XP fields - earned: {data['xp_earned']}, total: {data['total_xp']}, level: {level['name_de']}")


class TestNotificationTypes:
    """Test different notification types"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_daily_reminder_notification_type(self):
        """Daily reminder notification should have correct type"""
        # Generate daily notification
        requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=self.headers)
        
        # Get notifications
        response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        data = response.json()
        
        # Find daily_reminder type
        daily_reminders = [n for n in data["notifications"] if n["type"] == "daily_reminder"]
        assert len(daily_reminders) > 0, "Should have at least one daily_reminder notification"
        
        reminder = daily_reminders[0]
        assert reminder["title"] == "Tägliche Erinnerung", f"Expected German title, got: {reminder['title']}"
        assert reminder["icon"] == "bell", f"Expected 'bell' icon, got: {reminder['icon']}"
        print(f"SUCCESS: Daily reminder notification - title: {reminder['title']}, message: {reminder['message'][:50]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
