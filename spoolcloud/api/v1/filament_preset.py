"""Filament preset related endpoints."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spoolcloud import auth
from spoolcloud.api.v1.models import FilamentPreset, Message
from spoolcloud.database import filament_preset, models
from spoolcloud.database.database import get_db_session
from spoolcloud.exceptions import ItemDeleteError, ItemNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/filament-preset",
    tags=["filament-preset (耗材预设)"],
)


class FilamentPresetParameters(BaseModel):
    name: str = Field(max_length=64, description="Preset name.")
    code: Optional[str] = Field(None, max_length=32, description="Preset code.")
    filament_ids: Optional[list[int]] = Field(None, description="List of filament IDs in this preset.")


@router.get(
    "",
    name="List filament presets",
    description="Get a list of all filament presets for the current user.",
    response_model=list[FilamentPreset],
)
async def find(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> list[FilamentPreset]:
    db_items = await filament_preset.find(db=db, user_id=current_user.id)
    return [FilamentPreset.from_db(item) for item in db_items]


@router.get(
    "/{preset_id}",
    name="Get filament preset",
    description="Get a specific filament preset.",
    response_model=FilamentPreset,
    responses={404: {"model": Message}},
)
async def get(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    preset_id: int,
) -> FilamentPreset:
    db_item = await filament_preset.get_by_id(db, preset_id, current_user.id)
    return FilamentPreset.from_db(db_item)


class FilamentPresetBatchParameters(BaseModel):
    name: str = Field(max_length=64, description="Preset name.")
    code: Optional[str] = Field(None, max_length=32, description="Preset code.")


@router.post(
    "/batch",
    name="Batch create filament presets",
    description="Create multiple filament presets at once.",
    response_model=list[FilamentPreset],
)
async def create_batch(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    body: list[FilamentPresetBatchParameters],
) -> list[FilamentPreset]:
    created_presets = []
    for item in body:
        db_item = await filament_preset.create(
            db=db,
            user_id=current_user.id,
            name=item.name,
            code=item.code,
            filament_ids=None,
        )
        # We know filaments is empty because we passed filament_ids=None
        # Manually construct the response to avoid potential lazy load issues
        created_presets.append(FilamentPreset(
            id=db_item.id,
            name=db_item.name,
            code=db_item.code,
            filaments=[],
        ))
    return created_presets


@router.post(
    "",
    name="Create filament preset",
    description="Create a new filament preset.",
    response_model=FilamentPreset,
)
async def create(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    body: FilamentPresetParameters,
) -> FilamentPreset:
    db_item = await filament_preset.create(
        db=db,
        user_id=current_user.id,
        name=body.name,
        code=body.code,
        filament_ids=body.filament_ids,
    )
    return FilamentPreset.from_db(db_item)


@router.patch(
    "/{preset_id}",
    name="Update filament preset",
    description="Update a filament preset.",
    response_model=FilamentPreset,
    responses={404: {"model": Message}},
)
async def update(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    preset_id: int,
    body: FilamentPresetParameters,
) -> FilamentPreset:
    data = body.model_dump(exclude_unset=True)
    db_item = await filament_preset.update(
        db=db,
        preset_id=preset_id,
        user_id=current_user.id,
        data=data,
    )
    return FilamentPreset.from_db(db_item)


@router.delete(
    "/{preset_id}",
    name="Delete filament preset",
    description="Delete a filament preset.",
    response_model=Message,
    responses={404: {"model": Message}},
)
async def delete(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    preset_id: int,
) -> Message:
    try:
        await filament_preset.delete(db, preset_id, current_user.id)
    except ItemDeleteError:
        logger.exception("Failed to delete filament preset.")
        return JSONResponse(
            status_code=403,
            content={"message": "Failed to delete filament preset."},
        )
    return Message(message="Success!")


class FilamentPresetReplaceParameters(BaseModel):
    new_preset_id: int = Field(description="The ID of the new filament preset to use.")


@router.post(
    "/{preset_id}/replace",
    name="Replace and delete filament preset",
    description="Replace a filament preset with another one for all filaments, then delete the old one.",
    response_model=Message,
    responses={
        403: {"model": Message},
        404: {"model": Message},
    },
)
async def replace_and_delete(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    preset_id: int,
    body: FilamentPresetReplaceParameters,
) -> Message:
    try:
        await filament_preset.replace_and_delete(
            db=db,
            old_preset_id=preset_id,
            new_preset_id=body.new_preset_id,
            user_id=current_user.id,
        )
    except ItemNotFoundError as exc:
        return JSONResponse(
            status_code=404,
            content={"message": str(exc)},
        )
    except ItemDeleteError:
        logger.exception("Failed to replace and delete filament preset.")
        return JSONResponse(
            status_code=403,
            content={"message": "Failed to replace and delete filament preset."},
        )
    return Message(message="Success!")
