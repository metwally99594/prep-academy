"""
Test suite for Meine Notizen (My Notes) and Melden (Report) features
- GET /api/notes/all - Get all user notes with question text
- DELETE /api/notes/{question_id} - Delete a specific note
- POST /api/reports - Submit a report and create admin notification
- GET /api/notifications - Check admin notifications
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_EMAIL = f"test_notes_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "testpass123"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["is_admin"] == True
        print(f"PASS: Admin login successful")
        return data["token"]
    
    def test_register_test_user(self):
        """Register a test user for notes testing"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": "Test Notes User"
        })
        # May already exist, so accept 200 or 400
        if response.status_code == 200:
            print(f"PASS: Test user registered: {TEST_USER_EMAIL}")
            return response.json()["token"]
        elif response.status_code == 400:
            # User exists, try login
            login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            if login_resp.status_code == 200:
                print(f"PASS: Test user already exists, logged in")
                return login_resp.json()["token"]
        assert False, f"Failed to register/login test user: {response.text}"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture(scope="module")
def test_user_token():
    """Get or create test user token"""
    # Try to register
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "name": "Test Notes User"
    })
    if response.status_code == 200:
        return response.json()["token"]
    # User exists, login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture(scope="module")
def sample_question_id(admin_token):
    """Get a sample question ID for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/questions?limit=1", headers=headers)
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) > 0, "No questions found in database"
    return questions[0]["id"]


class TestNotesAll:
    """Tests for GET /api/notes/all endpoint"""
    
    def test_get_all_notes_empty(self, test_user_token):
        """Test getting notes when user has none"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/notes/all", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: GET /api/notes/all returns list (count: {len(data)})")
    
    def test_get_all_notes_unauthorized(self):
        """Test getting notes without auth"""
        response = requests.get(f"{BASE_URL}/api/notes/all")
        assert response.status_code == 401, "Should require authentication"
        print("PASS: GET /api/notes/all requires authentication")


