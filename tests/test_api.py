# tests/test_api.py
import os
import pytest
from fastapi.testclient import TestClient

# ensure our app picks up the test key
os.environ["MY_API_KEY"] = "testkey123"

from main import app, AcceptedInvoiceNumber, AcceptedVendorName, engine, SQLModel


# Re-create a fresh SQLite in-memory for tests
@pytest.fixture(autouse=True)
def init_db(monkeypatch):
    # point DATABASE_URL at a temp file or in-memory DB
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    # rebuild the engine/session based on the new env
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


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
