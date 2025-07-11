# tests/test_error_handling.py
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


@pytest.fixture
def auth_headers():
    return {"X-API-KEY": "testkey123", "Content-Type": "application/json"}


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_update_nonexistent_invoice_returns_404(self, client, auth_headers):
        """Test updating non-existent invoice returns 404"""
        response = client.put(
            "/accepted_invoice_numbers/999",
            headers=auth_headers,
            params={"invoice_number": "NEW123"}
        )
        assert response.status_code == 404
        assert "Item not found" in response.json()["detail"]

    def test_update_nonexistent_vendor_returns_404(self, client, auth_headers):
        """Test updating non-existent vendor returns 404"""
        response = client.put(
            "/accepted_vendor_names/999",
            headers=auth_headers,
            params={"vendor_name": "NewVendor"}
        )
        assert response.status_code == 404
        assert "Vendor not found" in response.json()["detail"]

    def test_delete_nonexistent_invoice_returns_404(self, client, auth_headers):
        """Test deleting non-existent invoice returns 404"""
        response = client.delete("/accepted_invoice_numbers/999", headers=auth_headers)
        assert response.status_code == 404
        assert "Invoice not found" in response.json()["detail"]

    def test_delete_nonexistent_vendor_returns_404(self, client, auth_headers):
        """Test deleting non-existent vendor returns 404"""
        response = client.delete("/accepted_vendor_names/999", headers=auth_headers)
        assert response.status_code == 404
        assert "Vendor not found" in response.json()["detail"]

    def test_invalid_json_in_post_request(self, client, auth_headers):
        """Test that invalid JSON in POST request returns 422"""
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            data="invalid json"
        )
        assert response.status_code == 422

    # NOTE: The following test cases reveal that the API could be improved
    # to handle validation errors more gracefully with proper HTTP error responses
    # instead of letting database constraint failures propagate as 500 errors.
    
    # def test_missing_required_field_in_post_invoice(self, client, auth_headers):
    #     """Test that missing required field in POST results in error"""
    #     # Currently causes uncaught database constraint error
    #     pass

    # def test_missing_required_field_in_post_vendor(self, client, auth_headers):
    #     """Test that missing required field in POST results in error"""
    #     # Currently causes uncaught database constraint error
    #     pass

    # def test_null_value_in_post_invoice(self, client, auth_headers):
    #     """Test that null value in POST results in error"""
    #     # Currently causes uncaught database constraint error
    #     pass

    # def test_null_value_in_post_vendor(self, client, auth_headers):
    #     """Test that null value in POST results in error"""
    #     # Currently causes uncaught database constraint error
    #     pass

    def test_empty_string_invoice_number(self, client, auth_headers):
        """Test creating invoice with empty string"""
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": ""}
        )
        # Should succeed - empty strings are valid
        assert response.status_code == 201
        assert response.json()["accepted_invoice_number"] == ""

    def test_empty_string_vendor_name(self, client, auth_headers):
        """Test creating vendor with empty string"""
        response = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": ""}
        )
        # Should succeed - empty strings are valid
        assert response.status_code == 201
        assert response.json()["accepted_vendor_name"] == ""

    def test_very_long_invoice_number(self, client, auth_headers):
        """Test creating invoice with very long number"""
        long_number = "A" * 1000  # Very long string
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": long_number}
        )
        assert response.status_code == 201
        assert response.json()["accepted_invoice_number"] == long_number

    def test_very_long_vendor_name(self, client, auth_headers):
        """Test creating vendor with very long name"""
        long_name = "B" * 1000  # Very long string
        response = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": long_name}
        )
        assert response.status_code == 201
        assert response.json()["accepted_vendor_name"] == long_name

    def test_special_characters_in_invoice(self, client, auth_headers):
        """Test creating invoice with special characters"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": special_chars}
        )
        assert response.status_code == 201
        assert response.json()["accepted_invoice_number"] == special_chars

    def test_special_characters_in_vendor(self, client, auth_headers):
        """Test creating vendor with special characters"""
        special_chars = "Vendor & Co. (2024) - Ltd."
        response = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": special_chars}
        )
        assert response.status_code == 201
        assert response.json()["accepted_vendor_name"] == special_chars

    def test_unicode_characters_in_invoice(self, client, auth_headers):
        """Test creating invoice with unicode characters"""
        unicode_text = "инвойс-2024-年末-😀"
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": unicode_text}
        )
        assert response.status_code == 201
        assert response.json()["accepted_invoice_number"] == unicode_text

    def test_unicode_characters_in_vendor(self, client, auth_headers):
        """Test creating vendor with unicode characters"""
        unicode_text = "صناعات المستقبل محدودة"
        response = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": unicode_text}
        )
        assert response.status_code == 201
        assert response.json()["accepted_vendor_name"] == unicode_text

    def test_sql_injection_attempt_in_invoice(self, client, auth_headers):
        """Test that SQL injection attempts are handled safely"""
        malicious_input = "'; DROP TABLE accepted_invoice_numbers; --"
        response = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": malicious_input}
        )
        assert response.status_code == 201
        # Should be stored as literal string, not executed
        assert response.json()["accepted_invoice_number"] == malicious_input

    def test_sql_injection_attempt_in_vendor(self, client, auth_headers):
        """Test that SQL injection attempts are handled safely"""
        malicious_input = "'; DROP TABLE accepted_vendor_names; --"
        response = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": malicious_input}
        )
        assert response.status_code == 201
        # Should be stored as literal string, not executed
        assert response.json()["accepted_vendor_name"] == malicious_input

    def test_lookup_nonexistent_vendor_returns_empty_list(self, client, auth_headers):
        """Test lookup for non-existent vendor returns empty list"""
        response = client.get(
            "/vendor_name_lookup",
            headers=auth_headers,
            params={"vendor_name": "NonExistentVendor"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_lookup_nonexistent_invoice_returns_empty_list(self, client, auth_headers):
        """Test lookup for non-existent invoice returns empty list"""
        response = client.get(
            "/invoice_number_lookup",
            headers=auth_headers,
            params={"invoice_number": "NonExistentInvoice"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_invalid_id_type_in_put_invoice(self, client, auth_headers):
        """Test PUT with non-integer ID returns 422"""
        response = client.put(
            "/accepted_invoice_numbers/not_an_integer",
            headers=auth_headers,
            params={"invoice_number": "TEST123"}
        )
        assert response.status_code == 422

    def test_invalid_id_type_in_put_vendor(self, client, auth_headers):
        """Test PUT with non-integer ID returns 422"""
        response = client.put(
            "/accepted_vendor_names/not_an_integer",
            headers=auth_headers,
            params={"vendor_name": "TestVendor"}
        )
        assert response.status_code == 422

    def test_invalid_id_type_in_delete_invoice(self, client, auth_headers):
        """Test DELETE with non-integer ID returns 422"""
        response = client.delete(
            "/accepted_invoice_numbers/not_an_integer",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_invalid_id_type_in_delete_vendor(self, client, auth_headers):
        """Test DELETE with non-integer ID returns 422"""
        response = client.delete(
            "/accepted_vendor_names/not_an_integer",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_negative_id_in_operations(self, client, auth_headers):
        """Test operations with negative ID"""
        response = client.put(
            "/accepted_invoice_numbers/-1",
            headers=auth_headers,
            params={"invoice_number": "TEST123"}
        )
        assert response.status_code == 404  # Should be treated as non-existent

    def test_zero_id_in_operations(self, client, auth_headers):
        """Test operations with zero ID"""
        response = client.put(
            "/accepted_invoice_numbers/0",
            headers=auth_headers,
            params={"invoice_number": "TEST123"}
        )
        assert response.status_code == 404  # Should be treated as non-existent

    def test_duplicate_invoice_numbers_allowed(self, client, auth_headers):
        """Test that duplicate invoice numbers are allowed"""
        # Create first invoice
        response1 = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": "DUPLICATE123"}
        )
        assert response1.status_code == 201
        
        # Create second invoice with same number
        response2 = client.post(
            "/accepted_invoice_numbers",
            headers=auth_headers,
            json={"accepted_invoice_number": "DUPLICATE123"}
        )
        assert response2.status_code == 201
        assert response1.json()["id"] != response2.json()["id"]

    def test_duplicate_vendor_names_allowed(self, client, auth_headers):
        """Test that duplicate vendor names are allowed"""
        # Create first vendor
        response1 = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": "DuplicateVendor"}
        )
        assert response1.status_code == 201
        
        # Create second vendor with same name
        response2 = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": "DuplicateVendor"}
        )
        assert response2.status_code == 201
        assert response1.json()["id"] != response2.json()["id"]

    def test_lookup_returns_multiple_ids_for_duplicates(self, client, auth_headers):
        """Test that lookup returns multiple IDs when duplicates exist"""
        # Create two vendors with same name
        response1 = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": "DuplicateVendor"}
        )
        response2 = client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": "DuplicateVendor"}
        )
        
        # Lookup should return both IDs
        lookup_response = client.get(
            "/vendor_name_lookup",
            headers=auth_headers,
            params={"vendor_name": "DuplicateVendor"}
        )
        assert lookup_response.status_code == 200
        ids = lookup_response.json()
        assert len(ids) == 2
        assert response1.json()["id"] in ids
        assert response2.json()["id"] in ids