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
