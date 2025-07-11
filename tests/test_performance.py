# tests/test_performance.py
import os
import tempfile
import pytest
import concurrent.futures
import time
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


class TestPerformanceAndConcurrency:
    """Test performance and concurrency aspects"""

    def test_concurrent_reads(self, client, auth_headers):
        """Test that concurrent read operations work correctly"""
        # First, create some test data
        for i in range(5):
            client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": f"INV{i:03d}"}
            )
        
        def make_read_request():
            return client.get("/accepted_invoice_numbers", headers=auth_headers)
        
        # Make multiple concurrent read requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_read_request) for _ in range(20)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5
            # All should return the same data
            invoice_numbers = [item["accepted_invoice_number"] for item in data]
            assert sorted(invoice_numbers) == [f"INV{i:03d}" for i in range(5)]

    def test_concurrent_writes_different_tables(self, client, auth_headers):
        """Test concurrent writes to different tables"""
        def create_invoice(invoice_num):
            return client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": f"INV{invoice_num}"}
            )
        
        def create_vendor(vendor_num):
            return client.post(
                "/accepted_vendor_names",
                headers=auth_headers,
                json={"accepted_vendor_name": f"Vendor{vendor_num}"}
            )
        
        # Mix of invoice and vendor creation requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            invoice_futures = [executor.submit(create_invoice, i) for i in range(5)]
            vendor_futures = [executor.submit(create_vendor, i) for i in range(5)]
            
            all_futures = invoice_futures + vendor_futures
            responses = [future.result() for future in all_futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 201
        
        # Verify all data was created
        invoice_response = client.get("/accepted_invoice_numbers", headers=auth_headers)
        vendor_response = client.get("/accepted_vendor_names", headers=auth_headers)
        
        assert len(invoice_response.json()) == 5
        assert len(vendor_response.json()) == 5

    def test_rapid_sequential_requests(self, client, auth_headers):
        """Test rapid sequential requests to same endpoint"""
        # Create many items in rapid succession
        start_time = time.time()
        
        for i in range(50):
            response = client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": f"RAPID{i:03d}"}
            )
            assert response.status_code == 201
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 10.0  # 50 requests in under 10 seconds
        
        # Verify all items were created
        response = client.get("/accepted_invoice_numbers", headers=auth_headers)
        assert len(response.json()) == 50

    def test_large_response_handling(self, client, auth_headers):
        """Test handling of large response data"""
        # Create many items
        for i in range(100):
            client.post(
                "/accepted_vendor_names",
                headers=auth_headers,
                json={"accepted_vendor_name": f"LargeTestVendor{i:03d}"}
            )
        
        # Request all items
        response = client.get("/accepted_vendor_names", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 100
        
        # Verify data integrity
        vendor_names = [item["accepted_vendor_name"] for item in data]
        expected_names = [f"LargeTestVendor{i:03d}" for i in range(100)]
        assert sorted(vendor_names) == sorted(expected_names)

    def test_mixed_operations_stress(self, client, auth_headers):
        """Test mix of CRUD operations under load"""
        # First create some base data
        created_ids = []
        for i in range(10):
            response = client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": f"STRESS{i:03d}"}
            )
            created_ids.append(response.json()["id"])
        
        def mixed_operations():
            results = []
            
            # Create
            response = client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": "THREAD_CREATE"}
            )
            results.append(response.status_code)
            
            # Read
            response = client.get("/accepted_invoice_numbers", headers=auth_headers)
            results.append(response.status_code)
            
            # Update (if we have IDs)
            if created_ids:
                response = client.put(
                    f"/accepted_invoice_numbers/{created_ids[0]}",
                    headers=auth_headers,
                    params={"invoice_number": "THREAD_UPDATE"}
                )
                results.append(response.status_code)
            
            return results
        
        # Run mixed operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mixed_operations) for _ in range(10)]
            all_results = [future.result() for future in futures]
        
        # Most operations should succeed (some updates might conflict)
        success_count = 0
        for results in all_results:
            success_count += sum(1 for status in results if status in [200, 201])
        
        # At least 80% of operations should succeed
        total_operations = sum(len(results) for results in all_results)
        assert success_count >= total_operations * 0.8

    def test_health_check_under_load(self, client):
        """Test that health check remains responsive under load"""
        def health_check():
            return client.get("/healthz")
        
        # Make many concurrent health check requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(health_check) for _ in range(100)]
            responses = [future.result() for future in futures]
        
        # All health checks should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_static_file_performance(self, client):
        """Test static file serving performance"""
        def get_index():
            return client.get("/")
        
        start_time = time.time()
        
        # Make many requests to static file
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_index) for _ in range(50)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
        
        # Should complete within reasonable time
        assert duration < 5.0  # 50 requests in under 5 seconds

    def test_lookup_performance_with_many_items(self, client, auth_headers):
        """Test lookup performance with many items in database"""
        # Create many vendors with similar names
        for i in range(100):
            client.post(
                "/accepted_vendor_names",
                headers=auth_headers,
                json={"accepted_vendor_name": f"PerfTestVendor{i:03d}"}
            )
        
        # Create one with a unique name for testing
        client.post(
            "/accepted_vendor_names",
            headers=auth_headers,
            json={"accepted_vendor_name": "UniqueVendorForLookup"}
        )
        
        # Test lookup performance
        start_time = time.time()
        
        response = client.get(
            "/vendor_name_lookup",
            headers=auth_headers,
            params={"vendor_name": "UniqueVendorForLookup"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        # Lookup should be reasonably fast even with many items
        assert duration < 1.0  # Should complete in under 1 second

    def test_authentication_performance(self, client):
        """Test authentication performance under load"""
        headers = {"X-API-KEY": "testkey123"}
        
        def authenticated_request():
            return client.get("/accepted_invoice_numbers", headers=headers)
        
        start_time = time.time()
        
        # Make many authenticated requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(authenticated_request) for _ in range(100)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Should complete within reasonable time
        assert duration < 10.0  # 100 requests in under 10 seconds

    def test_memory_usage_with_large_strings(self, client, auth_headers):
        """Test handling of large string values"""
        # Create items with large string values
        large_string = "A" * 10000  # 10KB string
        
        for i in range(10):
            response = client.post(
                "/accepted_invoice_numbers",
                headers=auth_headers,
                json={"accepted_invoice_number": f"{large_string}_{i}"}
            )
            assert response.status_code == 201
        
        # Retrieve and verify
        response = client.get("/accepted_invoice_numbers", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 10
        
        for item in data:
            assert len(item["accepted_invoice_number"]) > 10000