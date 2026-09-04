import requests
import json
import sys

# force utf-8 for print
sys.stdout.reconfigure(encoding='utf-8')

def test_add_medication():
    # 1. Login to get token
    login_url = "http://localhost:8000/api/v1/auth/login/"
    login_data = {
        "email": "admin@securemed.app",
        "password": "SecurePassword123!"
    }
    print("Logging in...")
    resp = requests.post(login_url, json=login_data)
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} - {resp.text}")
        return

    tokens = resp.json()
    access = tokens.get('access')
    
    # 2. Add Medication
    headers = {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/json"
    }
    med_url = "http://localhost:8000/api/v1/pharmacy/medications/"
    med_data = {
        "name": "Panadol Test",
        "scientific_name": "Paracetamol",
        "barcode": "123456789",
        "stock_quantity": 100,
        "reorder_level": 20,
        "unit_price": 5.50
    }
    print("Adding medication...")
    resp = requests.post(med_url, headers=headers, json=med_data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == '__main__':
    test_add_medication()
