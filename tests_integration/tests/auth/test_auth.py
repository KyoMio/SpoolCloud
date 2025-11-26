import time
import httpx
from tests_integration.tests.conftest import URL

def test_register_and_login():
    """Test user registration and login."""
    username = f"user_{int(time.time())}"
    password = "password123"
    
    # Register
    response = httpx.post(f"{URL}/api/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    
    # Login
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    
    # Get Me
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(f"{URL}/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == username

def test_change_password():
    """Test changing password."""
    username = f"user_pw_{int(time.time())}"
    password = "password123"
    new_password = "newpassword456"
    
    # Register
    httpx.post(f"{URL}/api/v1/auth/register", json={"username": username, "password": password})
    
    # Login
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": password})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Change Password
    response = httpx.post(
        f"{URL}/api/v1/auth/change-password",
        json={"old_password": password, "new_password": new_password},
        headers=headers
    )
    assert response.status_code == 200
    
    # Login with old password (should fail)
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 401
    
    # Login with new password (should succeed)
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": new_password})
    assert response.status_code == 200

def test_api_key():
    """Test API key creation and usage."""
    username = f"user_apikey_{int(time.time())}"
    password = "password123"
    
    # Register & Login
    httpx.post(f"{URL}/api/v1/auth/register", json={"username": username, "password": password})
    response = httpx.post(f"{URL}/api/v1/auth/token", data={"username": username, "password": password})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create API Key
    response = httpx.post(f"{URL}/api/v1/auth/api-key", json={"label": "Test Key"}, headers=headers)
    assert response.status_code == 200
    key_data = response.json()
    api_key = key_data["key"]
    
    # Use API Key to get Me
    api_key_headers = {"Authorization": f"Bearer {api_key}"}
    response = httpx.get(f"{URL}/api/v1/auth/me", headers=api_key_headers)
    assert response.status_code == 200
    assert response.json()["username"] == username
    
    # List API Keys
    response = httpx.get(f"{URL}/api/v1/auth/api-key", headers=headers)
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) >= 1
    assert keys[0]["label"] == "Test Key"
    
    # Delete API Key
    key_id = keys[0]["id"]
    response = httpx.delete(f"{URL}/api/v1/auth/api-key/{key_id}", headers=headers)
    assert response.status_code == 204
    
    # Use Deleted API Key (should fail)
    response = httpx.get(f"{URL}/api/v1/auth/me", headers=api_key_headers)
    assert response.status_code == 401
