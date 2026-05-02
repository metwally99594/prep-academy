"""
Test Exam Date Countdown Feature
- POST /api/dashboard/settings?exam_date=YYYY-MM-DD saves exam date
- GET /api/dashboard/stats returns the saved exam_date field
- POST /api/dashboard/settings?exam_date= clears the exam date
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestExamDateFeature:
    """Test exam date countdown feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"✓ Logged in as admin@medical.com")
    
    def test_01_set_exam_date(self):
        """Test setting exam date via POST /api/dashboard/settings"""
        exam_date = "2026-07-15"
        response = self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": exam_date}
        )
        assert response.status_code == 200, f"Failed to set exam date: {response.text}"
        data = response.json()
        assert data.get("message") == "Settings updated", f"Unexpected response: {data}"
        print(f"✓ Set exam date to {exam_date}")
    
    def test_02_get_exam_date_from_stats(self):
        """Test that GET /api/dashboard/stats returns the saved exam_date"""
        # First set the exam date
        exam_date = "2026-07-15"
        set_response = self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": exam_date}
        )
        assert set_response.status_code == 200
        
        # Now get stats and verify exam_date is returned
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Failed to get stats: {response.text}"
        data = response.json()
        
        # Verify exam_date field exists and has correct value
        assert "exam_date" in data, f"exam_date not in response: {data.keys()}"
        assert data["exam_date"] == exam_date, f"Expected {exam_date}, got {data['exam_date']}"
        print(f"✓ GET /api/dashboard/stats returns exam_date: {data['exam_date']}")
    
    def test_03_clear_exam_date(self):
        """Test clearing exam date via POST /api/dashboard/settings?exam_date="""
        # First set a date
        self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": "2026-07-15"}
        )
        
        # Now clear it
        response = self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": ""}
        )
        assert response.status_code == 200, f"Failed to clear exam date: {response.text}"
        print("✓ Cleared exam date")
        
        # Verify it's cleared in stats
        stats_response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert stats_response.status_code == 200
        data = stats_response.json()
        
        # exam_date should be empty string or None
        assert data.get("exam_date") in ["", None], f"Expected empty exam_date, got: {data.get('exam_date')}"
        print(f"✓ Verified exam_date is cleared: {data.get('exam_date')}")
    
    def test_04_set_different_exam_date(self):
        """Test updating exam date to a different value"""
        # Set first date
        first_date = "2026-06-01"
        response1 = self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": first_date}
        )
        assert response1.status_code == 200
        
        # Verify first date
        stats1 = self.session.get(f"{BASE_URL}/api/dashboard/stats").json()
        assert stats1["exam_date"] == first_date
        print(f"✓ First exam date set: {first_date}")
        
        # Update to second date
        second_date = "2026-08-20"
        response2 = self.session.post(
            f"{BASE_URL}/api/dashboard/settings",
            params={"exam_date": second_date}
        )
        assert response2.status_code == 200
        
        # Verify second date
        stats2 = self.session.get(f"{BASE_URL}/api/dashboard/stats").json()
        assert stats2["exam_date"] == second_date, f"Expected {second_date}, got {stats2['exam_date']}"
        print(f"✓ Updated exam date to: {second_date}")
    
    def test_05_dashboard_stats_structure(self):
        """Verify dashboard stats response structure includes all expected fields"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = [
            "total_answered", "total_correct", "total_wrong",
            "accuracy", "coverage", "readiness",
            "current_streak", "longest_streak",
            "exam_date", "daily_goal", "weekly_goal",
            "specialty_progress"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Dashboard stats has all required fields: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
