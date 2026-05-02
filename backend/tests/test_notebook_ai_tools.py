"""
Test Notebook AI Tools: Audio TTS, Quiz Generation, MCQ, Study Guide, Flashcards, Mind Map
Tests the bug fixes for Audio TTS (await restored) and Quiz generation (background job with polling)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@medical.com"
ADMIN_PASSWORD = "admin123"

# Existing notebook IDs from the problem statement
NOTEBOOK_ID_SMALL = "de06c38f-0791-4e82-b96e-2589f8e2d13e"  # test_large.pdf, 10 pages
NOTEBOOK_ID_LARGE = "c8b9ee9f-6668-4c01-b04b-40fb28a93aca"  # sip5a-2020-06.pdf, 43 pages


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestHealthAndAuth:
    """Basic health and auth tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"Health check passed: {response.json()}")
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"Admin login successful: {data['user'].get('email')}")


class TestNotebookAccess:
    """Test notebook access and listing"""
    
    def test_notebook_list(self, auth_headers):
        """Test listing notebooks"""
        response = requests.get(f"{BASE_URL}/api/notebook/list", headers=auth_headers)
        assert response.status_code == 200
        notebooks = response.json()
        assert isinstance(notebooks, list)
        print(f"Found {len(notebooks)} notebooks")
        for nb in notebooks[:3]:
            print(f"  - {nb.get('filename')} ({nb.get('page_count')} pages, id={nb.get('id')[:8]}...)")
    
    def test_notebook_get_small(self, auth_headers):
        """Test getting the small test notebook"""
        response = requests.get(f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_SMALL}", headers=auth_headers)
        if response.status_code == 404:
            pytest.skip(f"Small notebook {NOTEBOOK_ID_SMALL} not found")
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        print(f"Small notebook: {data.get('filename')}, {data.get('page_count')} pages")
    
    def test_notebook_get_large(self, auth_headers):
        """Test getting the large test notebook"""
        response = requests.get(f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_LARGE}", headers=auth_headers)
        if response.status_code == 404:
            pytest.skip(f"Large notebook {NOTEBOOK_ID_LARGE} not found")
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        print(f"Large notebook: {data.get('filename')}, {data.get('page_count')} pages")


class TestAudioTTS:
    """Test Audio TTS 2-step generation (bug fix: await restored on async method)"""
    
    def test_audio_script_generation(self, auth_headers):
        """Step 1: Generate audio script from notebook"""
        response = requests.post(
            f"{BASE_URL}/api/learn/audio-script",
            json={
                "notebook_id": NOTEBOOK_ID_SMALL,
                "language": "de",
                "voice": "nova"
            },
            headers=auth_headers,
            timeout=60
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert response.status_code == 200, f"Audio script failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain audio_id"
        assert "script" in data, "Response should contain script"
        assert len(data["script"]) > 50, "Script should have content"
        print(f"Audio script generated: {len(data['script'])} chars, id={data['id'][:8]}...")
        return data
    
    def test_audio_tts_generation(self, auth_headers):
        """Step 2: Convert script to speech - tests the await fix"""
        # First generate script
        script_response = requests.post(
            f"{BASE_URL}/api/learn/audio-script",
            json={
                "notebook_id": NOTEBOOK_ID_SMALL,
                "language": "de",
                "voice": "nova"
            },
            headers=auth_headers,
            timeout=60
        )
        if script_response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert script_response.status_code == 200
        script_data = script_response.json()
        audio_id = script_data.get("id")
        
        # Now generate TTS
        tts_response = requests.post(
            f"{BASE_URL}/api/learn/audio-tts",
            json={
                "audio_id": audio_id,
                "voice": "nova"
            },
            headers=auth_headers,
            timeout=60
        )
        
        assert tts_response.status_code == 200, f"TTS failed: {tts_response.status_code} - {tts_response.text}"
        tts_data = tts_response.json()
        assert "audio_base64" in tts_data, "Response should contain audio_base64"
        assert tts_data["audio_base64"] is not None, "audio_base64 should not be None"
        assert len(tts_data["audio_base64"]) > 1000, "audio_base64 should have content"
        print(f"TTS generated: {len(tts_data['audio_base64'])} chars base64, voice={tts_data.get('voice')}")
    
    def test_audio_tts_with_direct_script(self, auth_headers):
        """Test TTS with direct script input"""
        tts_response = requests.post(
            f"{BASE_URL}/api/learn/audio-tts",
            json={
                "script": "Dies ist ein kurzer Test für die Text-zu-Sprache Funktion.",
                "voice": "alloy"
            },
            headers=auth_headers,
            timeout=60
        )
        
        assert tts_response.status_code == 200, f"Direct TTS failed: {tts_response.status_code} - {tts_response.text}"
        tts_data = tts_response.json()
        assert "audio_base64" in tts_data
        assert tts_data["audio_base64"] is not None
        print(f"Direct TTS generated: {len(tts_data['audio_base64'])} chars base64")


class TestQuizGeneration:
    """Test Quiz generation with background job and polling (bug fix: avoid 60s proxy timeout)"""
    
    def test_quiz_generation_starts_job(self, auth_headers):
        """Test that quiz generation returns job_id immediately"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_SMALL}/generate-quiz?count=5&language=de",
            json={},
            headers=auth_headers,
            timeout=30
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert response.status_code == 200, f"Quiz start failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "job_id" in data, "Response should contain job_id"
        assert "status" in data, "Response should contain status"
        assert data["status"] == "processing", f"Status should be 'processing', got {data['status']}"
        print(f"Quiz job started: job_id={data['job_id'][:8]}..., status={data['status']}")
        return data["job_id"]
    
    def test_quiz_job_polling(self, auth_headers):
        """Test polling quiz job until completion"""
        # Start quiz generation
        start_response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_SMALL}/generate-quiz?count=3&language=de",
            json={},
            headers=auth_headers,
            timeout=30
        )
        if start_response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert start_response.status_code == 200
        job_id = start_response.json().get("job_id")
        
        # Poll for completion (max 120 seconds)
        max_polls = 40
        poll_interval = 3
        final_status = None
        
        for i in range(max_polls):
            time.sleep(poll_interval)
            poll_response = requests.get(
                f"{BASE_URL}/api/quiz-job/{job_id}",
                headers=auth_headers
            )
            assert poll_response.status_code == 200, f"Poll failed: {poll_response.status_code}"
            poll_data = poll_response.json()
            status = poll_data.get("status")
            print(f"Poll {i+1}: status={status}")
            
            if status == "done":
                final_status = poll_data
                break
            elif status == "error":
                final_status = poll_data
                break
        
        assert final_status is not None, "Job did not complete within timeout"
        assert final_status.get("status") in ["done", "error"], f"Unexpected final status: {final_status.get('status')}"
        
        if final_status.get("status") == "done":
            assert "count" in final_status, "Done status should have count"
            assert "message" in final_status, "Done status should have message"
            print(f"Quiz completed: {final_status.get('count')} questions, message={final_status.get('message')}")
        else:
            print(f"Quiz error: {final_status.get('message')}")


class TestMCQGeneration:
    """Test MCQ generation from notebook (text reduced from 40k to 15k chars)"""
    
    def test_mcq_generation(self, auth_headers):
        """Test MCQ generation endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_SMALL}/generate-mcq?language=de",
            json={},
            headers=auth_headers,
            timeout=90
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert response.status_code == 200, f"MCQ generation failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "mcq" in data, "Response should contain mcq"
        assert len(data["mcq"]) > 100, "MCQ content should have substantial text"
        print(f"MCQ generated: {len(data['mcq'])} chars")
        # Check for expected MCQ format markers
        mcq_text = data["mcq"].lower()
        assert any(marker in mcq_text for marker in ["frage", "question", "a)", "b)", "c)"]), "MCQ should contain question markers"


