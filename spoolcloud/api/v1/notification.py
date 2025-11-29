"""Notification related endpoints."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spoolcloud import auth
from spoolcloud.api.v1.models import InternalNotification, Message, NotificationConfig
from spoolcloud.database import models, notification
from spoolcloud.database.database import get_db_session
from spoolcloud.exceptions import ItemNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notification",
    tags=["notification (通知)"],
)


class NotificationConfigParameters(BaseModel):
    channel: Optional[str] = Field(None, description="Notification channel (serverchan, bark, synochat, email, webhook).")
    webhook_url: Optional[str] = Field(None, description="Webhook URL (for channels that use webhooks).")
    config_data: Optional[dict] = Field(None, description="Channel-specific configuration data.")
    is_enabled: bool = Field(default=False, description="Whether notifications are enabled.")
    notification_types: Optional[list[str]] = Field(
        None, 
        description="List of enabled notification types (system, deduction, low_supply). If None, all are enabled."
    )
    language: str = Field(default="zh-CN", description="Notification language (zh-CN, en-US).")


@router.get(
    "/config",
    name="Get notification config",
    description="Get notification configuration for the current user.",
    response_model=Optional[NotificationConfig],
)
async def get_config(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> Optional[NotificationConfig]:
    db_item = await notification.get_config(db, current_user.id)
    if db_item:
        return NotificationConfig.from_db(db_item)
    # Return default config
    return NotificationConfig(
        id=-1,  # Dummy ID
        channel="serverchan",
        webhook_url="",
        is_enabled=False,
        notification_types=["system", "deduction", "low_supply"], # Default to all enabled
        language="zh-CN",
    )


@router.put(
    "/config",
    name="Update notification config",
    description="Update notification configuration for the current user.",
    response_model=NotificationConfig,
)
async def update_config(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    body: NotificationConfigParameters,
) -> NotificationConfig:
    import json
    config_data_str = None
    if body.config_data:
        config_data_str = json.dumps(body.config_data)
    
    db_item = await notification.update_config(
        db=db,
        user_id=current_user.id,
        channel=body.channel,
        webhook_url=body.webhook_url,
        config_data=config_data_str,
        is_enabled=body.is_enabled,
        notification_types=body.notification_types,
        language=body.language,
    )
    return NotificationConfig.from_db(db_item)


@router.get(
    "",
    name="List notifications",
    description="Get a list of internal notifications.",
    response_model=list[InternalNotification],
)
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    unread_only: bool = Query(False, description="Only return unread notifications."),
    limit: int = Query(50, description="Maximum number of notifications to return."),
    offset: int = Query(0, description="Offset for pagination."),
) -> list[InternalNotification]:
    db_items, _ = await notification.get_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )
    return [InternalNotification.from_db(item) for item in db_items]


@router.put(
    "/{notification_id}/read",
    name="Mark notification as read",
    description="Mark a notification as read.",
    response_model=InternalNotification,
)
async def mark_as_read(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    notification_id: int,
) -> InternalNotification:
    try:
        db_item = await notification.mark_as_read(db, notification_id, current_user.id)
        return InternalNotification.from_db(db_item)
    except ItemNotFoundError:
        return JSONResponse(status_code=404, content={"message": "Notification not found."})


@router.put(
    "/read-all",
    name="Mark all notifications as read",
    description="Mark all notifications as read for the current user.",
    response_model=Message,
)
async def mark_all_as_read(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> Message:
    await notification.mark_all_as_read(db, current_user.id)
    return Message(message="Success!")


@router.delete(
    "/{notification_id}",
    name="Delete notification",
    description="Delete a notification.",
    response_model=Message,
)
async def delete_notification(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    notification_id: int,
) -> Message:
    await notification.delete_notification(db, notification_id, current_user.id)
    return Message(message="Success!")


@router.delete(
    "",
    name="Clear all notifications",
    description="Delete all notifications for the current user.",
    response_model=Message,
)
async def clear_all_notifications(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> Message:
    await notification.clear_all_notifications(db, current_user.id)
    return Message(message="Success!")


@router.post(
    "/test",
    name="Test notification",
    description="Send a test notification using current configuration.",
    response_model=Message,
)
async def test_notification(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> Message:
    from spoolcloud.services.notification_service import NotificationService
    
    # Get user's notification config
    db_config = await notification.get_config(db, current_user.id)
    if not db_config:
        return JSONResponse(
            status_code=400,
            content={"message": "No notification configuration found. Please configure notifications first."}
        )
    
    if not db_config.is_enabled:
        return JSONResponse(
            status_code=400,
            content={"message": "Notifications are disabled. Please enable notifications first."}
        )
    
    # Parse config_data
    import json
    config_data = None
    if db_config.config_data:
        try:
            config_data = json.loads(db_config.config_data)
        except json.JSONDecodeError:
            config_data = {}
    
    # Send test notification
    success, message = await NotificationService.send_test_notification(
        channel=db_config.channel,
        webhook_url=db_config.webhook_url,
        config_data=config_data,
    )
    
    if success:
        return Message(message=message)
    else:
        return JSONResponse(
            status_code=400,
            content={"message": message}
        )

