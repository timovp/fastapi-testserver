# tests/test_api.py
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# 1) Create a temp file for SQLite and point DATABASE_URL at it
_dbf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_dbf.name}"
os.environ["MY_API_KEY"] = "testkey123"

# 2) Now import your app & models
from main import app, engine, SQLModel, AcceptedInvoiceNumber, AcceptedVendorName


# 3) Fixture to reset the schema before each test
@pytest.fixture(autouse=True)
def init_db():
    # Drop any existing tables, then recreate them
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    # (we don’t delete the file here so each test can open it;
    # the file cleanup happens automatically when the container/VM goes away)


# 4) TestClient fixture
@pytest.fixture
def client():
    return TestClient(app)


# 5) Tests
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_empty_lists(client):
    h = {"X-API-KEY": "testkey123"}
    assert client.get("/accepted_invoice_numbers", headers=h).json() == []
    assert client.get("/accepted_vendor_names", headers=h).json() == []


@pytest.mark.parametrize("num", ["X1", "Y2", "Z3"])
def test_invoice_crud(client, num):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    # CREATE
    r = client.post(
        "/accepted_invoice_numbers", headers=h, json={"accepted_invoice_number": num}
    )
    assert r.status_code == 201
    inv = r.json()
    assert inv["accepted_invoice_number"] == num

    # UPDATE
    newval = num + "_UPD"
    r2 = client.put(
        f"/accepted_invoice_numbers/{inv['id']}",
        headers=h,
        params={"invoice_number": newval},
    )
    assert r2.status_code == 200
    assert r2.json()["accepted_invoice_number"] == newval

    # DELETE
    r3 = client.delete(
        f"/accepted_invoice_numbers/{inv['id']}",
        headers=h,
    )
    assert r3.status_code == 204
    # Verify deletion
    r4 = client.get(
        "/accepted_invoice_numbers",
        headers=h,
    )
    assert r4.status_code == 200
    assert r4.json() == []


@pytest.mark.parametrize("name", ["Acme", "Globex"])
def test_vendor_crud(client, name):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    # CREATE
    r = client.post(
        "/accepted_vendor_names", headers=h, json={"accepted_vendor_name": name}
    )
    assert r.status_code == 201
    v = r.json()
    assert v["accepted_vendor_name"] == name

    # UPDATE
    newval = name + "_UPD"
    r2 = client.put(
        f"/accepted_vendor_names/{v['id']}", headers=h, params={"vendor_name": newval}
    )
    assert r2.status_code == 200
    assert r2.json()["accepted_vendor_name"] == newval

    # DELETE
    r3 = client.delete(
        f"/accepted_vendor_names/{v['id']}",
        headers=h,
    )
    assert r3.status_code == 204
    # Verify deletion
    r4 = client.get(
        "/accepted_vendor_names",
        headers=h,
    )
    assert r4.status_code == 200
    # Should not contain the deleted vendor
    vendor_names = [vendor["accepted_vendor_name"] for vendor in r4.json()]
    assert newval not in vendor_names


def test_get_vendor_list(client):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    r1 = client.post(
        "/accepted_vendor_names", headers=h, json={"accepted_vendor_name": "TestVendor"}
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/accepted_vendor_names",
        headers=h,
        json={"accepted_vendor_name": "TestVendor2"},
    )
    assert r2.status_code == 201
    r = client.get(
        "/accepted_vendor_list",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json() == ["TestVendor", "TestVendor2"]


def test_get_invoice_list(client):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    r1 = client.post(
        "/accepted_invoice_numbers",
        headers=h,
        json={"accepted_invoice_number": "INV001"},
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/accepted_invoice_numbers",
        headers=h,
        json={"accepted_invoice_number": "INV002"},
    )
    assert r2.status_code == 201
    r = client.get(
        "/accepted_invoice_list",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json() == ["INV001", "INV002"]


def test_lookup_vendor(client):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    r1 = client.post(
        "/accepted_vendor_names", headers=h, json={"accepted_vendor_name": "TestVendor"}
    )
    assert r1.status_code == 201
    vendor_id = r1.json()["id"]
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "TestVendor"},
    )
    assert r.status_code == 200
    assert r.json() == [vendor_id]


