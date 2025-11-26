import httpx
from tests_integration.tests.conftest import URL
from tests_integration.tests.auth.test_multi_user import register_and_login

def test_notification_config():
    """Test notification configuration endpoints."""
    headers = register_and_login("user_notif")
    
    # Get config
    response = httpx.get(f"{URL}/api/v1/notification/config", headers=headers)
    assert response.status_code == 200
    config = response.json()
    assert config["is_enabled"] is True
    assert config["channel"] == "serverchan"
    
    # Update config
    response = httpx.put(
        f"{URL}/api/v1/notification/config",
        json={"is_enabled": False, "channel": "bark", "webhook_url": "http://example.com"},
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify update
    response = httpx.get(f"{URL}/api/v1/notification/config", headers=headers)
    assert response.status_code == 200
    config = response.json()
    assert config["is_enabled"] is False
    assert config["channel"] == "bark"
    assert config["webhook_url"] == "http://example.com"

def test_internal_notifications():
    """Test internal notification endpoints."""
    headers = register_and_login("user_internal_notif")
    
    # List notifications (empty)
    response = httpx.get(f"{URL}/api/v1/notification", headers=headers)
    assert response.status_code == 200
    notifications = response.json()
    assert isinstance(notifications, list)
    assert len(notifications) == 0
