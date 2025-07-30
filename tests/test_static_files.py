# tests/test_static_files.py
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Setup test database
_dbf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_dbf.name}"
os.environ["MY_API_KEY"] = "testkey123"

from main import app, engine, SQLModel


@pytest.fixture(autouse=True)
def init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


class TestStaticFiles:
    """Test static file serving functionality"""

    def test_root_serves_index_html(self, client):
        """Test that root URL serves index.html"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Should contain expected HTML content
        content = response.text
        assert "<!DOCTYPE html>" in content
        assert "<title>Quick CRUD UI</title>" in content
        assert "Manage Your Lists" in content

    def test_index_html_contains_expected_elements(self, client):
        """Test that index.html contains expected UI elements"""
        response = client.get("/")
        content = response.text
        
        # Check for key UI elements
        assert "Invoice Numbers" in content
        assert "Vendor Names" in content
        assert "new-invoice" in content  # Input ID
        assert "new-vendor" in content   # Input ID
        assert "Add Invoice" in content
        assert "Add Vendor" in content

    def test_index_html_contains_api_integration(self, client):
        """Test that index.html contains API integration code"""
        response = client.get("/")
        content = response.text
        
        # Check for API endpoints in JavaScript
        assert "/accepted_invoice_numbers" in content
        assert "/accepted_vendor_names" in content
        assert "X-API-KEY" in content
        assert "fetch(" in content

    def test_static_directory_accessible(self, client):
        """Test that static directory is mounted and accessible"""
        # Test accessing the existing index.html through static mount
        response = client.get("/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_static_nonexistent_file_returns_404(self, client):
        """Test that non-existent static file returns 404"""
        response = client.get("/static/nonexistent.js")
        assert response.status_code == 404

    def test_static_file_security_no_directory_traversal(self, client):
        """Test that directory traversal attempts are blocked"""
        # Attempt directory traversal
        response = client.get("/static/../main.py")
        assert response.status_code in (404, 403)

    def test_static_file_security_no_system_files(self, client):
        """Test that system files cannot be accessed through static mount"""
        # Attempt to access system files
        response = client.get("/static/../../../../etc/passwd")
        assert response.status_code in (404, 403)

    def test_root_endpoint_no_auth_required(self, client):
        """Test that root endpoint doesn't require authentication"""
        # Should work without any headers
        response = client.get("/")
        assert response.status_code == 200

    def test_static_files_no_auth_required(self, client):
        """Test that static files don't require authentication"""
        # Should work without any headers
        response = client.get("/static/index.html")
        assert response.status_code == 200

    def test_response_headers_for_html(self, client):
        """Test that HTML responses have appropriate headers"""
        response = client.get("/")
        
        # Check content type
        assert "text/html" in response.headers.get("content-type", "")
        
        # Should not have API-related headers like those from FastAPI
        assert "X-API-KEY" not in response.headers

    def test_static_mount_name(self, client):
        """Test that static mount is working correctly"""
        # The static mount should be accessible via /static prefix
        response = client.get("/static/index.html")
        assert response.status_code == 200
        
        # But direct access to static without prefix should 404
        response = client.get("/index.html")
        assert response.status_code == 404

    def test_content_length_header(self, client):
        """Test that content-length header is set for static files"""
        response = client.get("/")
        assert "content-length" in response.headers
        assert int(response.headers["content-length"]) > 0

    def test_etag_or_cache_headers(self, client):
        """Test for cache-related headers"""
        response = client.get("/")
        # At minimum, should have some form of caching header
        # (The exact headers depend on StaticFiles implementation)
        assert "cache-control" in response.headers or "etag" in response.headers, \
            "Expected cache-related headers (e.g., 'cache-control' or 'etag') to be present."

    def test_concurrent_static_file_access(self, client):
        """Test that multiple concurrent requests to static files work"""
        import concurrent.futures
        
        def make_request():
            return client.get("/")
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    def test_head_request_to_root(self, client):
        """Test HEAD request to root endpoint"""
        response = client.head("/")
        # HEAD requests might not be supported on all endpoints
        assert response.status_code in [200, 405]
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
            # HEAD should not have body
            assert len(response.content) == 0

    def test_head_request_to_static_file(self, client):
        """Test HEAD request to static file"""
        response = client.head("/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # HEAD should not have body
        assert len(response.content) == 0