def test_lookup_invoice(client):
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    r1 = client.post(
        "/accepted_invoice_numbers",
        headers=h,
        json={"accepted_invoice_number": "INV001"},
    )
    assert r1.status_code == 201

    assert r1.status_code == 201
    invoice_id = r1.json()["id"]
    r = client.get(
        "/invoice_number_lookup",
        headers=h,
        params={"invoice_number": "INV001"},
    )
    assert r.status_code == 200
    assert r.json() == [invoice_id]


def test_complete_invoice_workflow(client):
    """Test a complete workflow with multiple invoices"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Start with empty list
    r = client.get("/accepted_invoice_numbers", headers=h)
    assert r.status_code == 200
    assert r.json() == []
    
    # Create multiple invoices
    invoices = ["INV001", "INV002", "INV003"]
    created_ids = []
    
    for inv in invoices:
        r = client.post(
            "/accepted_invoice_numbers",
            headers=h,
            json={"accepted_invoice_number": inv}
        )
        assert r.status_code == 201
        created_ids.append(r.json()["id"])
    
    # Verify all are in the list
    r = client.get("/accepted_invoice_numbers", headers=h)
    assert r.status_code == 200
    all_invoices = r.json()
    assert len(all_invoices) == 3
    
    # Verify string list endpoint
    r = client.get("/accepted_invoice_list", headers=h)
    assert r.status_code == 200
    invoice_list = r.json()
    assert set(invoice_list) == set(invoices)
    
    # Update one invoice
    r = client.put(
        f"/accepted_invoice_numbers/{created_ids[0]}",
        headers=h,
        params={"invoice_number": "INV001_UPDATED"}
    )
    assert r.status_code == 200
    assert r.json()["accepted_invoice_number"] == "INV001_UPDATED"
    
    # Delete one invoice
    r = client.delete(f"/accepted_invoice_numbers/{created_ids[1]}", headers=h)
    assert r.status_code == 204
    
    # Verify final state
    r = client.get("/accepted_invoice_numbers", headers=h)
    assert r.status_code == 200
    final_invoices = r.json()
    assert len(final_invoices) == 2
    
    # Check the remaining invoices
    remaining_numbers = [inv["accepted_invoice_number"] for inv in final_invoices]
    assert "INV001_UPDATED" in remaining_numbers
    assert "INV003" in remaining_numbers
    assert "INV002" not in remaining_numbers


def test_complete_vendor_workflow(client):
    """Test a complete workflow with multiple vendors"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Start with empty list
    r = client.get("/accepted_vendor_names", headers=h)
    assert r.status_code == 200
    assert r.json() == []
    
    # Create multiple vendors
    vendors = ["Acme Corp", "Global Inc", "Tech Solutions"]
    created_ids = []
    
    for vendor in vendors:
        r = client.post(
            "/accepted_vendor_names",
            headers=h,
            json={"accepted_vendor_name": vendor}
        )
        assert r.status_code == 201
        created_ids.append(r.json()["id"])
    
    # Verify all are in the list
    r = client.get("/accepted_vendor_names", headers=h)
    assert r.status_code == 200
    all_vendors = r.json()
    assert len(all_vendors) == 3
    
    # Test lookup functionality
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "Acme Corp"}
    )
    assert r.status_code == 200
    assert created_ids[0] in r.json()
    
    # Update a vendor
    r = client.put(
        f"/accepted_vendor_names/{created_ids[1]}",
        headers=h,
        params={"vendor_name": "Global Inc UPDATED"}
    )
    assert r.status_code == 200
    assert r.json()["accepted_vendor_name"] == "Global Inc UPDATED"
    
    # Delete a vendor
    r = client.delete(f"/accepted_vendor_names/{created_ids[2]}", headers=h)
    assert r.status_code == 204
    
    # Verify final state
    r = client.get("/accepted_vendor_list", headers=h)
    assert r.status_code == 200
    final_vendor_list = r.json()
    assert len(final_vendor_list) == 2
    assert "Acme Corp" in final_vendor_list
    assert "Global Inc UPDATED" in final_vendor_list
    assert "Tech Solutions" not in final_vendor_list


