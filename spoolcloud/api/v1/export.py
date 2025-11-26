"""Functions for exporting data."""

import io
from collections.abc import Iterable
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from spoolcloud import auth
from spoolcloud.database import filament, spool, vendor
from spoolcloud.database.database import get_db_session
from spoolcloud.database.models import Base
from spoolcloud.export import dump_as_csv, dump_as_json

# ruff: noqa: D103,B008
router = APIRouter(
    prefix="/export",
    tags=["export (导出)"],
)


class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"


@router.get(
    "/spools",
    name="Export spools",
    description="Export the list of spools in various formats. Filament and vendor data is included.",
)
async def export_spools(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[Base, Depends(auth.get_current_user)],
    fmt: ExportFormat,
) -> Response:

    all_spools, _ = await spool.find(db=db, user_id=current_user.id)
    return await _export(all_spools, fmt)


@router.get(
    "/filaments",
    name="Export filaments",
    description="Export the list of filaments in various formats. Vendor data is included.",
)
async def export_filaments(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[Base, Depends(auth.get_current_user)],
    fmt: ExportFormat,
) -> Response:
    all_filaments, _ = await filament.find(db=db, user_id=current_user.id)
    return await _export(all_filaments, fmt)


@router.get(
    "/vendors",
    name="Export vendors",
    description="Export the list of vendors in various formats.",
)
async def export_vendors(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[Base, Depends(auth.get_current_user)],
    fmt: ExportFormat,
) -> Response:
    all_vendors, _ = await vendor.find(db=db, user_id=current_user.id)
    return await _export(all_vendors, fmt)


async def _export(objects: Iterable[Base], fmt: ExportFormat) -> Response:
    """Export the objects in various formats."""
    buffer = io.StringIO()
    media_type = ""

    if fmt == ExportFormat.CSV:
        media_type = "text/csv"
        await dump_as_csv(objects, buffer)
    elif fmt == ExportFormat.JSON:
        media_type = "application/json"
        await dump_as_json(objects, buffer)
    else:
        raise ValueError(f"Unknown export format: {fmt}")

    return Response(content=buffer.getvalue(), media_type=media_type)
