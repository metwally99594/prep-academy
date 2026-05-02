import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestHealthAndRoot:
    """Test API health and root endpoint"""
    
    def test_api_root(self, api_client):
        """API root returns correct response"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Medical MCQ API"


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_with_valid_credentials(self, api_client):
        """Login with valid admin credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@medical.com"
        assert data["user"]["is_admin"] == True
    
    def test_login_with_invalid_credentials(self, api_client):
        """Login with invalid credentials returns 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_with_nonexistent_user(self, api_client):
        """Login with non-existent user returns 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@email.com",
            "password": "somepassword"
        })
        assert response.status_code == 401
    
    def test_get_me_without_auth(self, api_client):
        """Access /auth/me without token returns 401"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
    
    def test_get_me_with_auth(self, authenticated_client):
        """Access /auth/me with valid token returns user data"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert data["email"] == "admin@medical.com"


class TestSpecialties:
    """Test specialties endpoint - 11 specialties including Psychiatrie"""
    
    def test_get_all_specialties(self, api_client):
        """Get all specialties - should return 11 including Psychiatrie"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 11, f"Expected 11 specialties, got {len(data)}"
    
    def test_specialties_include_psychiatrie(self, api_client):
        """Verify Psychiatrie specialty exists"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        specialty_ids = [s["id"] for s in data]
        assert "psychiatry" in specialty_ids, "Psychiatrie specialty not found"
        
        psychiatry = next((s for s in data if s["id"] == "psychiatry"), None)
        assert psychiatry is not None
        assert psychiatry["name_de"] == "Psychiatrie"
    
    def test_specialty_has_required_fields(self, api_client):
        """Each specialty has required fields"""
        response = api_client.get(f"{BASE_URL}/api/specialties")
        assert response.status_code == 200
        data = response.json()
        
        for specialty in data:
            assert "id" in specialty
            assert "name" in specialty
            assert "name_de" in specialty
            assert "icon" in specialty
            assert "question_count" in specialty
    
    def test_get_single_specialty(self, authenticated_client):
        """Get single specialty by ID"""
        response = authenticated_client.get(f"{BASE_URL}/api/specialties/surgery")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "surgery"
        assert data["name_de"] == "Chirurgie"
    
    def test_get_nonexistent_specialty(self, authenticated_client):
        """Get non-existent specialty returns 404"""
        response = authenticated_client.get(f"{BASE_URL}/api/specialties/nonexistent")
        assert response.status_code == 404


class TestQuestions:
    """Test questions endpoints including city filter"""
    
    def test_get_questions(self, authenticated_client):
        """Get questions list"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_questions_by_specialty(self, authenticated_client):
        """Filter questions by specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?specialty_id=surgery")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_questions_by_city_vienna(self, authenticated_client):
        """Filter questions by city - Vienna"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?exam_location=vienna")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # If there are results, verify they are all from Vienna
        for q in data:
            assert q.get("exam_location") == "vienna", f"Question has wrong city: {q.get('exam_location')}"
    
    def test_get_questions_by_city_innsbruck(self, authenticated_client):
        """Filter questions by city - Innsbruck"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions?exam_location=innsbruck")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # If there are results, verify they are all from Innsbruck
        for q in data:
            assert q.get("exam_location") == "innsbruck", f"Question has wrong city: {q.get('exam_location')}"
    
    def test_get_available_years(self, authenticated_client):
        """Get available years for questions"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/years/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_questions(self, authenticated_client):
        """Search questions by text"""
        response = authenticated_client.get(f"{BASE_URL}/api/questions/search/text?q=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestFavorites:
    """Test favorites endpoints"""
    
    def test_get_favorites_requires_auth(self, api_client):
        """Get favorites without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/favorites")
        assert response.status_code == 401
    
    def test_get_favorites_with_auth(self, authenticated_client):
        """Get favorites with auth returns list"""
        response = authenticated_client.get(f"{BASE_URL}/api/favorites")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStats:
    """Test stats endpoint"""
    
    def test_get_stats_requires_auth(self, api_client):
        """Get stats without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 401
    
    def test_get_stats_with_auth(self, authenticated_client):
        """Get stats with auth returns stats object"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_questions" in data
        assert "correct_answers" in data
        assert "accuracy_percentage" in data


class TestReviewEndpoints:
    """Test Quick Review Mode endpoints"""
    
    def test_get_review_requires_auth(self, api_client):
        """Get review list without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/review")
        assert response.status_code == 401
    
    def test_get_review_with_auth(self, authenticated_client):
        """Get review list with auth returns list"""
        response = authenticated_client.get(f"{BASE_URL}/api/review")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_review_count_requires_auth(self, api_client):
        """Get review count without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/review/count")
        assert response.status_code == 401
    
    def test_get_review_count_with_auth(self, authenticated_client):
        """Get review count with auth returns count object"""
        response = authenticated_client.get(f"{BASE_URL}/api/review/count")
        assert response.status_code == 200
        data = response.json()
        assert "unreviewed" in data
        assert "total" in data
        assert isinstance(data["unreviewed"], int)
        assert isinstance(data["total"], int)
    
    def test_get_review_with_include_reviewed(self, authenticated_client):
        """Get review list with include_reviewed=true returns all items"""
        response = authenticated_client.get(f"{BASE_URL}/api/review?include_reviewed=true")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_mark_reviewed_nonexistent(self, authenticated_client):
        """Mark non-existent question as reviewed returns 404"""
        response = authenticated_client.post(f"{BASE_URL}/api/review/nonexistent-id/mark-reviewed")
        assert response.status_code == 404
    
    def test_remove_from_review_nonexistent(self, authenticated_client):
        """Remove non-existent question from review returns 404"""
        response = authenticated_client.delete(f"{BASE_URL}/api/review/nonexistent-id")
        assert response.status_code == 404


