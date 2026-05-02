"""
Test suite for the redesigned Analyzer Page features
Tests: Report type selection, clinical context field, analyze endpoint, history
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"

# Sample base64 image (1x1 pixel PNG)
SAMPLE_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    """Return headers with admin auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAnalyzerEndpoint:
    """Tests for POST /api/analyzer/analyze endpoint"""
    
    def test_analyze_with_clinical_context(self, auth_headers):
        """Test analyzer accepts clinical_context field"""
        response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            headers=auth_headers,
            json={
                "image_base64": SAMPLE_IMAGE,
                "report_type": "ECG",
                "clinical_context": "55-jähriger Mann, Brustschmerzen mit Ausstrahlung in den linken Arm, RR 160/95"
            }
        )
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "analysis" in data
        assert "report_type" in data
        assert data["report_type"] == "ECG"
    
    def test_analyze_without_clinical_context(self, auth_headers):
        """Test analyzer works without clinical_context (optional field)"""
        response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            headers=auth_headers,
            json={
                "image_base64": SAMPLE_IMAGE,
                "report_type": "CT"
            }
        )
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "analysis" in data
        assert data["report_type"] == "CT"
    
    def test_analyze_all_report_types(self, auth_headers):
        """Test analyzer accepts all 6 report types"""
        report_types = ["ECG", "CT", "MRI", "BloodTest", "XRay", "Ultrasound"]
        
        for report_type in report_types:
            response = requests.post(
                f"{BASE_URL}/api/analyzer/analyze",
                headers=auth_headers,
                json={
                    "image_base64": SAMPLE_IMAGE,
                    "report_type": report_type
                }
            )
            assert response.status_code == 200, f"Analyze failed for {report_type}: {response.text}"
            data = response.json()
            assert data["report_type"] == report_type, f"Report type mismatch for {report_type}"
    
    def test_analyze_requires_auth(self):
        """Test analyzer endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            json={
                "image_base64": SAMPLE_IMAGE,
                "report_type": "ECG"
            }
        )
        assert response.status_code == 401, "Should require authentication"
    
    def test_analyze_requires_image(self, auth_headers):
        """Test analyzer requires image_base64 field"""
        response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            headers=auth_headers,
            json={
                "report_type": "ECG"
            }
        )
        assert response.status_code == 422, "Should require image_base64"


class TestAnalyzerHistory:
    """Tests for GET /api/analyzer/history endpoint"""
    
    def test_history_returns_list(self, auth_headers):
        """Test history endpoint returns list of analyses"""
        response = requests.get(
            f"{BASE_URL}/api/analyzer/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"History failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
    
    def test_history_item_structure(self, auth_headers):
        """Test history items have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/analyzer/history",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "report_type" in item
            assert "analysis" in item
            assert "created_at" in item
    
    def test_history_requires_auth(self):
        """Test history endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analyzer/history")
        assert response.status_code == 401, "Should require authentication"


class TestAnalyzerAccess:
    """Tests for analyzer access control"""
    
    def test_admin_has_access(self, auth_headers):
        """Test admin user has analyzer access"""
        response = requests.get(
            f"{BASE_URL}/api/analyzer/history",
            headers=auth_headers
        )
        assert response.status_code == 200, "Admin should have analyzer access"
    
    def test_analyzer_delete(self, auth_headers):
        """Test deleting an analysis"""
        # First create an analysis
        create_response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            headers=auth_headers,
            json={
                "image_base64": SAMPLE_IMAGE,
                "report_type": "ECG",
                "clinical_context": "Test for deletion"
            }
        )
        assert create_response.status_code == 200
        analysis_id = create_response.json()["id"]
        
        # Delete the analysis
        delete_response = requests.delete(
            f"{BASE_URL}/api/analyzer/{analysis_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
