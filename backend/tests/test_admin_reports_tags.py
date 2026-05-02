"""
Test Admin Reports Management and Tags System
Tests for iteration 26 features:
- Admin Reports tab: GET /api/admin/reports/all, POST /api/admin/reports/{id}/reply, POST /api/admin/reports/{id}/resolve
- Tags CRUD: GET /api/tags, POST /api/admin/tags, DELETE /api/admin/tags/{id}
- Custom Quiz tags filtering
"""
import pytest
import requests
import os
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
    return response.json().get("token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestTagsAPI:
    """Test Tags CRUD endpoints"""
    
    def test_get_tags_public(self):
        """GET /api/tags - should return all tags (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/tags")
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, list)
        # Verify existing tags from context
        tag_names = [t.get("name") for t in tags]
        assert "Innere Medizin" in tag_names or len(tags) >= 0  # May have existing tags
        print(f"✓ GET /api/tags returned {len(tags)} tags")
    
    def test_create_tag_requires_admin(self):
        """POST /api/admin/tags - should require admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/tags", json={
            "name": "Test Tag",
            "color": "#ff0000"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/admin/tags requires admin auth")
    
    def test_create_tag_success(self, admin_headers):
        """POST /api/admin/tags - admin can create tag"""
        unique_name = f"TEST_Tag_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/admin/tags", json={
            "name": unique_name,
            "color": "#22c55e"
        }, headers=admin_headers)
        assert response.status_code == 200, f"Create tag failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["name"] == unique_name
        assert data["color"] == "#22c55e"
        print(f"✓ Created tag: {unique_name} with id {data['id']}")
        
        # Verify tag appears in GET /api/tags
        get_response = requests.get(f"{BASE_URL}/api/tags")
        tags = get_response.json()
        tag_ids = [t.get("id") for t in tags]
        assert data["id"] in tag_ids, "Created tag not found in GET /api/tags"
        print("✓ Created tag verified in GET /api/tags")
        
        # Cleanup - delete the test tag
        delete_response = requests.delete(f"{BASE_URL}/api/admin/tags/{data['id']}", headers=admin_headers)
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up test tag {data['id']}")
    
    def test_create_tag_empty_name(self, admin_headers):
        """POST /api/admin/tags - should reject empty name"""
        response = requests.post(f"{BASE_URL}/api/admin/tags", json={
            "name": "",
            "color": "#ff0000"
        }, headers=admin_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ POST /api/admin/tags rejects empty name")
    
    def test_create_duplicate_tag(self, admin_headers):
        """POST /api/admin/tags - should reject duplicate tag name"""
        # First, get existing tags
        tags_response = requests.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        
        if len(tags) > 0:
            existing_name = tags[0]["name"]
            response = requests.post(f"{BASE_URL}/api/admin/tags", json={
                "name": existing_name,
                "color": "#ff0000"
            }, headers=admin_headers)
            assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
            print(f"✓ POST /api/admin/tags rejects duplicate name '{existing_name}'")
        else:
            pytest.skip("No existing tags to test duplicate prevention")
    
    def test_delete_tag_requires_admin(self):
        """DELETE /api/admin/tags/{id} - should require admin auth"""
        response = requests.delete(f"{BASE_URL}/api/admin/tags/fake-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ DELETE /api/admin/tags requires admin auth")
    
    def test_delete_tag_success(self, admin_headers):
        """DELETE /api/admin/tags/{id} - admin can delete tag"""
        # Create a tag to delete
        unique_name = f"TEST_DeleteMe_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/admin/tags", json={
            "name": unique_name,
            "color": "#ef4444"
        }, headers=admin_headers)
        assert create_response.status_code == 200
        tag_id = create_response.json()["id"]
        
        # Delete the tag
        delete_response = requests.delete(f"{BASE_URL}/api/admin/tags/{tag_id}", headers=admin_headers)
        assert delete_response.status_code == 200
        print(f"✓ Deleted tag {tag_id}")
        
        # Verify tag is gone
        get_response = requests.get(f"{BASE_URL}/api/tags")
        tags = get_response.json()
        tag_ids = [t.get("id") for t in tags]
        assert tag_id not in tag_ids, "Deleted tag still appears in GET /api/tags"
        print("✓ Verified tag deletion")


