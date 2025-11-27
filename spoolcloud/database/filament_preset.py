"""Helper functions for interacting with filament preset database objects."""

import logging
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy import update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from spoolcloud.database import models, filament, notification
from spoolcloud.database.models import NotificationType
from spoolcloud.exceptions import ItemDeleteError, ItemNotFoundError

logger = logging.getLogger(__name__)


async def create(
    *,
    db: AsyncSession,
    user_id: int,
    name: str,
    code: Optional[str] = None,
    filament_ids: Optional[list[int]] = None,
) -> models.FilamentPreset:
    """Add a new filament preset to the database."""
    preset = models.FilamentPreset(
        user_id=user_id,
        name=name,
        code=code,
    )
    if filament_ids:
        for fid in filament_ids:
            f = await filament.get_by_id(db, fid, user_id)
            preset.filaments.append(f)

    db.add(preset)
    await db.commit()
    
    return await get_by_id(db, preset.id, user_id)


async def get_by_id(db: AsyncSession, preset_id: int, user_id: int) -> models.FilamentPreset:
    """Get a filament preset object from the database by the unique ID."""
    stmt = (
        select(models.FilamentPreset)
        .where(models.FilamentPreset.id == preset_id, models.FilamentPreset.user_id == user_id)
        .options(
            selectinload(models.FilamentPreset.filaments).options(
                joinedload(models.Filament.vendor).options(
                    joinedload(models.Vendor.extra)
                ),
                selectinload(models.Filament.extra),
            )
        )
    )
    result = await db.execute(stmt)
    preset = result.unique().scalars().first()
    if preset is None:
        raise ItemNotFoundError(f"No filament preset with ID {preset_id} found.")
    return preset


async def find(
    *,
    db: AsyncSession,
    user_id: int,
) -> list[models.FilamentPreset]:
    """Find a list of filament preset objects for a user."""
    stmt = (
        select(models.FilamentPreset)
        .where(models.FilamentPreset.user_id == user_id)
        .options(joinedload(models.FilamentPreset.filaments))
    )
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


async def update(
    *,
    db: AsyncSession,
    preset_id: int,
    user_id: int,
    data: dict,
) -> models.FilamentPreset:
    """Update the fields of a filament preset object."""
    preset = await get_by_id(db, preset_id, user_id)
    for k, v in data.items():
        if k == "filament_ids":
            preset.filaments = []
            for fid in v:
                f = await filament.get_by_id(db, fid, user_id)
                preset.filaments.append(f)
        else:
            setattr(preset, k, v)
    await db.commit()
    return preset


async def delete(db: AsyncSession, preset_id: int, user_id: int) -> None:
    """Delete a filament preset object."""
    preset = await get_by_id(db, preset_id, user_id)
    
    # Check if preset is in use
    if preset.filaments:
        logger.info(f"Preset {preset_id} is in use by {len(preset.filaments)} filaments. Checking for existing notification.")
        
        # Check if a notification already exists for this preset
        existing_notification = await notification.find_notification_by_preset(
            db=db,
            user_id=user_id,
            preset_id=preset_id,
        )
        
        if not existing_notification:
            logger.info(f"Creating new conflict notification for preset {preset_id}")
            await notification.create_notification(
                db=db,
                user_id=user_id,
                title="Filament Preset Conflict",
                message=f"The filament preset '{preset.name}' cannot be deleted because it is in use by {len(preset.filaments)} filaments. Please replace the preset for these filaments.",
                type=NotificationType.WARNING,
                data={"preset_id": preset_id, "action": "replace_preset"},
            )
        else:
            logger.info(f"Notification already exists for preset {preset_id}, skipping duplicate")
        
        # Do not delete the preset
        return

    await db.delete(preset)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ItemDeleteError("Failed to delete filament preset.") from exc


async def replace_and_delete(
    db: AsyncSession,
    old_preset_id: int,
    new_preset_id: int,
    user_id: int,
) -> None:
    """Replace a filament preset with another one for all filaments, then delete the old one."""
    logger.info(f"Replacing preset {old_preset_id} with {new_preset_id}")
    
    # Verify new preset exists
    try:
        new_preset = await get_by_id(db, new_preset_id, user_id)
    except ItemNotFoundError:
        logger.error(f"New preset {new_preset_id} not found")
        raise ItemNotFoundError(f"Target preset (ID: {new_preset_id}) not found. It may have been deleted.")

    # Get old preset to verify ownership and existence
    try:
        old_preset = await get_by_id(db, old_preset_id, user_id)
    except ItemNotFoundError:
        logger.error(f"Old preset {old_preset_id} not found")
        raise ItemNotFoundError(f"Source preset (ID: {old_preset_id}) not found. It may have already been deleted.")
    
    logger.info(f"Old preset '{old_preset.name}' has {len(old_preset.filaments)} filaments")
    
    # Update all filaments that use the old preset
    stmt = (
        sql_update(models.Filament)
        .where(models.Filament.preset_id == old_preset_id, models.Filament.user_id == user_id)
        .values(preset_id=new_preset_id)
    )
    result = await db.execute(stmt)
    logger.info(f"Updated {result.rowcount} filaments from preset '{old_preset.name}' to '{new_preset.name}'")
    
    # Expire all objects to force refresh from DB
    db.expire_all()
    
    # Delete the old preset
    await db.delete(old_preset)
    
    try:
        await db.commit()
        logger.info(f"Successfully replaced preset {old_preset_id} with {new_preset_id}")
    except IntegrityError as exc:
        await db.rollback()
        raise ItemDeleteError("Failed to replace and delete filament preset.") from exc

