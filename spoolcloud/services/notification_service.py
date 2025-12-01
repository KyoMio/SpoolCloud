"""Notification service for sending notifications through various channels."""
import json
import logging
import asyncio
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through different channels."""
    
    _lock = asyncio.Lock()
    _last_sent_time = 0.0

    @staticmethod
    async def send_notification(
        db: "AsyncSession",
        user_id: int,
        type: str,
        title: str,
        message: str,
    ) -> tuple[bool, str]:
        """Send a notification to the user's configured channel if enabled."""
        async with NotificationService._lock:
            current_time = time.time()
            time_diff = current_time - NotificationService._last_sent_time
            if time_diff < 0.5:
                await asyncio.sleep(0.5 - time_diff)
            
            NotificationService._last_sent_time = time.time()

            from spoolcloud.database import notification
            
            config = await notification.get_config(db, user_id)
            if not config or not config.is_enabled:
                return False, "Notifications disabled or not configured."
                
            # Check if type is enabled
            # If notification_types is None or empty, we assume all are enabled (or none? Plan said default to all)
            # But in the model we didn't set a default. Let's assume if it's None, all are enabled for backward compatibility.
            # If it's a list, check if type is in it.
            if config.notification_types is not None:
                 # If it's a list (JSON decoded), check if type is in it
                if isinstance(config.notification_types, list) and type not in config.notification_types:
                    return False, f"Notification type '{type}' is disabled."
            
            # Parse config_data
            import json
            config_data = {}
            if config.config_data:
                try:
                    config_data = json.loads(config.config_data)
                except json.JSONDecodeError:
                    pass
                    
            if config.channel == "serverchan":
                return await NotificationService._send_serverchan(config.webhook_url, title, message)
            elif config.channel == "bark":
                return await NotificationService._send_bark(config_data, title, message)
            elif config.channel == "synochat":
                return await NotificationService._send_synochat(config.webhook_url, title, message)
            elif config.channel == "email":
                return await NotificationService._send_email(config_data, title, message)
            elif config.channel == "webhook":
                return await NotificationService._send_webhook(config.webhook_url, config_data, title, message)
            else:
                return False, f"Unsupported channel: {config.channel}"

    @staticmethod
    async def send_test_notification(
        channel: str,
        webhook_url: Optional[str],
        config_data: Optional[Dict[str, Any]],
    ) -> tuple[bool, str]:
        """Send a test notification.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        test_title = "SpoolCloud Test"
        test_message = "This is a test notification from SpoolCloud."
        
        try:
            if channel == "serverchan":
                # For ServerChan, webhook_url is actually the API Key now
                return await NotificationService._send_serverchan(webhook_url, test_title, test_message)
            elif channel == "bark":
                return await NotificationService._send_bark(config_data or {}, test_title, test_message)
            elif channel == "synochat":
                return await NotificationService._send_synochat(webhook_url, test_title, test_message)
            elif channel == "email":
                return await NotificationService._send_email(config_data or {}, test_title, test_message)
            elif channel == "webhook":
                return await NotificationService._send_webhook(webhook_url, config_data or {}, test_title, test_message)
            else:
                return False, f"Unsupported channel: {channel}"
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return False, f"Error: {str(e)}"
    
    @staticmethod
    async def _send_serverchan(api_key: Optional[str], title: str, message: str) -> tuple[bool, str]:
        """Send notification via Server酱."""
        if not api_key:
            return False, "API Key is required for ServerChan"
        
        try:
            url = f"https://sctapi.ftqq.com/{api_key}.send"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data={"title": title, "desp": message},
                    timeout=10.0,
                )
                # ServerChan returns JSON with code=0 for success
                try:
                    result = response.json()
                    if result.get("code") == 0:
                        return True, "Notification sent successfully via ServerChan"
                    else:
                        return False, f"ServerChan error: {result.get('message', 'Unknown error')}"
                except Exception:
                    if response.status_code == 200:
                        return True, "Notification sent successfully via ServerChan"
                    return False, f"ServerChan returned status code {response.status_code}"
        except Exception as e:
            return False, f"ServerChan error: {str(e)}"
    
    @staticmethod
    async def _send_bark(config: Dict[str, Any], title: str, message: str) -> tuple[bool, str]:
        """Send notification via Bark."""
        base_url = config.get("base_url", "").rstrip("/")
        device_key = config.get("device_key", "")
        
        if not base_url or not device_key:
            return False, "Base URL and Device Key are required for Bark"
        
        try:
            # Bark URL format: base_url/device_key/title/message
            # Ensure proper encoding of title and message
            import urllib.parse
            encoded_title = urllib.parse.quote(title)
            encoded_message = urllib.parse.quote(message)
            
            url = f"{base_url}/{device_key}/{encoded_title}/{encoded_message}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    return True, "Notification sent successfully via Bark"
                else:
                    return False, f"Bark returned status code {response.status_code}"
        except Exception as e:
            return False, f"Bark error: {str(e)}"
    
    @staticmethod
    async def _send_synochat(webhook_url: Optional[str], title: str, message: str) -> tuple[bool, str]:
        """Send notification via Synology Chat."""
        if not webhook_url:
            return False, "Webhook URL is required for SynoChat"
        
        try:
            # Synology Chat expects payload parameter as JSON string in form data
            payload = {
                "text": f"**{title}**\n\n{message}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    data={"payload": json.dumps(payload)},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return True, "Notification sent successfully via SynoChat"
                else:
                    return False, f"SynoChat returned status code {response.status_code}"
        except Exception as e:
            return False, f"SynoChat error: {str(e)}"
    
    @staticmethod
    async def _send_email(config: Dict[str, Any], title: str, message: str) -> tuple[bool, str]:
        """Send notification via Email."""
        smtp_server = config.get("smtp_server", "")
        smtp_port = config.get("smtp_port", 587)
        email_from = config.get("email", "")
        password = config.get("password", "")
        email_to = config.get("email_to", email_from)
        
        if not all([smtp_server, email_from, password]):
            return False, "SMTP server, email, and password are required for Email notifications"
        
        try:
            msg = MIMEMultipart()
            msg['From'] = email_from
            msg['To'] = email_to
            msg['Subject'] = title
            
            body = MIMEText(message, 'plain')
            msg.attach(body)
            
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls()
                server.login(email_from, password)
                server.send_message(msg)
            
            return True, "Notification sent successfully via Email"
        except Exception as e:
            return False, f"Email error: {str(e)}"
    
    @staticmethod
    async def _send_webhook(webhook_url: Optional[str], config: Dict[str, Any], title: str, message: str) -> tuple[bool, str]:
        """Send notification via generic Webhook."""
        if not webhook_url:
            return False, "Webhook URL is required"
        
        try:
            headers = config.get("headers", {})
            if isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except json.JSONDecodeError:
                    headers = {}
            
            payload = {
                "title": title,
                "message": message,
                "timestamp": None  # Could add timestamp
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code in [200, 201, 204]:
                    return True, "Notification sent successfully via Webhook"
                else:
                    return False, f"Webhook returned status code {response.status_code}"
        except Exception as e:
            return False, f"Webhook error: {str(e)}"