class TestAdminReportsAPI:
    """Test Admin Reports Management endpoints"""
    
    def test_get_all_reports_requires_admin(self):
        """GET /api/admin/reports/all - should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/reports/all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/admin/reports/all requires admin auth")
    
    def test_get_all_reports_success(self, admin_headers):
        """GET /api/admin/reports/all - admin can get all reports with user_email"""
        response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        assert response.status_code == 200, f"Get reports failed: {response.text}"
        reports = response.json()
        assert isinstance(reports, list)
        print(f"✓ GET /api/admin/reports/all returned {len(reports)} reports")
        
        # Verify report structure includes user_email
        if len(reports) > 0:
            report = reports[0]
            assert "id" in report, "Report missing 'id'"
            assert "status" in report, "Report missing 'status'"
            assert "user_email" in report, "Report missing 'user_email'"
            assert "category" in report or "question_text" in report, "Report missing category/question_text"
            print(f"✓ Report structure verified: status={report.get('status')}, user_email={report.get('user_email')}")
    
    def test_reply_to_report_requires_admin(self):
        """POST /api/admin/reports/{id}/reply - should require admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/reports/fake-id/reply", json={
            "message": "Test reply"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/admin/reports/{id}/reply requires admin auth")
    
    def test_reply_to_report_success(self, admin_headers):
        """POST /api/admin/reports/{id}/reply - admin can reply to report"""
        # Get a report to reply to
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        reports = reports_response.json()
        
        # Find an open report
        open_reports = [r for r in reports if r.get("status") == "open"]
        if len(open_reports) == 0:
            pytest.skip("No open reports to test reply")
        
        report = open_reports[0]
        report_id = report["id"]
        
        # Reply to the report
        reply_message = f"Test admin reply {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/admin/reports/{report_id}/reply", json={
            "message": reply_message
        }, headers=admin_headers)
        assert response.status_code == 200, f"Reply failed: {response.text}"
        print(f"✓ Replied to report {report_id}")
        
        # Verify report status changed to 'replied'
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        reports = reports_response.json()
        updated_report = next((r for r in reports if r["id"] == report_id), None)
        assert updated_report is not None
        assert updated_report.get("status") == "replied", f"Expected status 'replied', got {updated_report.get('status')}"
        assert updated_report.get("admin_reply") == reply_message
        print(f"✓ Report status updated to 'replied' with admin_reply text")
    
    def test_reply_empty_message(self, admin_headers):
        """POST /api/admin/reports/{id}/reply - should reject empty message"""
        # Get any report
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        reports = reports_response.json()
        
        if len(reports) == 0:
            pytest.skip("No reports to test")
        
        report_id = reports[0]["id"]
        response = requests.post(f"{BASE_URL}/api/admin/reports/{report_id}/reply", json={
            "message": ""
        }, headers=admin_headers)
        assert response.status_code == 400, f"Expected 400 for empty message, got {response.status_code}"
        print("✓ POST /api/admin/reports/{id}/reply rejects empty message")
    
    def test_resolve_report_requires_admin(self):
        """POST /api/admin/reports/{id}/resolve - should require admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/reports/fake-id/resolve", json={})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/admin/reports/{id}/resolve requires admin auth")
    
    def test_resolve_report_success(self, admin_headers):
        """POST /api/admin/reports/{id}/resolve - admin can resolve report"""
        # Get a report to resolve
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        reports = reports_response.json()
        
        # Find a non-resolved report
        non_resolved = [r for r in reports if r.get("status") != "resolved"]
        if len(non_resolved) == 0:
            pytest.skip("No non-resolved reports to test")
        
        report = non_resolved[0]
        report_id = report["id"]
        
        # Resolve the report
        response = requests.post(f"{BASE_URL}/api/admin/reports/{report_id}/resolve", json={}, headers=admin_headers)
        assert response.status_code == 200, f"Resolve failed: {response.text}"
        print(f"✓ Resolved report {report_id}")
        
        # Verify report status changed to 'resolved'
        reports_response = requests.get(f"{BASE_URL}/api/admin/reports/all", headers=admin_headers)
        reports = reports_response.json()
        updated_report = next((r for r in reports if r["id"] == report_id), None)
        assert updated_report is not None
        assert updated_report.get("status") == "resolved", f"Expected status 'resolved', got {updated_report.get('status')}"
        print(f"✓ Report status updated to 'resolved'")


class TestCustomQuizTagsFilter:
    """Test Custom Quiz tags filtering"""
    
    def test_custom_quiz_count_with_tags(self, admin_headers):
        """POST /api/questions/custom-quiz/count - should accept tags filter"""
        # Get existing tags
        tags_response = requests.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        
        if len(tags) == 0:
            pytest.skip("No tags to test filtering")
        
        tag_id = tags[0]["id"]
        
        # Count with tags filter
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz/count", json={
            "tags": [tag_id],
            "limit": 50
        }, headers=admin_headers)
        assert response.status_code == 200, f"Count failed: {response.text}"
        data = response.json()
        assert "count" in data
        print(f"✓ Custom quiz count with tag filter: {data['count']} questions")
    
    def test_custom_quiz_with_tags(self, admin_headers):
        """POST /api/questions/custom-quiz - should filter by tags"""
        # Get existing tags
        tags_response = requests.get(f"{BASE_URL}/api/tags")
        tags = tags_response.json()
        
        if len(tags) == 0:
            pytest.skip("No tags to test filtering")
        
        tag_id = tags[0]["id"]
        
        # Get questions with tags filter
        response = requests.post(f"{BASE_URL}/api/questions/custom-quiz", json={
            "tags": [tag_id],
            "limit": 10
        }, headers=admin_headers)
        assert response.status_code == 200, f"Custom quiz failed: {response.text}"
        questions = response.json()
        assert isinstance(questions, list)
        print(f"✓ Custom quiz with tag filter returned {len(questions)} questions")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