class TestNotebookSummarize:
    """Test notebook summarize endpoint"""
    
    def test_summarize(self, auth_headers):
        """Test summarize endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_ID_SMALL}/summarize?language=de",
            json={},
            headers=auth_headers,
            timeout=90
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found")
        
        assert response.status_code == 200, f"Summarize failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "summary" in data, "Response should contain summary"
        assert len(data["summary"]) > 100, "Summary should have content"
        print(f"Summary generated: {len(data['summary'])} chars")


class TestStudyGuide:
    """Test Study Guide generation"""
    
    def test_study_guide_generation(self, auth_headers):
        """Test study guide endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/learn/study-guide",
            json={
                "notebook_id": NOTEBOOK_ID_SMALL,
                "language": "de",
                "model": "gpt-4o"
            },
            headers=auth_headers,
            timeout=120
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found or no content")
        
        assert response.status_code == 200, f"Study guide failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "content" in data, "Response should contain content"
        assert len(data["content"]) > 100, "Study guide should have content"
        print(f"Study guide generated: {len(data['content'])} chars")


class TestFlashcards:
    """Test Flashcards generation"""
    
    def test_flashcards_generation(self, auth_headers):
        """Test flashcards endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/learn/flashcards",
            json={
                "notebook_id": NOTEBOOK_ID_SMALL,
                "count": 5,
                "language": "de",
                "model": "gpt-4o"
            },
            headers=auth_headers,
            timeout=120
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found or no content")
        
        assert response.status_code == 200, f"Flashcards failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "cards" in data, "Response should contain cards"
        assert isinstance(data["cards"], list), "Cards should be a list"
        assert len(data["cards"]) > 0, "Should have at least one card"
        
        # Validate card structure
        card = data["cards"][0]
        assert "front" in card, "Card should have front"
        assert "back" in card, "Card should have back"
        print(f"Flashcards generated: {len(data['cards'])} cards")


class TestMindMap:
    """Test Mind Map generation"""
    
    def test_mind_map_generation(self, auth_headers):
        """Test mind map endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/learn/mind-map",
            json={
                "notebook_id": NOTEBOOK_ID_SMALL,
                "language": "de",
                "model": "gpt-4o"
            },
            headers=auth_headers,
            timeout=120
        )
        if response.status_code == 404:
            pytest.skip(f"Notebook {NOTEBOOK_ID_SMALL} not found or no content")
        
        assert response.status_code == 200, f"Mind map failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "mind_map" in data, "Response should contain mind_map"
        mind_map = data["mind_map"]
        assert "title" in mind_map, "Mind map should have title"
        assert "children" in mind_map, "Mind map should have children"
        print(f"Mind map generated: title='{mind_map.get('title')}', {len(mind_map.get('children', []))} children")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
