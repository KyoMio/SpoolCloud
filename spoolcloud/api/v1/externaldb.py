"""External database API."""

import logging

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from spoolcloud import auth
from spoolcloud.api.v1 import models
from spoolcloud.externaldb import ExternalFilament, ExternalMaterial, get_filaments_file, get_materials_file

router = APIRouter(
    prefix="/external",
    tags=["externaldb (外部数据库)"],
)

# ruff: noqa: D103,B008

logger = logging.getLogger(__name__)


@router.get(
    "/filament",
    name="Get all external filaments",
    response_model_exclude_none=True,
    response_model=list[ExternalFilament],
)
async def filaments(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> FileResponse:
    """Get all external filaments."""
    return FileResponse(path=get_filaments_file(), media_type="application/json")


@router.get(
    "/material",
    name="Get all external materials",
    response_model_exclude_none=True,
    response_model=list[ExternalMaterial],
)
async def materials(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> FileResponse:
    """Get all external materials."""
    return FileResponse(path=get_materials_file(), media_type="application/json")
