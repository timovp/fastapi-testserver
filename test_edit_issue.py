#!/usr/bin/env python3
"""
Test script to reproduce the edit functionality issue.
This will help us confirm the problem before fixing it.
"""

import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "secret123"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY
}

def test_edit_functionality():
    print("Testing edit functionality...")
    
    # First, create an invoice
    print("\n1. Creating an invoice...")
    create_response = requests.post(
        f"{BASE_URL}/accepted_invoice_numbers",
        headers=HEADERS,
        json={"accepted_invoice_number": "TEST-001"}
    )
    print(f"Create response: {create_response.status_code} - {create_response.json()}")
    
    if create_response.status_code != 201:
        print("Failed to create invoice!")
        return
    
    invoice_data = create_response.json()
    invoice_id = invoice_data["id"]
    
    # Now try to edit it using the same logic as the frontend
    print(f"\n2. Attempting to edit invoice {invoice_id}...")
    
    # This is the problematic URL construction from the frontend
    type_name = "invoice"
    # Original buggy logic from frontend:
    # const url = `${base}/accepted_${type}_names/${id}`.replace(/_names/, type + (type==="invoice"? "_numbers": "_names"));
    
    # Let's simulate this logic
    buggy_url = f"{BASE_URL}/accepted_{type_name}_names/{invoice_id}"
    replacement = type_name + ("_numbers" if type_name == "invoice" else "_names")
    buggy_url = buggy_url.replace("_names", replacement)
    
    print(f"Buggy URL constructed: {buggy_url}")
    
    # Try the buggy URL
    edit_response = requests.put(
        f"{buggy_url}?invoice_number=TEST-001-EDITED",
        headers=HEADERS
    )
    print(f"Edit response (buggy): {edit_response.status_code}")
    if edit_response.status_code != 200:
        print(f"Edit failed as expected: {edit_response.text}")
    
    # Now try the correct URL
    print(f"\n3. Trying with correct URL...")
    correct_url = f"{BASE_URL}/accepted_invoice_numbers/{invoice_id}"
    print(f"Correct URL: {correct_url}")
    
    correct_edit_response = requests.put(
        f"{correct_url}?invoice_number=TEST-001-CORRECTED",
        headers=HEADERS
    )
    print(f"Edit response (correct): {correct_edit_response.status_code} - {correct_edit_response.json() if correct_edit_response.status_code == 200 else correct_edit_response.text}")
    
    # Test vendor edit as well
    print(f"\n4. Testing vendor edit...")
    
    # Create a vendor
    vendor_create_response = requests.post(
        f"{BASE_URL}/accepted_vendor_names",
        headers=HEADERS,
        json={"accepted_vendor_name": "TestVendor"}
    )
    print(f"Vendor create response: {vendor_create_response.status_code} - {vendor_create_response.json()}")
    
    if vendor_create_response.status_code == 201:
        vendor_data = vendor_create_response.json()
        vendor_id = vendor_data["id"]
        
        # Test buggy vendor URL
        vendor_type = "vendor"
        vendor_buggy_url = f"{BASE_URL}/accepted_{vendor_type}_names/{vendor_id}"
        vendor_replacement = vendor_type + ("_numbers" if vendor_type == "invoice" else "_names")
        vendor_buggy_url = vendor_buggy_url.replace("_names", vendor_replacement)
        
        print(f"Vendor buggy URL: {vendor_buggy_url}")
        
        vendor_edit_response = requests.put(
            f"{vendor_buggy_url}?vendor_name=TestVendor-EDITED",
            headers=HEADERS
        )
        print(f"Vendor edit response (should work): {vendor_edit_response.status_code}")
        if vendor_edit_response.status_code == 200:
            print(f"Vendor edit succeeded: {vendor_edit_response.json()}")
        else:
            print(f"Vendor edit failed: {vendor_edit_response.text}")

if __name__ == "__main__":
    test_edit_functionality()