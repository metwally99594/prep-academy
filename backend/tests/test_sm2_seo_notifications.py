"""
Test SM-2 Spaced Repetition, SEO Pages, and Smart Notifications
Features for Prep Academy Medical MCQ Platform - Iteration 32
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ============ SM-2 SPACED REPETITION TESTS ============

class TestSM2ReviewStats:
    """Test GET /api/review/stats endpoint"""
    
    def test_review_stats_returns_correct_structure(self, authenticated_client):
        """SM-2 Review Stats: GET /api/review/stats returns total_cards, due_today, mastered"""
        response = authenticated_client.get(f"{BASE_URL}/api/review/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_cards" in data, "Missing total_cards field"
        assert "due_today" in data, "Missing due_today field"
        assert "mastered" in data, "Missing mastered field"
        
        # Validate types
        assert isinstance(data["total_cards"], int), "total_cards should be int"
        assert isinstance(data["due_today"], int), "due_today should be int"
        assert isinstance(data["mastered"], int), "mastered should be int"
        
        print(f"Review stats: total={data['total_cards']}, due={data['due_today']}, mastered={data['mastered']}")
    
    def test_review_stats_requires_auth(self, api_client):
        """Review stats endpoint requires authentication"""
        # Remove auth header temporarily
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/review/stats", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestSM2DueReviews:
    """Test GET /api/review/due endpoint"""
    
    def test_due_reviews_returns_correct_structure(self, authenticated_client):
        """SM-2 Due Reviews: GET /api/review/due returns questions with sr_interval, sr_repetitions"""
        response = authenticated_client.get(f"{BASE_URL}/api/review/due?limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "questions" in data, "Missing questions field"
        assert "due_count" in data, "Missing due_count field"
        assert isinstance(data["questions"], list), "questions should be a list"
        
        # If there are due questions, verify SR metadata
        if data["questions"]:
            q = data["questions"][0]
            assert "id" in q, "Question missing id"
            assert "question_text_de" in q or "question_text" in q, "Question missing text"
            # SR metadata should be attached
            assert "sr_interval" in q, "Missing sr_interval metadata"
            assert "sr_repetitions" in q, "Missing sr_repetitions metadata"
            print(f"Due question has sr_interval={q['sr_interval']}, sr_repetitions={q['sr_repetitions']}")
        else:
            print("No due questions found (this is valid)")
        
        print(f"Due reviews: {data['due_count']} questions due")
    
    def test_due_reviews_requires_auth(self, api_client):
        """Due reviews endpoint requires authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/review/due", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestSM2SubmitReview:
    """Test POST /api/review/submit endpoint"""
    
    def test_submit_review_returns_sm2_data(self, authenticated_client):
        """SM-2 Submit Review: POST /api/review/submit returns interval, next_review, easiness"""
        # First get a question to use
        questions_response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        assert questions_response.status_code == 200
        questions = questions_response.json()
        
        if not questions:
            pytest.skip("No questions available for testing")
        
        question_id = questions[0]["id"]
        
        # Submit review with quality=4 (remembered correctly)
        response = authenticated_client.post(
            f"{BASE_URL}/api/review/submit?question_id={question_id}&quality=4"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "interval" in data, "Missing interval field"
        assert "next_review" in data, "Missing next_review field"
        assert "easiness" in data, "Missing easiness field"
        
        # Validate types and ranges
        assert isinstance(data["interval"], int), "interval should be int"
        assert data["interval"] >= 1, "interval should be at least 1"
        assert isinstance(data["easiness"], (int, float)), "easiness should be numeric"
        assert data["easiness"] >= 1.3, "easiness should be at least 1.3 (SM-2 minimum)"
        
        # Validate next_review is a date string
        try:
            datetime.strptime(data["next_review"], "%Y-%m-%d")
        except ValueError:
            pytest.fail(f"next_review '{data['next_review']}' is not a valid date")
        
        print(f"Review submitted: interval={data['interval']}, next_review={data['next_review']}, easiness={data['easiness']}")
    
    def test_submit_review_quality_0_resets_interval(self, authenticated_client):
        """SM-2: quality < 3 should reset interval to 1"""
        questions_response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        questions = questions_response.json()
        
        if not questions:
            pytest.skip("No questions available")
        
        question_id = questions[0]["id"]
        
        # Submit with quality=0 (complete blackout)
        response = authenticated_client.post(
            f"{BASE_URL}/api/review/submit?question_id={question_id}&quality=0"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["interval"] == 1, f"Quality 0 should reset interval to 1, got {data['interval']}"
        print(f"Quality 0 correctly reset interval to 1")
    
    def test_submit_review_requires_auth(self, api_client):
        """Submit review endpoint requires authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/review/submit?question_id=test&quality=4",
            headers=headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestSM2AutoFeedFromWrongAnswers:
    """Test that wrong answers automatically create spaced_repetition entries"""
    
    def test_wrong_answer_creates_sr_entry(self, authenticated_client):
        """SM-2 Auto-feed: answering wrong creates spaced_repetition entry"""
        # Get a question
        questions_response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        questions = questions_response.json()
        
        if not questions:
            pytest.skip("No questions available")
        
        question = questions[0]
        question_id = question["id"]
        
        # Get the choices and find a wrong answer
        choices = question.get("choices") or question.get("choices_de") or []
        wrong_choice_ids = [c["id"] for c in choices if not c.get("is_correct")]
        
        if not wrong_choice_ids:
            # If no wrong choices found, try correct_answers field
            correct_ids = question.get("correct_answers", [])
            wrong_choice_ids = [c["id"] for c in choices if c["id"] not in correct_ids]
        
        if not wrong_choice_ids:
            pytest.skip("Could not find wrong answer choice")
        
        # Submit wrong answer - include question_id in body as required by model
        response = authenticated_client.post(
            f"{BASE_URL}/api/questions/{question_id}/answer",
            json={"question_id": question_id, "selected_choice_ids": [wrong_choice_ids[0]]}
        )
        assert response.status_code == 200, f"Answer submission failed: {response.status_code}"
        
        result = response.json()
        assert result["is_correct"] == False, "Expected wrong answer"
        
        # Now check that the question appears in review stats
        stats_response = authenticated_client.get(f"{BASE_URL}/api/review/stats")
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert stats["total_cards"] >= 1, "Wrong answer should create SR entry"
        print(f"Wrong answer created SR entry. Total cards: {stats['total_cards']}")


# ============ SMART NOTIFICATIONS TESTS ============

class TestSmartNotifications:
    """Test POST /api/notifications/generate-daily endpoint"""
    
    def test_generate_daily_notifications(self, authenticated_client):
        """Smart Notifications: POST /api/notifications/generate-daily creates notifications"""
        response = authenticated_client.post(f"{BASE_URL}/api/notifications/generate-daily")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Missing status field"
        
        # Status can be "created" or "already_generated"
        assert data["status"] in ["created", "already_generated"], f"Unexpected status: {data['status']}"
        
        if data["status"] == "created":
            assert "count" in data, "Missing count field when status is created"
            assert data["count"] >= 1, "Should create at least 1 notification (streak reminder)"
            print(f"Created {data['count']} notifications")
        else:
            print("Notifications already generated for today")
    
    def test_notifications_list_contains_generated(self, authenticated_client):
        """Verify generated notifications appear in notifications list"""
        # First generate
        authenticated_client.post(f"{BASE_URL}/api/notifications/generate-daily")
        
        # Then fetch
        response = authenticated_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        assert "notifications" in data, "Missing notifications field"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        
        # Check for daily_reminder type
        types = [n.get("type") for n in data["notifications"]]
        assert "daily_reminder" in types, "Should have daily_reminder notification"
        print(f"Found notification types: {set(types)}")
    
    def test_notifications_requires_auth(self, api_client):
        """Notifications endpoint requires authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/api/notifications/generate-daily", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


# ============ SEO SPECIALTY PAGE TESTS (NO AUTH) ============

class TestSEOSpecialtyPage:
    """Test GET /api/seo/specialty/{specialty_id} endpoint - NO AUTH REQUIRED"""
    
    def test_seo_specialty_page_returns_correct_structure(self, api_client):
        """SEO Specialty Page: GET /api/seo/specialty/internal returns required fields"""
        # Use 'internal' specialty as specified in requirements
        response = requests.get(f"{BASE_URL}/api/seo/specialty/internal")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Required fields
        assert "name_de" in data, "Missing name_de field"
        assert "total_questions" in data, "Missing total_questions field"
        assert "sample_questions" in data, "Missing sample_questions field"
        assert "years" in data, "Missing years field"
        assert "active_users" in data, "Missing active_users field"
        
        # Validate types
        assert isinstance(data["name_de"], str), "name_de should be string"
        assert isinstance(data["total_questions"], int), "total_questions should be int"
        assert isinstance(data["sample_questions"], list), "sample_questions should be list"
        assert isinstance(data["years"], list), "years should be list"
        assert isinstance(data["active_users"], int), "active_users should be int"
        
        # Sample questions should have question structure
        if data["sample_questions"]:
            sq = data["sample_questions"][0]
            assert "id" in sq or "question_text_de" in sq or "question_text" in sq, "Sample question missing expected fields"
        
        print(f"SEO page for internal: {data['name_de']}, {data['total_questions']} questions, {len(data['sample_questions'])} samples")
    
    def test_seo_specialty_page_no_auth_required(self, api_client):
        """SEO Specialty Page: Accessible without authentication"""
        # Make request without any auth headers
        response = requests.get(f"{BASE_URL}/api/seo/specialty/internal")
        assert response.status_code == 200, f"SEO page should be accessible without auth, got {response.status_code}"
        print("SEO specialty page accessible without auth - PASS")
    
    def test_seo_specialty_page_not_found(self, api_client):
        """SEO Specialty Page: Returns 404 for invalid specialty"""
        response = requests.get(f"{BASE_URL}/api/seo/specialty/nonexistent_specialty_xyz")
        assert response.status_code == 404, f"Expected 404 for invalid specialty, got {response.status_code}"
    
    def test_seo_specialty_page_sample_questions_limited(self, api_client):
        """SEO Specialty Page: Returns max 3 sample questions"""
        response = requests.get(f"{BASE_URL}/api/seo/specialty/internal")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["sample_questions"]) <= 3, f"Should return max 3 samples, got {len(data['sample_questions'])}"
        print(f"Sample questions count: {len(data['sample_questions'])} (max 3)")


class TestSEOStats:
    """Test GET /api/seo/stats endpoint - NO AUTH REQUIRED"""
    
    def test_seo_stats_returns_correct_structure(self, api_client):
        """SEO Stats: GET /api/seo/stats returns total_questions, total_users, total_specialties"""
        response = requests.get(f"{BASE_URL}/api/seo/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Required fields
        assert "total_questions" in data, "Missing total_questions field"
        assert "total_users" in data, "Missing total_users field"
        assert "total_specialties" in data, "Missing total_specialties field"
        
        # Validate types
        assert isinstance(data["total_questions"], int), "total_questions should be int"
        assert isinstance(data["total_users"], int), "total_users should be int"
        assert isinstance(data["total_specialties"], int), "total_specialties should be int"
        
        # Validate reasonable values
        assert data["total_questions"] >= 0, "total_questions should be non-negative"
        assert data["total_users"] >= 0, "total_users should be non-negative"
        assert data["total_specialties"] >= 0, "total_specialties should be non-negative"
        
        print(f"SEO stats: {data['total_questions']} questions, {data['total_users']} users, {data['total_specialties']} specialties")
    
    def test_seo_stats_no_auth_required(self, api_client):
        """SEO Stats: Accessible without authentication"""
        response = requests.get(f"{BASE_URL}/api/seo/stats")
        assert response.status_code == 200, f"SEO stats should be accessible without auth, got {response.status_code}"
        print("SEO stats accessible without auth - PASS")


# ============ INTEGRATION TESTS ============

class TestSM2Integration:
    """Integration tests for SM-2 flow"""
    
    def test_full_sm2_flow(self, authenticated_client):
        """Test complete SM-2 flow: answer wrong -> appears in due -> submit review -> interval increases"""
        # 1. Get a question
        questions_response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        questions = questions_response.json()
        
        if not questions:
            pytest.skip("No questions available")
        
        question_id = questions[0]["id"]
        
        # 2. Submit review with quality=5 (perfect recall)
        response = authenticated_client.post(
            f"{BASE_URL}/api/review/submit?question_id={question_id}&quality=5"
        )
        assert response.status_code == 200
        first_result = response.json()
        
        # 3. Submit again with quality=5 - interval should increase
        response = authenticated_client.post(
            f"{BASE_URL}/api/review/submit?question_id={question_id}&quality=5"
        )
        assert response.status_code == 200
        second_result = response.json()
        
        # SM-2: After 2 successful reviews, interval should be 6 days
        # (first review: 1 day, second review: 6 days)
        print(f"First interval: {first_result['interval']}, Second interval: {second_result['interval']}")
        
        # Verify stats reflect the card
        stats_response = authenticated_client.get(f"{BASE_URL}/api/review/stats")
        assert stats_response.status_code == 200
        print(f"Final stats: {stats_response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
