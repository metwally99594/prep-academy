"""
Test PDF Export Feature for Medical Analyzer
Tests:
1. PDF export endpoint returns valid PDF (Content-Type: application/pdf)
2. PDF export requires authentication (401 without token)
3. PDF export returns 404 for non-existent analysis_id
4. PDF export ownership - user can only download their own analyses
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


class TestPDFExport:
    """PDF Export endpoint tests"""
    
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
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Create a test user and get token"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"test_pdf_{unique_id}@test.com"
        password = "testpass123"
        
        # Register new user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test PDF User"
        })
        if response.status_code == 200:
            return response.json()["token"]
        
        # If user exists, login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_user_headers(self, test_user_token):
        """Get headers with test user auth token"""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    @pytest.fixture(scope="class")
    def existing_analysis_id(self, admin_headers):
        """Get an existing analysis ID from admin's history"""
        response = requests.get(f"{BASE_URL}/api/analyzer/history", headers=admin_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        return None
    
    def test_pdf_export_requires_auth(self):
        """Test 1: PDF export should return 401 without authentication"""
        # Use a random analysis_id - doesn't matter since auth check comes first
        response = requests.get(f"{BASE_URL}/api/analyzer/test-id-123/pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: PDF export returns 401 without authentication")
    
    def test_pdf_export_404_for_nonexistent(self, admin_headers):
        """Test 2: PDF export should return 404 for non-existent analysis_id"""
        fake_id = f"nonexistent-{uuid.uuid4().hex}"
        response = requests.get(f"{BASE_URL}/api/analyzer/{fake_id}/pdf", headers=admin_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: PDF export returns 404 for non-existent analysis_id")
    
    def test_pdf_export_returns_valid_pdf(self, admin_headers, existing_analysis_id):
        """Test 3: PDF export should return valid PDF with correct Content-Type"""
        if not existing_analysis_id:
            pytest.skip("No existing analysis found in admin history")
        
        response = requests.get(
            f"{BASE_URL}/api/analyzer/{existing_analysis_id}/pdf",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Content-Type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Check Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, f"Expected attachment in Content-Disposition, got {content_disposition}"
        assert ".pdf" in content_disposition, f"Expected .pdf in filename, got {content_disposition}"
        
        # Check PDF magic bytes (PDF files start with %PDF)
        assert response.content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        
        # Check PDF has reasonable size (at least 1KB)
        assert len(response.content) > 1000, f"PDF too small: {len(response.content)} bytes"
        
        print(f"PASS: PDF export returns valid PDF ({len(response.content)} bytes)")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Disposition: {content_disposition}")
    
    def test_pdf_export_ownership(self, admin_headers, test_user_headers, existing_analysis_id):
        """Test 4: User should only be able to download their own analyses"""
        if not existing_analysis_id:
            pytest.skip("No existing analysis found in admin history")
        
        # Admin should be able to download their own analysis
        admin_response = requests.get(
            f"{BASE_URL}/api/analyzer/{existing_analysis_id}/pdf",
            headers=admin_headers
        )
        assert admin_response.status_code == 200, f"Admin should access own analysis, got {admin_response.status_code}"
        
        # Test user should NOT be able to download admin's analysis (404 due to user_id filter)
        test_user_response = requests.get(
            f"{BASE_URL}/api/analyzer/{existing_analysis_id}/pdf",
            headers=test_user_headers
        )
        # Should return 404 because the query filters by user_id
        assert test_user_response.status_code in [403, 404], \
            f"Test user should not access admin's analysis, got {test_user_response.status_code}"
        
        print("PASS: PDF export enforces ownership - users can only download their own analyses")


class TestAnalyzerHistoryForPDF:
    """Test analyzer history endpoint to ensure analyses exist for PDF testing"""
    
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
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_analyzer_history_endpoint(self, admin_headers):
        """Test that analyzer history endpoint works"""
        response = requests.get(f"{BASE_URL}/api/analyzer/history", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        
        print(f"PASS: Analyzer history returns {len(data)} analyses")
        
        if len(data) > 0:
            # Verify structure of first analysis
            first = data[0]
            assert "id" in first, "Analysis should have 'id' field"
            assert "report_type" in first, "Analysis should have 'report_type' field"
            assert "analysis" in first, "Analysis should have 'analysis' field"
            print(f"  First analysis: id={first['id'][:12]}..., type={first['report_type']}")
        
        return data


class TestExistingFeatures:
    """Test that existing analyzer features still work"""
    
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
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_analyzer_analyze_endpoint_exists(self, admin_headers):
        """Test that analyze endpoint exists and requires image"""
        # Test without image - should fail with validation error
        response = requests.post(
            f"{BASE_URL}/api/analyzer/analyze",
            headers=admin_headers,
            json={"report_type": "ECG", "clinical_context": "Test context"}
        )
        # Should fail because image_base64 is required
        assert response.status_code in [400, 422], f"Expected 400/422 without image, got {response.status_code}"
        print("PASS: Analyzer analyze endpoint exists and validates input")
    
    def test_analyzer_delete_endpoint(self, admin_headers):
        """Test that delete endpoint exists"""
        fake_id = f"nonexistent-{uuid.uuid4().hex}"
        response = requests.delete(
            f"{BASE_URL}/api/analyzer/{fake_id}",
            headers=admin_headers
        )
        # Should return 404 for non-existent
        assert response.status_code == 404, f"Expected 404 for non-existent, got {response.status_code}"
        print("PASS: Analyzer delete endpoint exists and returns 404 for non-existent")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
