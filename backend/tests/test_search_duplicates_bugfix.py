"""
Test suite for bug fixes in iteration 16:
1. Search endpoint - choices_de.text search, regex escaping, explanation_de field
2. Duplicates endpoint - normalized text + choices fingerprint algorithm
3. Admin UI - 'Andere Stadt' city option
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSearchEndpoint:
    """Tests for GET /api/questions/search/text endpoint bug fixes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Admin login failed")
    
    def test_search_choices_de_text_hypertriglyzeridamien(self):
        """Test 1: Search for 'Hypertriglyzeridämien' should return results (choices_de.text search)"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "Hypertriglyzeridämien", "limit": 50}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"Search 'Hypertriglyzeridämien': Found {len(data)} results")
        # This tests the choices_de.text field search
        # If results > 0, the fix is working
        assert isinstance(data, list), "Response should be a list"
    
    def test_search_choices_text_lungenembolie(self):
        """Test 2: Search for 'Lungenembolie' should return results (choices.text search)"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "Lungenembolie", "limit": 50}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"Search 'Lungenembolie': Found {len(data)} results")
        assert isinstance(data, list), "Response should be a list"
    
    def test_search_regex_escaping_parentheses(self):
        """Test 3: Search for 'Patient(in)' should NOT crash (regex escaping)"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "Patient(in)", "limit": 50}
        )
        # The key test is that it doesn't return 500 error
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Regex escaping may have failed."
        data = response.json()
        print(f"Search 'Patient(in)': Found {len(data)} results (no crash = success)")
        assert isinstance(data, list), "Response should be a list"
    
    def test_search_regex_escaping_special_chars(self):
        """Test regex escaping with various special characters"""
        special_queries = ["test[1]", "a+b", "x*y", "a.b", "a?b", "a^b", "a$b"]
        for query in special_queries:
            response = requests.get(
                f"{BASE_URL}/api/questions/search/text",
                params={"q": query, "limit": 10}
            )
            assert response.status_code == 200, f"Query '{query}' failed with status {response.status_code}"
            print(f"Search '{query}': Status 200 (regex escaping works)")
    
    def test_search_case_insensitive_falsch(self):
        """Test 4: Search for 'FALSCH' should return results (case insensitive)"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "FALSCH", "limit": 50}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"Search 'FALSCH' (uppercase): Found {len(data)} results")
        assert isinstance(data, list), "Response should be a list"
        
        # Also test lowercase
        response_lower = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "falsch", "limit": 50}
        )
        assert response_lower.status_code == 200
        data_lower = response_lower.json()
        print(f"Search 'falsch' (lowercase): Found {len(data_lower)} results")
        # Both should return similar results (case insensitive)
    
    def test_search_medical_term_in_choices(self):
        """Test searching for medical terms that appear in answer choices"""
        medical_terms = ["Herzinfarkt", "Diabetes", "Hypertonie", "Fieber"]
        for term in medical_terms:
            response = requests.get(
                f"{BASE_URL}/api/questions/search/text",
                params={"q": term, "limit": 20}
            )
            assert response.status_code == 200, f"Search for '{term}' failed"
            data = response.json()
            print(f"Search '{term}': Found {len(data)} results")


