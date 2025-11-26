"""Helper functions for interacting with filament preset database objects."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from spoolcloud.database import models, filament
from spoolcloud.exceptions import ItemDeleteError, ItemNotFoundError

logger = logging.getLogger(__name__)


async def create(
    *,
    db: AsyncSession,
    user_id: int,
    name: str,
    filament_ids: Optional[list[int]] = None,
) -> models.FilamentPreset:
    """Add a new filament preset to the database."""
    preset = models.FilamentPreset(
        user_id=user_id,
        name=name,
    )
    if filament_ids:
        for fid in filament_ids:
            f = await filament.get_by_id(db, fid, user_id)
            preset.filaments.append(f)

    db.add(preset)
    await db.commit()
    return preset


async def get_by_id(db: AsyncSession, preset_id: int, user_id: int) -> models.FilamentPreset:
    """Get a filament preset object from the database by the unique ID."""
    stmt = (
        select(models.FilamentPreset)
        .where(models.FilamentPreset.id == preset_id, models.FilamentPreset.user_id == user_id)
        .options(joinedload(models.FilamentPreset.filaments))
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
    await db.delete(preset)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ItemDeleteError("Failed to delete filament preset.") from exc
