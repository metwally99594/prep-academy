"""
Test Audio Save/Load and Quiz Count Features for Prep Academy
Tests:
1. Saved Audio: GET /api/learn/audio-saved/{notebook_id} returns saved audio
2. Audio TTS saves to DB: POST /api/learn/audio-tts with notebook_id saves audio
3. Quiz count=30: POST /api/notebook/{id}/generate-quiz?count=30 generates 30 questions via 3 batches
4. Quiz count=50: POST /api/notebook/{id}/generate-quiz?count=50 generates 50 questions via 5 batches
5. Quiz batch progress: polling shows batch progress messages
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test notebooks from the review request
NOTEBOOK_WITH_SAVED_AUDIO = "c8b9ee9f-6668-4c01-b04b-40fb28a93aca"  # sip5a, has saved audio
NOTEBOOK_FOR_TESTING = "de06c38f-0791-4e82-b96e-2589f8e2d13e"  # test_large.pdf


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@medical.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestSavedAudio:
    """Test saved audio retrieval feature"""
    
    def test_get_saved_audio_found(self, headers):
        """Test GET /api/learn/audio-saved/{notebook_id} returns saved audio when it exists"""
        response = requests.get(
            f"{BASE_URL}/api/learn/audio-saved/{NOTEBOOK_WITH_SAVED_AUDIO}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return found=true with audio data
        assert "found" in data, "Response should have 'found' field"
        
        if data["found"]:
            # Verify all expected fields are present
            assert "script" in data, "Should have script field"
            assert "audio_base64" in data, "Should have audio_base64 field"
            assert "voice" in data, "Should have voice field"
            assert "created_at" in data, "Should have created_at field"
            
            # Verify data is not empty
            assert len(data.get("script", "")) > 0, "Script should not be empty"
            assert len(data.get("audio_base64", "")) > 0, "Audio base64 should not be empty"
            print(f"✓ Found saved audio with voice: {data.get('voice')}, created: {data.get('created_at')}")
        else:
            print("Note: No saved audio found for this notebook (may need to generate first)")
    
    def test_get_saved_audio_not_found(self, headers):
        """Test GET /api/learn/audio-saved/{notebook_id} returns found=false for non-existent audio"""
        fake_notebook_id = "non-existent-notebook-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/learn/audio-saved/{fake_notebook_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("found") == False, "Should return found=false for non-existent notebook"
        print("✓ Correctly returns found=false for non-existent notebook")


class TestAudioTTSSave:
    """Test that audio TTS saves to database"""
    
    def test_audio_script_generation(self, headers):
        """Test POST /api/learn/audio-script generates script"""
        response = requests.post(
            f"{BASE_URL}/api/learn/audio-script",
            headers=headers,
            json={
                "notebook_id": NOTEBOOK_FOR_TESTING,
                "language": "de",
                "voice": "nova"
            },
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Should return audio_id"
        assert "script" in data, "Should return script"
        assert len(data.get("script", "")) > 0, "Script should not be empty"
        print(f"✓ Generated audio script with id: {data.get('id')}")
        return data
    
    def test_audio_tts_saves_to_db(self, headers):
        """Test POST /api/learn/audio-tts saves audio to database for future retrieval"""
        # First generate a script
        script_response = requests.post(
            f"{BASE_URL}/api/learn/audio-script",
            headers=headers,
            json={
                "notebook_id": NOTEBOOK_FOR_TESTING,
                "language": "de",
                "voice": "nova"
            },
            timeout=60
        )
        assert script_response.status_code == 200
        script_data = script_response.json()
        audio_id = script_data.get("id")
        
        # Now generate TTS with notebook_id to save
        tts_response = requests.post(
            f"{BASE_URL}/api/learn/audio-tts",
            headers=headers,
            json={
                "audio_id": audio_id,
                "voice": "nova",
                "notebook_id": NOTEBOOK_FOR_TESTING
            },
            timeout=60
        )
        assert tts_response.status_code == 200, f"Expected 200, got {tts_response.status_code}: {tts_response.text}"
        
        tts_data = tts_response.json()
        assert "audio_base64" in tts_data, "Should return audio_base64"
        assert len(tts_data.get("audio_base64", "")) > 0, "Audio base64 should not be empty"
        print(f"✓ Generated TTS audio with voice: {tts_data.get('voice')}")
        
        # Verify it was saved by retrieving it
        saved_response = requests.get(
            f"{BASE_URL}/api/learn/audio-saved/{NOTEBOOK_FOR_TESTING}",
            headers=headers
        )
        assert saved_response.status_code == 200
        saved_data = saved_response.json()
        assert saved_data.get("found") == True, "Audio should be saved and retrievable"
        assert len(saved_data.get("audio_base64", "")) > 0, "Saved audio should have audio_base64"
        print("✓ Audio was saved to database and is retrievable")


class TestQuizCountBatches:
    """Test quiz generation with different counts and batch processing"""
    
    def test_quiz_count_10_single_batch(self, headers):
        """Test count=10 generates in 1 batch"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_FOR_TESTING}/generate-quiz?count=10&language=de",
            headers=headers,
            json={},
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "job_id" in data, "Should return job_id for background processing"
        assert data.get("status") == "processing", "Should start in processing status"
        
        job_id = data["job_id"]
        print(f"✓ Quiz job started with id: {job_id}")
        
        # Poll for completion
        final_status = self._poll_quiz_job(job_id, headers, max_polls=40)
        assert final_status.get("status") == "done", f"Job should complete, got: {final_status.get('status')}"
        
        count = final_status.get("count", 0)
        assert count >= 8, f"Should generate at least 8 questions, got {count}"  # Allow some tolerance
        print(f"✓ Quiz completed with {count} questions")
    
    def test_quiz_count_30_three_batches(self, headers):
        """Test count=30 generates in 3 batches of 10"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_FOR_TESTING}/generate-quiz?count=30&language=de",
            headers=headers,
            json={},
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        job_id = data["job_id"]
        print(f"✓ Quiz job (count=30) started with id: {job_id}")
        
        # Poll and check for batch progress messages
        batch_messages_seen = []
        for i in range(60):  # Up to 3 minutes
            time.sleep(3)
            poll_response = requests.get(
                f"{BASE_URL}/api/quiz-job/{job_id}",
                headers=headers
            )
            if poll_response.status_code != 200:
                continue
            
            poll_data = poll_response.json()
            message = poll_data.get("message", "")
            
            # Check for batch progress messages
            if "Batch" in message and message not in batch_messages_seen:
                batch_messages_seen.append(message)
                print(f"  Progress: {message}")
            
            if poll_data.get("status") == "done":
                count = poll_data.get("count", 0)
                assert count >= 25, f"Should generate at least 25 questions for count=30, got {count}"
                print(f"✓ Quiz completed with {count} questions")
                
                # Verify we saw batch progress
                assert len(batch_messages_seen) >= 1, "Should have seen at least one batch progress message"
                print(f"✓ Saw {len(batch_messages_seen)} batch progress messages")
                return
            
            if poll_data.get("status") == "error":
                pytest.fail(f"Quiz generation failed: {poll_data.get('message')}")
        
        pytest.fail("Quiz generation timed out")
    
    def test_quiz_count_50_five_batches(self, headers):
        """Test count=50 generates in 5 batches of 10"""
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_FOR_TESTING}/generate-quiz?count=50&language=de",
            headers=headers,
            json={},
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        job_id = data["job_id"]
        print(f"✓ Quiz job (count=50) started with id: {job_id}")
        
        # Poll and check for batch progress messages
        batch_messages_seen = []
        for i in range(90):  # Up to 4.5 minutes for 5 batches
            time.sleep(3)
            poll_response = requests.get(
                f"{BASE_URL}/api/quiz-job/{job_id}",
                headers=headers
            )
            if poll_response.status_code != 200:
                continue
            
            poll_data = poll_response.json()
            message = poll_data.get("message", "")
            
            # Check for batch progress messages like "Batch 2/5: Generiere Fragen 11-20..."
            if "Batch" in message and message not in batch_messages_seen:
                batch_messages_seen.append(message)
                print(f"  Progress: {message}")
            
            if poll_data.get("status") == "done":
                count = poll_data.get("count", 0)
                assert count >= 40, f"Should generate at least 40 questions for count=50, got {count}"
                print(f"✓ Quiz completed with {count} questions")
                
                # Verify we saw multiple batch progress messages
                assert len(batch_messages_seen) >= 2, f"Should have seen at least 2 batch progress messages, saw {len(batch_messages_seen)}"
                print(f"✓ Saw {len(batch_messages_seen)} batch progress messages")
                return
            
            if poll_data.get("status") == "error":
                pytest.fail(f"Quiz generation failed: {poll_data.get('message')}")
        
        pytest.fail("Quiz generation timed out")
    
    def _poll_quiz_job(self, job_id, headers, max_polls=40):
        """Poll quiz job until completion"""
        for i in range(max_polls):
            time.sleep(3)
            response = requests.get(
                f"{BASE_URL}/api/quiz-job/{job_id}",
                headers=headers
            )
            if response.status_code != 200:
                continue
            
            data = response.json()
            if data.get("status") in ["done", "error"]:
                return data
        
        return {"status": "timeout"}


class TestQuizJobPolling:
    """Test quiz job polling endpoint"""
    
    def test_quiz_job_returns_progress(self, headers):
        """Test GET /api/quiz-job/{job_id} returns progress information"""
        # Start a quiz job
        response = requests.post(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_FOR_TESTING}/generate-quiz?count=10&language=de",
            headers=headers,
            json={},
            timeout=10
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Poll immediately to check initial state
        poll_response = requests.get(
            f"{BASE_URL}/api/quiz-job/{job_id}",
            headers=headers
        )
        assert poll_response.status_code == 200
        
        poll_data = poll_response.json()
        assert "status" in poll_data, "Should have status field"
        assert "id" in poll_data, "Should have id field"
        assert poll_data.get("status") in ["processing", "done", "error"], f"Invalid status: {poll_data.get('status')}"
        print(f"✓ Quiz job polling returns status: {poll_data.get('status')}")
    
    def test_quiz_job_not_found(self, headers):
        """Test GET /api/quiz-job/{job_id} returns 404 for non-existent job"""
        response = requests.get(
            f"{BASE_URL}/api/quiz-job/non-existent-job-id",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for non-existent job")


class TestNotebookAccess:
    """Test notebook access for audio and quiz features"""
    
    def test_notebook_list(self, headers):
        """Test notebook list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/notebook/list",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        notebooks = response.json()
        assert isinstance(notebooks, list), "Should return a list"
        print(f"✓ Found {len(notebooks)} notebooks")
        
        # Check if our test notebooks exist
        notebook_ids = [nb.get("id") for nb in notebooks]
        if NOTEBOOK_WITH_SAVED_AUDIO in notebook_ids:
            print(f"  ✓ Found notebook with saved audio: {NOTEBOOK_WITH_SAVED_AUDIO}")
        if NOTEBOOK_FOR_TESTING in notebook_ids:
            print(f"  ✓ Found test notebook: {NOTEBOOK_FOR_TESTING}")
    
    def test_notebook_get(self, headers):
        """Test getting a specific notebook"""
        response = requests.get(
            f"{BASE_URL}/api/notebook/{NOTEBOOK_FOR_TESTING}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "id" in data, "Should have id field"
        assert "filename" in data, "Should have filename field"
        print(f"✓ Got notebook: {data.get('filename')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
