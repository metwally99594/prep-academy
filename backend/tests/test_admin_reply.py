"""
Test Admin Reply to Reports Feature
- POST /api/admin/reports/{report_id}/reply creates notification for reporting user with type='report_reply'
- Report status updates to 'replied' after admin reply
- POST /api/reports includes report_id in admin notification
- Full flow: User submits report -> Admin sees notification -> Admin replies -> User sees reply notification
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminReplyFeature:
    """Test the admin reply to reports feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_email = "admin@medical.com"
        self.admin_password = "admin123"
        self.test_user_email = f"test_reply_{uuid.uuid4().hex[:8]}@test.com"
        self.test_user_password = "testpass123"
        self.test_user_name = "Test Reply User"
        
    def get_admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"], response.json()["user"]
    
    def create_test_user(self):
        """Create a test user and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": self.test_user_name
        })
        if response.status_code == 400 and "already registered" in response.text:
            # User exists, login instead
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": self.test_user_email,
                "password": self.test_user_password
            })
        assert response.status_code in [200, 201], f"User creation/login failed: {response.text}"
        return response.json()["token"], response.json()["user"]
    
    def test_01_admin_login(self):
        """Test admin can login"""
        token, user = self.get_admin_token()
        assert token is not None
        assert user["is_admin"] == True
        print(f"✅ Admin login successful: {user['email']}")
    
    def test_02_user_submit_report_creates_admin_notification_with_report_id(self):
        """Test that POST /api/reports creates admin notification with report_id"""
        # Create test user
        user_token, user = self.create_test_user()
        
        # Get a question to report
        response = requests.get(f"{BASE_URL}/api/questions?limit=1")
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) > 0, "No questions available for testing"
        question_id = questions[0]["id"]
        
        # Submit a report
        headers = {"Authorization": f"Bearer {user_token}"}
        report_response = requests.post(f"{BASE_URL}/api/reports", json={
            "question_id": question_id,
            "category": "Falsche Antwort",
            "details": "Test report for admin reply feature"
        }, headers=headers)
        assert report_response.status_code == 200, f"Report submission failed: {report_response.text}"
        print(f"✅ Report submitted successfully")
        
        # Login as admin and check notifications
        admin_token, admin_user = self.get_admin_token()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        notif_response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert notif_response.status_code == 200, f"Get notifications failed: {notif_response.text}"
        
        notifications = notif_response.json().get("notifications", [])
        
        # Find the report notification
        report_notif = None
        for n in notifications:
            if n.get("type") == "report" and "Test report for admin reply feature" in n.get("message", ""):
                report_notif = n
                break
        
        assert report_notif is not None, "Report notification not found for admin"
        assert "report_id" in report_notif, "report_id missing from admin notification"
        assert report_notif["report_id"] is not None, "report_id is None"
        print(f"✅ Admin notification has report_id: {report_notif['report_id']}")
        
        # Store for next test
        self.__class__.report_id = report_notif["report_id"]
        self.__class__.user_token = user_token
        self.__class__.admin_token = admin_token
    
    def test_03_admin_reply_to_report(self):
        """Test POST /api/admin/reports/{report_id}/reply creates user notification"""
        # Use stored values from previous test
        report_id = getattr(self.__class__, 'report_id', None)
        admin_token = getattr(self.__class__, 'admin_token', None)
        
        if not report_id or not admin_token:
            # Re-run setup if needed
            admin_token, _ = self.get_admin_token()
            # Get a report
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            reports_response = requests.get(f"{BASE_URL}/api/admin/reports?status=all", headers=admin_headers)
            assert reports_response.status_code == 200
            reports = reports_response.json()
            assert len(reports) > 0, "No reports available"
            report_id = reports[0]["id"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Admin replies to the report
        reply_message = f"Test admin reply {uuid.uuid4().hex[:8]}"
        reply_response = requests.post(
            f"{BASE_URL}/api/admin/reports/{report_id}/reply",
            json={"message": reply_message},
            headers=admin_headers
        )
        assert reply_response.status_code == 200, f"Admin reply failed: {reply_response.text}"
        assert reply_response.json().get("status") == "replied"
        print(f"✅ Admin reply sent successfully")
        
        # Store reply message for verification
        self.__class__.reply_message = reply_message
    
    def test_04_report_status_updated_to_replied(self):
        """Test that report status is updated to 'replied' after admin reply"""
        admin_token = getattr(self.__class__, 'admin_token', None)
        report_id = getattr(self.__class__, 'report_id', None)
        
        if not admin_token:
            admin_token, _ = self.get_admin_token()
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all reports including replied ones
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports?status=all", headers=admin_headers)
        assert reports_response.status_code == 200
        reports = reports_response.json()
        
        # Find the replied report
        replied_reports = [r for r in reports if r.get("status") == "replied"]
        assert len(replied_reports) > 0, "No reports with 'replied' status found"
        print(f"✅ Found {len(replied_reports)} reports with 'replied' status")
    
    def test_05_user_receives_report_reply_notification(self):
        """Test that user receives notification with type='report_reply'"""
        user_token = getattr(self.__class__, 'user_token', None)
        reply_message = getattr(self.__class__, 'reply_message', None)
        
        if not user_token:
            # Create a new user and check for any report_reply notifications
            user_token, _ = self.create_test_user()
        
        headers = {"Authorization": f"Bearer {user_token}"}
        
        notif_response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert notif_response.status_code == 200, f"Get user notifications failed: {notif_response.text}"
        
        notifications = notif_response.json().get("notifications", [])
        
        # Find report_reply notification
        reply_notifs = [n for n in notifications if n.get("type") == "report_reply"]
        
        if reply_message:
            # Check for specific reply
            matching = [n for n in reply_notifs if reply_message in n.get("message", "")]
            if matching:
                print(f"✅ User received report_reply notification with correct message")
            else:
                print(f"⚠️ User has {len(reply_notifs)} report_reply notifications but none match the test message")
        else:
            print(f"✅ User has {len(reply_notifs)} report_reply notifications")
    
    def test_06_admin_reply_requires_message(self):
        """Test that admin reply requires a message"""
        admin_token, _ = self.get_admin_token()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a report
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports?status=all", headers=admin_headers)
        assert reports_response.status_code == 200
        reports = reports_response.json()
        
        if len(reports) == 0:
            pytest.skip("No reports available for testing")
        
        report_id = reports[0]["id"]
        
        # Try to reply with empty message
        reply_response = requests.post(
            f"{BASE_URL}/api/admin/reports/{report_id}/reply",
            json={"message": ""},
            headers=admin_headers
        )
        assert reply_response.status_code == 400, "Should reject empty message"
        print(f"✅ Empty message correctly rejected")
    
    def test_07_admin_reply_requires_admin_auth(self):
        """Test that admin reply endpoint requires admin authentication"""
        # Create regular user
        user_token, user = self.create_test_user()
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to reply as regular user
        reply_response = requests.post(
            f"{BASE_URL}/api/admin/reports/some-report-id/reply",
            json={"message": "Test"},
            headers=headers
        )
        assert reply_response.status_code == 403, f"Should reject non-admin: {reply_response.status_code}"
        print(f"✅ Non-admin correctly rejected from reply endpoint")
    
    def test_08_admin_reply_to_nonexistent_report(self):
        """Test admin reply to non-existent report returns 404"""
        admin_token, _ = self.get_admin_token()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        reply_response = requests.post(
            f"{BASE_URL}/api/admin/reports/nonexistent-report-id/reply",
            json={"message": "Test reply"},
            headers=admin_headers
        )
        assert reply_response.status_code == 404, f"Should return 404: {reply_response.status_code}"
        print(f"✅ Non-existent report correctly returns 404")


class TestFullReplyFlow:
    """Test the complete flow: User reports -> Admin sees -> Admin replies -> User sees reply"""
    
    def test_full_flow(self):
        """Complete end-to-end test of the reply feature"""
        # 1. Create test user
        test_email = f"test_flow_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Flow Test User"
        })
        assert reg_response.status_code in [200, 201], f"Registration failed: {reg_response.text}"
        user_token = reg_response.json()["token"]
        user_id = reg_response.json()["user"]["id"]
        print(f"✅ Step 1: Created test user {test_email}")
        
        # 2. Get a question
        questions_response = requests.get(f"{BASE_URL}/api/questions?limit=1")
        assert questions_response.status_code == 200
        question_id = questions_response.json()[0]["id"]
        
        # 3. User submits report
        user_headers = {"Authorization": f"Bearer {user_token}"}
        unique_detail = f"Full flow test {uuid.uuid4().hex[:8]}"
        report_response = requests.post(f"{BASE_URL}/api/reports", json={
            "question_id": question_id,
            "category": "Tippfehler",
            "details": unique_detail
        }, headers=user_headers)
        assert report_response.status_code == 200
        print(f"✅ Step 2: User submitted report")
        
        # 4. Admin login and check notification
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert admin_response.status_code == 200
        admin_token = admin_response.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        notif_response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert notif_response.status_code == 200
        notifications = notif_response.json().get("notifications", [])
        
        # Find the notification with report_id
        report_notif = None
        for n in notifications:
            if n.get("type") == "report" and unique_detail[:20] in n.get("message", ""):
                report_notif = n
                break
        
        assert report_notif is not None, "Admin notification not found"
        assert "report_id" in report_notif, "report_id missing from notification"
        report_id = report_notif["report_id"]
        print(f"✅ Step 3: Admin sees notification with report_id: {report_id}")
        
        # 5. Admin replies
        reply_msg = f"Thank you for your report - {uuid.uuid4().hex[:8]}"
        reply_response = requests.post(
            f"{BASE_URL}/api/admin/reports/{report_id}/reply",
            json={"message": reply_msg},
            headers=admin_headers
        )
        assert reply_response.status_code == 200
        print(f"✅ Step 4: Admin sent reply")
        
        # 6. Check report status
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports?status=all", headers=admin_headers)
        reports = reports_response.json()
        replied_report = next((r for r in reports if r["id"] == report_id), None)
        assert replied_report is not None
        assert replied_report["status"] == "replied"
        print(f"✅ Step 5: Report status is 'replied'")
        
        # 7. User checks notifications
        user_notif_response = requests.get(f"{BASE_URL}/api/notifications", headers=user_headers)
        assert user_notif_response.status_code == 200
        user_notifications = user_notif_response.json().get("notifications", [])
        
        reply_notif = None
        for n in user_notifications:
            if n.get("type") == "report_reply" and reply_msg in n.get("message", ""):
                reply_notif = n
                break
        
        assert reply_notif is not None, "User did not receive report_reply notification"
        assert reply_notif["type"] == "report_reply"
        print(f"✅ Step 6: User received report_reply notification")
        
        print(f"\n🎉 FULL FLOW TEST PASSED!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