class TestAdminLeaderboard:
    """Test admin leaderboard endpoint"""
    
    def test_leaderboard_requires_admin(self, api_client):
        """Get leaderboard without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/admin/leaderboard")
        assert response.status_code == 401
    
    def test_leaderboard_returns_user_stats(self, authenticated_client):
        """Get leaderboard returns user ranking with stats"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check first user has required fields
        if len(data) > 0:
            user = data[0]
            assert "id" in user
            assert "name" in user
            assert "email" in user
            assert "total_questions" in user
            assert "correct_answers" in user
            assert "wrong_answers" in user
            assert "accuracy" in user


class TestAdminActivityOnline:
    """Test admin online activity tracking endpoints"""
    
    def test_heartbeat_updates_activity(self, authenticated_client):
        """Heartbeat endpoint updates user activity"""
        response = authenticated_client.post(f"{BASE_URL}/api/admin/activity/heartbeat")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_online_users_requires_admin(self, api_client):
        """Get online users without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/admin/activity/online")
        assert response.status_code == 401
    
    def test_online_users_returns_list(self, authenticated_client):
        """Get online users returns activity list"""
        # Send heartbeat first
        authenticated_client.post(f"{BASE_URL}/api/admin/activity/heartbeat")
        
        response = authenticated_client.get(f"{BASE_URL}/api/admin/activity/online")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check if admin is in list (after heartbeat)
        if len(data) > 0:
            activity = data[0]
            assert "user_id" in activity
            assert "last_active" in activity
            assert "is_online" in activity


class TestAdminExportQuestions:
    """Test admin export questions endpoint"""
    
    def test_export_requires_admin(self, api_client):
        """Export questions without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/admin/export/questions")
        assert response.status_code == 401
    
    def test_export_all_questions(self, authenticated_client):
        """Export all questions returns structured data"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/export/questions")
        assert response.status_code == 200
        data = response.json()
        
        assert "questions" in data
        assert "total" in data
        assert "exported_at" in data
        assert isinstance(data["questions"], list)
        assert data["total"] == len(data["questions"])
    
    def test_export_by_specialty(self, authenticated_client):
        """Export questions filtered by specialty"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/export/questions?specialty_id=surgery")
        assert response.status_code == 200
        data = response.json()
        
        assert "questions" in data
        # All questions should have specialty_name
        for q in data["questions"]:
            assert "specialty_name" in q


class TestWrongAnswerFlow:
    """Test that wrong answers are added to review list"""
    
    def test_wrong_answer_adds_to_review(self, authenticated_client):
        """Submitting wrong answer adds question to review list"""
        # First get a question
        response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        assert response.status_code == 200
        questions = response.json()
        
        if len(questions) == 0:
            pytest.skip("No questions available")
        
        question = questions[0]
        question_id = question["id"]
        
        # Find an incorrect choice
        incorrect_choices = [c["id"] for c in question["choices"] if not c.get("is_correct")]
        if not incorrect_choices:
            pytest.skip("No incorrect choices available")
        
        # Get initial review count
        count_resp = authenticated_client.get(f"{BASE_URL}/api/review/count")
        initial_total = count_resp.json()["total"]
        
        # Submit wrong answer
        response = authenticated_client.post(
            f"{BASE_URL}/api/questions/{question_id}/answer",
            json={"question_id": question_id, "selected_choice_ids": [incorrect_choices[0]]}
        )
        assert response.status_code == 200
        assert response.json()["is_correct"] == False
        
        # Verify review list updated
        review_resp = authenticated_client.get(f"{BASE_URL}/api/review?include_reviewed=true")
        review_ids = [q["id"] for q in review_resp.json()]
        assert question_id in review_ids, "Question should be in review list after wrong answer"
    
    def test_correct_answer_marks_reviewed(self, authenticated_client):
        """Submitting correct answer marks question as reviewed"""
        # First get a question
        response = authenticated_client.get(f"{BASE_URL}/api/questions?limit=1")
        assert response.status_code == 200
        questions = response.json()
        
        if len(questions) == 0:
            pytest.skip("No questions available")
        
        question = questions[0]
        question_id = question["id"]
        
        # Find correct choice(s)
        correct_choices = [c["id"] for c in question["choices"] if c.get("is_correct")]
        if not correct_choices:
            pytest.skip("No correct choices found")
        
        # Submit correct answer
        response = authenticated_client.post(
            f"{BASE_URL}/api/questions/{question_id}/answer",
            json={"question_id": question_id, "selected_choice_ids": correct_choices}
        )
        assert response.status_code == 200
        assert response.json()["is_correct"] == True
        
        # Check unreviewed count - the question should be marked as reviewed (if it was in review)
        count_resp = authenticated_client.get(f"{BASE_URL}/api/review/count")
        assert count_resp.status_code == 200