class TestNotesCreateAndRetrieve:
    """Tests for creating notes and retrieving them"""
    
    def test_create_note_and_retrieve(self, test_user_token, sample_question_id):
        """Create a note and verify it appears in /notes/all"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Create a note
        note_text = f"TEST_NOTE_{uuid.uuid4().hex[:8]}: This is a test note for testing"
        response = requests.post(f"{BASE_URL}/api/notes", json={
            "question_id": sample_question_id,
            "text": note_text
        }, headers=headers)
        assert response.status_code == 200, f"Failed to create note: {response.text}"
        print(f"PASS: Created note for question {sample_question_id}")
        
        # Retrieve all notes
        response = requests.get(f"{BASE_URL}/api/notes/all", headers=headers)
        assert response.status_code == 200, f"Failed to get notes: {response.text}"
        notes = response.json()
        
        # Verify note structure
        assert isinstance(notes, list)
        assert len(notes) > 0, "Should have at least one note"
        
        # Find our note
        our_note = next((n for n in notes if n.get("question_id") == sample_question_id), None)
        assert our_note is not None, "Created note not found in /notes/all"
        
        # Verify note fields
        assert "question_text" in our_note, "Note should have question_text"
        assert "specialty_id" in our_note, "Note should have specialty_id"
        assert "text" in our_note, "Note should have text"
        assert "updated_at" in our_note, "Note should have updated_at"
        assert our_note["text"] == note_text, "Note text should match"
        
        print(f"PASS: Note retrieved with question_text: {our_note['question_text'][:50]}...")
        print(f"PASS: Note has specialty_id: {our_note['specialty_id']}")
        return sample_question_id


class TestNotesDelete:
    """Tests for DELETE /api/notes/{question_id}"""
    
    def test_delete_note(self, test_user_token, sample_question_id):
        """Test deleting a note"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # First ensure note exists
        note_text = f"TEST_DELETE_NOTE_{uuid.uuid4().hex[:8]}"
        requests.post(f"{BASE_URL}/api/notes", json={
            "question_id": sample_question_id,
            "text": note_text
        }, headers=headers)
        
        # Delete the note
        response = requests.delete(f"{BASE_URL}/api/notes/{sample_question_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete note: {response.text}"
        data = response.json()
        assert data.get("status") == "deleted", "Should return deleted status"
        print(f"PASS: DELETE /api/notes/{sample_question_id} successful")
        
        # Verify note is gone from /notes/all
        response = requests.get(f"{BASE_URL}/api/notes/all", headers=headers)
        assert response.status_code == 200
        notes = response.json()
        our_note = next((n for n in notes if n.get("question_id") == sample_question_id), None)
        assert our_note is None, "Deleted note should not appear in /notes/all"
        print("PASS: Deleted note no longer appears in /notes/all")
    
    def test_delete_note_unauthorized(self, sample_question_id):
        """Test deleting note without auth"""
        response = requests.delete(f"{BASE_URL}/api/notes/{sample_question_id}")
        assert response.status_code == 401, "Should require authentication"
        print("PASS: DELETE /api/notes requires authentication")


class TestReports:
    """Tests for POST /api/reports and admin notifications"""
    
    def test_submit_report(self, test_user_token, sample_question_id):
        """Test submitting a report"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        report_data = {
            "question_id": sample_question_id,
            "category": "Falsche Antwort",
            "details": f"TEST_REPORT_{uuid.uuid4().hex[:8]}: Test report details",
            "question_text": "Test question text"
        }
        
        response = requests.post(f"{BASE_URL}/api/reports", json=report_data, headers=headers)
        assert response.status_code == 200, f"Failed to submit report: {response.text}"
        data = response.json()
        assert data.get("status") == "submitted", "Should return submitted status"
        print(f"PASS: POST /api/reports successful with category '{report_data['category']}'")
        return report_data["category"]
    
    def test_submit_report_missing_fields(self, test_user_token):
        """Test submitting report with missing fields"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Missing category
        response = requests.post(f"{BASE_URL}/api/reports", json={
            "question_id": "some-id"
        }, headers=headers)
        assert response.status_code == 400, "Should fail without category"
        print("PASS: POST /api/reports validates required fields")
    
    def test_submit_report_unauthorized(self):
        """Test submitting report without auth"""
        response = requests.post(f"{BASE_URL}/api/reports", json={
            "question_id": "some-id",
            "category": "Test"
        })
        assert response.status_code == 401, "Should require authentication"
        print("PASS: POST /api/reports requires authentication")


class TestAdminNotifications:
    """Tests for admin notifications after report submission"""
    
    def test_admin_receives_report_notification(self, admin_token, test_user_token, sample_question_id):
        """Test that admin receives notification when user submits report"""
        user_headers = {"Authorization": f"Bearer {test_user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Submit a report as test user
        unique_category = f"Test Category {uuid.uuid4().hex[:6]}"
        report_data = {
            "question_id": sample_question_id,
            "category": unique_category,
            "details": "Test report for notification testing",
            "question_text": "Test question"
        }
        
        response = requests.post(f"{BASE_URL}/api/reports", json=report_data, headers=user_headers)
        assert response.status_code == 200, f"Failed to submit report: {response.text}"
        print(f"PASS: Report submitted with category: {unique_category}")
        
        # Check admin notifications
        response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get notifications: {response.text}"
        data = response.json()
        
        assert "notifications" in data, "Response should have notifications"
        assert "unread_count" in data, "Response should have unread_count"
        
        notifications = data["notifications"]
        assert isinstance(notifications, list), "Notifications should be a list"
        
        # Find our notification
        report_notification = None
        for n in notifications:
            if n.get("type") == "report" and unique_category in n.get("title", ""):
                report_notification = n
                break
        
        assert report_notification is not None, f"Admin should have notification for report with category '{unique_category}'"
        assert report_notification.get("type") == "report", "Notification type should be 'report'"
        assert unique_category in report_notification.get("title", ""), "Notification title should contain category"
        assert report_notification.get("read") == False, "Notification should be unread"
        
        print(f"PASS: Admin received notification: {report_notification['title']}")
        print(f"PASS: Notification message: {report_notification.get('message', '')[:80]}...")
    
    def test_get_notifications_structure(self, admin_token):
        """Test notifications endpoint returns correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        print(f"PASS: Notifications structure correct, unread_count: {data['unread_count']}")
    
    def test_mark_notifications_read(self, admin_token):
        """Test marking notifications as read"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/notifications/read", headers=headers)
        assert response.status_code == 200, f"Failed to mark read: {response.text}"
        print("PASS: POST /api/notifications/read successful")
        
        # Verify unread count is 0
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0, "Unread count should be 0 after marking read"
        print("PASS: Unread count is 0 after marking all as read")


class TestAdminReports:
    """Tests for admin reports endpoint"""
    
    def test_get_reports_as_admin(self, admin_token):
        """Test admin can get reports"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reports", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        reports = response.json()
        assert isinstance(reports, list), "Should return list of reports"
        print(f"PASS: GET /api/admin/reports returns {len(reports)} reports")
    
    def test_get_reports_unauthorized(self, test_user_token):
        """Test non-admin cannot get reports"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reports", headers=headers)
        assert response.status_code == 403, "Non-admin should be forbidden"
        print("PASS: GET /api/admin/reports requires admin access")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
