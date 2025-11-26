import time
import httpx
from tests_integration.tests.conftest import URL

def register_and_login(username_prefix):
    username = f"{username_prefix}_{int(time.time())}"
    password = "password123"
    httpx.post(f"{URL}/api/v1/auth/register", json={"username": username, "password": password})
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_vendor_isolation():
    """Test that vendors are isolated between users."""
    headers_a = register_and_login("user_a")
    headers_b = register_and_login("user_b")
    
    # User A creates vendor
    response = httpx.post(
        f"{URL}/api/v1/vendor",
        json={"name": "Vendor A"},
        headers=headers_a
    )
    assert response.status_code == 200
    vendor_a = response.json()
    
    # User B lists vendors (should be empty or not contain Vendor A)
    response = httpx.get(f"{URL}/api/v1/vendor", headers=headers_b)
    assert response.status_code == 200
    vendors_b = response.json()
    assert not any(v["id"] == vendor_a["id"] for v in vendors_b)
    
    # User B tries to get Vendor A (should be 404)
    response = httpx.get(f"{URL}/api/v1/vendor/{vendor_a['id']}", headers=headers_b)
    assert response.status_code == 404
    
    # User A can see Vendor A
    response = httpx.get(f"{URL}/api/v1/vendor/{vendor_a['id']}", headers=headers_a)
    assert response.status_code == 200
