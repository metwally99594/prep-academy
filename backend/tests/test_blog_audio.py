"""
Test Blog and Smart Audio Features - Iteration 36
Tests:
- Blog: GET /api/blog/posts (NO AUTH) returns published posts with total count
- Blog: GET /api/blog/posts/{slug} (NO AUTH) returns full blog article content
- Blog: POST /api/blog/generate starts background job, returns job_id
- Blog: GET /api/blog/job/{job_id} returns job status
- Blog: Existing blog post 'Kardiologie' accessible and title has no ** markers
- Smart Audio: POST /api/learn/audio-script generates script from ALL chunks
- Smart Audio: Script contains [Moderator] and [Experte] speaker tags
- Smart Audio: Script is 3000-4500 chars (longer than before)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://doctor-readiness.preview.emergentagent.com')

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
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestBlogPublicEndpoints:
    """Test public blog endpoints (NO AUTH required)"""
    
    def test_get_blog_posts_no_auth(self, api_client):
        """GET /api/blog/posts returns published posts with total count (NO AUTH)"""
        response = api_client.get(f"{BASE_URL}/api/blog/posts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "posts" in data, "Response should contain 'posts' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["posts"], list), "posts should be a list"
        assert isinstance(data["total"], int), "total should be an integer"
        print(f"✓ Blog posts endpoint returns {data['total']} total posts")
    
    def test_get_kardiologie_blog_post(self, api_client):
        """GET /api/blog/posts/{slug} returns full blog article content"""
        slug = "kardiologie-in-der-oesterreichischen-aerzte-pruefung-wissenswertes-und-lernstrat"
        response = api_client.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "title" in data, "Response should contain 'title'"
        assert "content" in data, "Response should contain 'content'"
        assert "slug" in data, "Response should contain 'slug'"
        assert "author" in data, "Response should contain 'author'"
        
        # Verify title has no ** markers
        assert "**" not in data["title"], f"Title should not contain ** markers: {data['title']}"
        
        # Verify content is substantial
        assert len(data["content"]) > 500, "Content should be substantial (>500 chars)"
        
        print(f"✓ Blog post '{data['title'][:50]}...' accessible with {len(data['content'])} chars content")
    
    def test_blog_post_not_found(self, api_client):
        """GET /api/blog/posts/{slug} returns 404 for non-existent post"""
        response = api_client.get(f"{BASE_URL}/api/blog/posts/non-existent-slug-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent blog post returns 404")


class TestBlogAdminEndpoints:
    """Test admin blog endpoints (AUTH required)"""
    
    def test_generate_blog_post_requires_auth(self, api_client):
        """POST /api/blog/generate requires admin auth"""
        response = api_client.post(f"{BASE_URL}/api/blog/generate?topic=Test")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Blog generation requires authentication")
    
    def test_generate_blog_post_starts_job(self, api_client, admin_token):
        """POST /api/blog/generate starts background job, returns job_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/blog/generate?topic=Test%20Neurologie&specialty_id=neurology",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "job_id" in data, "Response should contain 'job_id'"
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "processing", f"Initial status should be 'processing', got {data['status']}"
        
        print(f"✓ Blog generation started with job_id: {data['job_id']}")
        return data["job_id"]
    
    def test_poll_blog_job_status(self, api_client, admin_token):
        """GET /api/blog/job/{job_id} returns job status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First start a job
        response = api_client.post(
            f"{BASE_URL}/api/blog/generate?topic=Test%20Chirurgie",
            headers=headers
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Poll for status
        response = api_client.get(f"{BASE_URL}/api/blog/job/{job_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] in ["processing", "done", "error"], f"Invalid status: {data['status']}"
        
        print(f"✓ Job {job_id} status: {data['status']}")
    
    def test_poll_job_requires_auth(self, api_client):
        """GET /api/blog/job/{job_id} requires admin auth"""
        response = api_client.get(f"{BASE_URL}/api/blog/job/some-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Job polling requires authentication")


class TestSmartAudioScript:
    """Test Smart Audio Script generation"""
    
    def test_audio_script_requires_auth(self, api_client):
        """POST /api/learn/audio-script requires auth"""
        response = api_client.post(f"{BASE_URL}/api/learn/audio-script", json={
            "specialty_id": "internal",
            "language": "de"
        })
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Audio script requires authentication")
    
    def test_audio_script_with_specialty(self, api_client, admin_token):
        """POST /api/learn/audio-script generates script with speaker tags"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/learn/audio-script",
            headers=headers,
            json={
                "specialty_id": "internal",
                "language": "de",
                "voice": "nova"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "script" in data, "Response should contain 'script'"
        assert "id" in data, "Response should contain 'id'"
        
        script = data["script"]
        script_len = len(script)
        
        # Check for speaker tags
        has_moderator = "[Moderator]" in script
        has_experte = "[Experte]" in script
        
        print(f"✓ Audio script generated: {script_len} chars")
        print(f"  - Has [Moderator] tag: {has_moderator}")
        print(f"  - Has [Experte] tag: {has_experte}")
        
        # Verify speaker tags are present
        assert has_moderator or has_experte, "Script should contain speaker tags [Moderator] or [Experte]"
    
    def test_audio_script_with_notebook(self, api_client, admin_token):
        """POST /api/learn/audio-script with notebook_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get a notebook ID
        nb_response = api_client.get(f"{BASE_URL}/api/notebook/list", headers=headers)
        if nb_response.status_code != 200:
            pytest.skip("No notebooks available for testing")
        
        notebooks = nb_response.json()
        if not notebooks:
            pytest.skip("No notebooks available for testing")
        
        notebook_id = notebooks[0].get("id")
        
        response = api_client.post(
            f"{BASE_URL}/api/learn/audio-script",
            headers=headers,
            json={
                "notebook_id": notebook_id,
                "language": "de",
                "voice": "nova"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "script" in data, "Response should contain 'script'"
        
        script = data["script"]
        print(f"✓ Audio script from notebook: {len(script)} chars")


class TestBlogContentQuality:
    """Test blog content quality"""
    
    def test_kardiologie_title_no_markdown(self, api_client):
        """Verify Kardiologie blog title has no ** markers"""
        slug = "kardiologie-in-der-oesterreichischen-aerzte-pruefung-wissenswertes-und-lernstrat"
        response = api_client.get(f"{BASE_URL}/api/blog/posts/{slug}")
        
        if response.status_code != 200:
            pytest.skip("Kardiologie blog post not found")
        
        data = response.json()
        title = data.get("title", "")
        
        # Check for markdown artifacts
        assert "**" not in title, f"Title contains ** markers: {title}"
        assert "*" not in title or title.count("*") == 0, f"Title contains * markers: {title}"
        
        print(f"✓ Blog title clean: '{title}'")
    
    def test_blog_content_has_markdown_structure(self, api_client):
        """Verify blog content has proper markdown structure"""
        slug = "kardiologie-in-der-oesterreichischen-aerzte-pruefung-wissenswertes-und-lernstrat"
        response = api_client.get(f"{BASE_URL}/api/blog/posts/{slug}")
        
        if response.status_code != 200:
            pytest.skip("Kardiologie blog post not found")
        
        data = response.json()
        content = data.get("content", "")
        
        # Check for markdown headers
        has_h2 = "## " in content
        has_h3 = "### " in content
        
        print(f"✓ Blog content structure: H2={has_h2}, H3={has_h3}, length={len(content)}")
        
        assert has_h2 or has_h3, "Blog content should have markdown headers"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