def test_case_sensitivity_in_lookups(client):
    """Test that lookups are case sensitive"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Create a vendor
    r = client.post(
        "/accepted_vendor_names",
        headers=h,
        json={"accepted_vendor_name": "TestVendor"}
    )
    assert r.status_code == 201
    vendor_id = r.json()["id"]
    
    # Exact match should work
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "TestVendor"}
    )
    assert r.status_code == 200
    assert vendor_id in r.json()
    
    # Different case should not match
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "testvendor"}
    )
    assert r.status_code == 200
    assert r.json() == []
    
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "TESTVENDOR"}
    )
    assert r.status_code == 200
    assert r.json() == []


def test_whitespace_handling(client):
    """Test handling of whitespace in values"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Create invoice with leading/trailing whitespace
    r = client.post(
        "/accepted_invoice_numbers",
        headers=h,
        json={"accepted_invoice_number": "  INV001  "}
    )
    assert r.status_code == 201
    # Whitespace should be preserved
    assert r.json()["accepted_invoice_number"] == "  INV001  "
    
    # Lookup should be exact match including whitespace
    r = client.get(
        "/invoice_number_lookup",
        headers=h,
        params={"invoice_number": "  INV001  "}
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    
    # Without whitespace should not match
    r = client.get(
        "/invoice_number_lookup",
        headers=h,
        params={"invoice_number": "INV001"}
    )
    assert r.status_code == 200
    assert r.json() == []


def test_numeric_strings_in_vendor_names(client):
    """Test that vendor names can be numeric strings"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Create vendor with numeric name
    r = client.post(
        "/accepted_vendor_names",
        headers=h,
        json={"accepted_vendor_name": "12345"}
    )
    assert r.status_code == 201
    assert r.json()["accepted_vendor_name"] == "12345"
    
    # Should appear in vendor list
    r = client.get("/accepted_vendor_list", headers=h)
    assert r.status_code == 200
    assert "12345" in r.json()


def test_empty_database_responses(client):
    """Test responses when database is empty"""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # All list endpoints should return empty arrays
    endpoints = [
        "/accepted_invoice_numbers",
        "/accepted_vendor_names", 
        "/accepted_vendor_list",
        "/accepted_invoice_list"
    ]
    
    for endpoint in endpoints:
        r = client.get(endpoint, headers=h)
        assert r.status_code == 200
        assert r.json() == []
    
    # Lookup endpoints should return empty arrays for any search
    r = client.get(
        "/vendor_name_lookup",
        headers=h,
        params={"vendor_name": "NonExistent"}
    )
    assert r.status_code == 200
    assert r.json() == []
    
    r = client.get(
        "/invoice_number_lookup", 
        headers=h,
        params={"invoice_number": "NonExistent"}
    )
    assert r.status_code == 200
    assert r.json() == []


def test_edit_functionality_endpoints(client):
    """Test that the edit functionality endpoints work correctly."""
    h = {"X-API-KEY": "testkey123", "Content-Type": "application/json"}
    
    # Test invoice edit
    r1 = client.post(
        "/accepted_invoice_numbers",
        headers=h,
        json={"accepted_invoice_number": "EDIT-TEST-001"},
    )
    assert r1.status_code == 201
    invoice_data = r1.json()
    invoice_id = invoice_data["id"]
    
    # Test the exact endpoint the frontend should use
    r2 = client.put(
        f"/accepted_invoice_numbers/{invoice_id}",
        headers=h,
        params={"invoice_number": "EDIT-TEST-001-UPDATED"},
    )
    assert r2.status_code == 200
    assert r2.json()["accepted_invoice_number"] == "EDIT-TEST-001-UPDATED"
    
    # Test vendor edit
    r3 = client.post(
        "/accepted_vendor_names",
        headers=h,
        json={"accepted_vendor_name": "EditTestVendor"},
    )
    assert r3.status_code == 201
    vendor_data = r3.json()
    vendor_id = vendor_data["id"]
    
    # Test the exact endpoint the frontend should use
    r4 = client.put(
        f"/accepted_vendor_names/{vendor_id}",
        headers=h,
        params={"vendor_name": "EditTestVendor-UPDATED"},
    )
    assert r4.status_code == 200
    assert r4.json()["accepted_vendor_name"] == "EditTestVendor-UPDATED"
