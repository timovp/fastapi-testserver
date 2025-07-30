# tests/test_authentication.py
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


class TestAuthentication:
    """Test API key authentication for all protected endpoints"""
    
    # All protected endpoints
    protected_endpoints = [
        ("GET", "/accepted_invoice_numbers"),
        ("POST", "/accepted_invoice_numbers"),
        ("PUT", "/accepted_invoice_numbers/1"),
        ("DELETE", "/accepted_invoice_numbers/1"),
        ("GET", "/accepted_vendor_names"),
        ("POST", "/accepted_vendor_names"),
        ("PUT", "/accepted_vendor_names/1"),
        ("DELETE", "/accepted_vendor_names/1"),
        ("GET", "/accepted_vendor_list"),
        ("GET", "/accepted_invoice_list"),
        ("GET", "/vendor_name_lookup"),
        ("GET", "/invoice_number_lookup"),
    ]

    @pytest.mark.parametrize("method,endpoint", protected_endpoints)
    def test_missing_api_key_returns_401(self, client, method, endpoint):
        """Test that missing API key returns 401 for all protected endpoints"""
        response = getattr(client, method.lower())(endpoint)
        assert response.status_code == 401
        assert "Invalid or missing API Key" in response.json()["detail"]

    @pytest.mark.parametrize("method,endpoint", protected_endpoints)
    def test_invalid_api_key_returns_401(self, client, method, endpoint):
        """Test that invalid API key returns 401 for all protected endpoints"""
        headers = {"X-API-KEY": "invalid_key"}
        
        # Handle different request types
        if method == "POST":
            if "invoice" in endpoint:
                json_data = {"accepted_invoice_number": "TEST123"}
            else:
                json_data = {"accepted_vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, json=json_data)
        elif method == "PUT":
            params = {"invoice_number": "TEST123"} if "invoice" in endpoint else {"vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, params=params)
        elif method == "GET" and "lookup" in endpoint:
            params = {"invoice_number": "TEST123"} if "invoice" in endpoint else {"vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, params=params)
        else:
            response = getattr(client, method.lower())(endpoint, headers=headers)
            
        assert response.status_code == 401
        assert "Invalid or missing API Key" in response.json()["detail"]

    @pytest.mark.parametrize("method,endpoint", protected_endpoints)
    def test_empty_api_key_returns_401(self, client, method, endpoint):
        """Test that empty API key returns 401 for all protected endpoints"""
        headers = {"X-API-KEY": ""}
        
        # Handle different request types
        if method == "POST":
            if "invoice" in endpoint:
                json_data = {"accepted_invoice_number": "TEST123"}
            else:
                json_data = {"accepted_vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, json=json_data)
        elif method == "PUT":
            params = {"invoice_number": "TEST123"} if "invoice" in endpoint else {"vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, params=params)
        elif method == "GET" and "lookup" in endpoint:
            params = {"invoice_number": "TEST123"} if "invoice" in endpoint else {"vendor_name": "TestVendor"}
            response = getattr(client, method.lower())(endpoint, headers=headers, params=params)
        else:
            response = getattr(client, method.lower())(endpoint, headers=headers)
            
        assert response.status_code == 401
        assert "Invalid or missing API Key" in response.json()["detail"]

    def test_valid_api_key_allows_access(self, client):
        """Test that valid API key allows access to protected endpoints"""
        headers = {"X-API-KEY": "testkey123"}
        
        # Test GET endpoints that should work without data
        response = client.get("/accepted_invoice_numbers", headers=headers)
        assert response.status_code == 200
        
        response = client.get("/accepted_vendor_names", headers=headers)
        assert response.status_code == 200

    def test_healthz_endpoint_unprotected(self, client):
        """Test that health check endpoint doesn't require authentication"""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_endpoint_unprotected(self, client):
        """Test that root endpoint (serving index.html) doesn't require authentication"""
        response = client.get("/")
        assert response.status_code == 200
        # Should serve the index.html file
        assert "text/html" in response.headers.get("content-type", "")

    def test_static_files_unprotected(self, client):
        """Test that static files don't require authentication"""
        # This will 404 if the file doesn't exist, but shouldn't require auth
        response = client.get("/static/nonexistent.js")
        # Should be 404, not 401 (which would indicate auth was required)
        assert response.status_code == 404

    def test_api_key_case_sensitivity(self, client):
        """Test that API key is case sensitive"""
        headers = {"X-API-KEY": "TESTKEY123"}  # Wrong case
        response = client.get("/accepted_invoice_numbers", headers=headers)
        assert response.status_code == 401

    def test_api_key_header_name_case_insensitive(self, client):
        """Test that header name is case insensitive (HTTP standard)"""
        headers = {"x-api-key": "testkey123"}  # Different case
        response = client.get("/accepted_invoice_numbers", headers=headers)
        assert response.status_code == 200

    def test_api_key_with_whitespace(self, client):
        """Test that API key with whitespace fails"""
        headers = {"X-API-KEY": " testkey123 "}  # Extra whitespace
        response = client.get("/accepted_invoice_numbers", headers=headers)
        assert response.status_code == 401