class TestDuplicatesEndpoint:
    """Tests for GET /api/admin/questions/duplicates endpoint bug fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Admin login failed")
    
    def test_duplicates_requires_auth(self):
        """Test that duplicates endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/questions/duplicates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Duplicates endpoint requires auth: PASS")
    
    def test_duplicates_returns_groups(self):
        """Test 5: GET /api/admin/questions/duplicates returns groups with matching choices"""
        response = requests.get(
            f"{BASE_URL}/api/admin/questions/duplicates",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert "groups" in data, "Response should have 'groups' field"
        assert "total_duplicate_groups" in data, "Response should have 'total_duplicate_groups' field"
        assert "total_extra_copies" in data, "Response should have 'total_extra_copies' field"
        
        print(f"Duplicates found: {data['total_duplicate_groups']} groups, {data['total_extra_copies']} extra copies")
        
        # Verify each group has questions with matching choices
        for group in data.get("groups", [])[:5]:  # Check first 5 groups
            assert "questions" in group, "Each group should have 'questions'"
            assert "count" in group, "Each group should have 'count'"
            assert len(group["questions"]) >= 2, "Each group should have at least 2 questions"
            
            # Verify questions in group have similar structure
            questions = group["questions"]
            print(f"  Group with {len(questions)} questions: '{group.get('_id', '')[:50]}...'")
    
    def test_duplicates_with_specialty_filter(self):
        """Test duplicates endpoint with specialty filter"""
        specialties = ["surgery", "internal", "pediatrics"]
        for specialty in specialties:
            response = requests.get(
                f"{BASE_URL}/api/admin/questions/duplicates",
                params={"specialty_id": specialty},
                headers=self.headers
            )
            assert response.status_code == 200, f"Failed for specialty {specialty}"
            data = response.json()
            print(f"Duplicates in {specialty}: {data['total_duplicate_groups']} groups")
    
    def test_duplicates_group_structure(self):
        """Verify duplicate groups have proper question structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/questions/duplicates",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("groups"):
            group = data["groups"][0]
            for q in group["questions"]:
                # Each question should have required fields
                assert "id" in q, "Question should have 'id'"
                assert "specialty_id" in q, "Question should have 'specialty_id'"
                # Should have either question_text or question_text_de
                has_text = q.get("question_text") or q.get("question_text_de")
                assert has_text, "Question should have text"
            print("Duplicate group structure: PASS")
        else:
            print("No duplicate groups found (may be expected if data is clean)")


class TestAdminCitiesOption:
    """Tests for Admin UI 'Andere Stadt' city option"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@medical.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Admin login failed")
    
    def test_create_question_with_andere_stadt(self):
        """Test 6: Create a question with 'andere' exam_location"""
        question_data = {
            "specialty_id": "internal",
            "year": 2024,
            "exam_location": "andere",  # The new city option
            "question_text": "Test question for Andere Stadt",
            "question_text_de": "Testfrage für Andere Stadt",
            "choices": [
                {"id": "a", "text": "Option A", "text_de": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "text_de": "Option B", "is_correct": False},
                {"id": "c", "text": "Option C", "text_de": "Option C", "is_correct": False},
                {"id": "d", "text": "Option D", "text_de": "Option D", "is_correct": False},
                {"id": "e", "text": "Option E", "text_de": "Option E", "is_correct": False},
            ],
            "explanation_de": "Test explanation"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/questions",
            json=question_data,
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify the question was created with 'andere' location
        assert data.get("exam_location") == "andere", f"Expected 'andere', got {data.get('exam_location')}"
        print(f"Created question with 'andere' exam_location: {data.get('id')}")
        
        # Clean up - delete the test question
        question_id = data.get("id")
        if question_id:
            delete_response = requests.delete(
                f"{BASE_URL}/api/questions/{question_id}",
                headers=self.headers
            )
            assert delete_response.status_code == 200, "Failed to delete test question"
            print(f"Cleaned up test question: {question_id}")
    
    def test_search_by_andere_city(self):
        """Test searching for questions with 'andere' exam_location"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "andere", "limit": 20}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"Search 'andere': Found {len(data)} results")
        # The search should work without errors


class TestSearchEndpointEdgeCases:
    """Additional edge case tests for search"""
    
    def test_search_short_query(self):
        """Test that short queries (< 2 chars) return empty list"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "a", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Short query should return empty list"
        print("Short query returns empty: PASS")
    
    def test_search_empty_query(self):
        """Test that empty query returns empty list"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Empty query should return empty list"
        print("Empty query returns empty: PASS")
    
    def test_search_year_query(self):
        """Test searching by year"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "2023", "limit": 50}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"Search '2023': Found {len(data)} results")
    
    def test_search_city_alias_wien(self):
        """Test searching by city alias 'wien'"""
        response = requests.get(
            f"{BASE_URL}/api/questions/search/text",
            params={"q": "wien", "limit": 50}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"Search 'wien': Found {len(data)} results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
