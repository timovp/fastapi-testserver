# tests/test_database_initialization.py
import os
import tempfile
import subprocess
import json
import pytest


def test_application_runs_without_initial_database():
    """Test that the application starts and works correctly without an existing database"""
    
    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test database path
        temp_db_path = os.path.join(temp_dir, "test_empty.db")
        
        # Create a test script that tests database initialization
        # Use uv run to ensure dependencies are available
        test_script = f'''
import os
import sys
import tempfile
os.environ["DATABASE_URL"] = "sqlite:///{temp_db_path}"
os.environ["MY_API_KEY"] = "test_init_key"

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health endpoint
response = client.get("/healthz")
assert response.status_code == 200, f"Health check failed: {{response.status_code}}"

# Test database operations - should automatically create database and tables
headers = {{"X-API-KEY": "test_init_key"}}

# Initially empty
response = client.get("/accepted_invoice_numbers", headers=headers)
assert response.status_code == 200, f"Get invoices failed: {{response.status_code}}"
assert response.json() == [], f"Expected empty list, got: {{response.json()}}"

# Create an item
create_data = {{"accepted_invoice_number": "INIT_TEST_001"}}
response = client.post("/accepted_invoice_numbers", 
                     headers={{**headers, "Content-Type": "application/json"}}, 
                     json=create_data)
assert response.status_code == 201, f"Create failed: {{response.status_code}}"

# Verify the item was saved
response = client.get("/accepted_invoice_numbers", headers=headers)
assert response.status_code == 200, f"Get after create failed: {{response.status_code}}"
items = response.json()
assert len(items) == 1, f"Expected 1 item, got {{len(items)}}: {{items}}"
assert items[0]["accepted_invoice_number"] == "INIT_TEST_001"

# Verify database file was created
assert os.path.exists("{temp_db_path}"), "Database file was not created"

print("SUCCESS: Application runs without initial database")
'''
        
        # Run the test script in a subprocess with uv run to ensure dependencies
        # Use the directory containing main.py as working directory
        main_py_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Try uv run first, fallback to python with explicit httpx install
        try:
            result = subprocess.run(
                ["uv", "run", "python", "-c", test_script], 
                cwd=main_py_dir,
                capture_output=True, 
                text=True
            )
        except FileNotFoundError:
            # Fallback: install httpx and run with python
            subprocess.run(["python", "-m", "pip", "install", "httpx"], 
                         cwd=main_py_dir, capture_output=True)
            result = subprocess.run(
                ["python", "-c", test_script], 
                cwd=main_py_dir,
                capture_output=True, 
                text=True
            )
        
        assert result.returncode == 0, f"Test failed with error: {result.stderr}"
        assert "SUCCESS: Application runs without initial database" in result.stdout


def test_application_handles_permission_denied_database_path():
    """Test that the application gracefully handles permission denied for default database path"""
    
    test_script = '''
import os
import sys

# Set environment to use an inaccessible path
os.environ["DATABASE_URL"] = "sqlite:////root/protected/items.db"
os.environ["MY_API_KEY"] = "test_permission_key"

from main import app, DATABASE_URL
from fastapi.testclient import TestClient

# Should have fallen back to local database
assert DATABASE_URL == "sqlite:///items.db", f"Expected fallback to items.db, got: {DATABASE_URL}"

# Application should work normally with fallback
client = TestClient(app)

# Test health endpoint
response = client.get("/healthz")
assert response.status_code == 200, f"Health check failed: {response.status_code}"

# Test database operations work with fallback
headers = {"X-API-KEY": "test_permission_key"}
response = client.get("/accepted_invoice_numbers", headers=headers)
assert response.status_code == 200, f"Database access failed: {response.status_code}"
assert isinstance(response.json(), list), f"Expected list response, got: {type(response.json())}"

print("SUCCESS: Application handles permission denied gracefully")
'''
    
    # Run the test script in a subprocess with uv run to ensure dependencies
    # Use the directory containing main.py as working directory
    main_py_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try uv run first, fallback to python with explicit httpx install
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", test_script], 
            cwd=main_py_dir,
            capture_output=True, 
            text=True
        )
    except FileNotFoundError:
        # Fallback: install httpx and run with python
        subprocess.run(["python", "-m", "pip", "install", "httpx"], 
                     cwd=main_py_dir, capture_output=True)
        result = subprocess.run(
            ["python", "-c", test_script], 
            cwd=main_py_dir,
            capture_output=True, 
            text=True
        )
    
    assert result.returncode == 0, f"Test failed with error: {result.stderr}"
    assert "SUCCESS: Application handles permission denied gracefully" in result.stdout


def test_database_initialization_is_idempotent():
    """Test that database initialization can be called multiple times safely"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "test_idempotent.db")
        
        test_script = f'''
import os
os.environ["DATABASE_URL"] = "sqlite:///{temp_db_path}"
os.environ["MY_API_KEY"] = "test_idempotent_key"

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
headers = {{"X-API-KEY": "test_idempotent_key"}}

# Multiple database accesses should not cause errors
for i in range(3):
    response = client.get("/accepted_invoice_numbers", headers=headers)
    assert response.status_code == 200, f"Access {{i}} failed: {{response.status_code}}"
    assert isinstance(response.json(), list), f"Access {{i}} returned non-list: {{type(response.json())}}"

# Create an item
create_data = {{"accepted_invoice_number": "PERSIST_TEST"}}
response = client.post("/accepted_invoice_numbers", 
                     headers={{**headers, "Content-Type": "application/json"}}, 
                     json=create_data)
assert response.status_code == 201, f"Create failed: {{response.status_code}}"

# Multiple reads should return the same data
for i in range(3):
    response = client.get("/accepted_invoice_numbers", headers=headers)
    assert response.status_code == 200, f"Read {{i}} failed: {{response.status_code}}"
    items = response.json()
    assert len(items) == 1, f"Read {{i}} expected 1 item, got {{len(items)}}"
    assert items[0]["accepted_invoice_number"] == "PERSIST_TEST", f"Read {{i}} data mismatch"

print("SUCCESS: Database initialization is idempotent")
'''
        
        # Run the test script in a subprocess with uv run to ensure dependencies
        # Use the directory containing main.py as working directory
        main_py_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Try uv run first, fallback to python with explicit httpx install
        try:
            result = subprocess.run(
                ["uv", "run", "python", "-c", test_script], 
                cwd=main_py_dir,
                capture_output=True, 
                text=True
            )
        except FileNotFoundError:
            # Fallback: install httpx and run with python
            subprocess.run(["python", "-m", "pip", "install", "httpx"], 
                         cwd=main_py_dir, capture_output=True)
            result = subprocess.run(
                ["python", "-c", test_script], 
                cwd=main_py_dir,
                capture_output=True, 
                text=True
            )
        
        assert result.returncode == 0, f"Test failed with error: {result.stderr}"
        assert "SUCCESS: Database initialization is idempotent" in result.stdout