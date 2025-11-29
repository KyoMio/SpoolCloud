"""Spool related endpoints."""

import asyncio
import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from spoolcloud import auth
from spoolcloud.api.v1.models import Message, Spool, SpoolEvent
from spoolcloud.database import models, spool
from spoolcloud.database.database import get_db_session
from spoolcloud.database.utils import SortOrder
from spoolcloud.exceptions import ItemCreateError, SpoolMeasureError
from spoolcloud.extra_fields import EntityType, get_extra_fields, validate_extra_field_dict
from spoolcloud.ws import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/spool",
    tags=["spool (线轴)"],
)


class SpoolParameters(BaseModel):
    first_used: Optional[datetime] = Field(None, description="First logged occurence of spool usage.")
    last_used: Optional[datetime] = Field(None, description="Last logged occurence of spool usage.")
    filament_id: int = Field(description="The ID of the filament type of this spool.")
    price: Optional[float] = Field(
        None,
        ge=0,
        description="The price of this filament in the system configured currency.",
        examples=[20.0],
    )
    initial_weight: Optional[float] = Field(
        None,
        ge=0,
        description="The initial weight of the filament on the spool, in grams. (net weight)",
        examples=[200],
    )
    spool_weight: Optional[float] = Field(
        None,
        ge=0,
        description="The weight of an empty spool, in grams. (tare weight)",
        examples=[200],
    )
    remaining_weight: Optional[float] = Field(
        None,
        ge=0,
        description=(
            "Remaining weight of filament on the spool. Can only be used if the filament type has a weight set."
        ),
        examples=[800],
    )
    used_weight: Optional[float] = Field(
        None,
        ge=0,
        description="Used weight of filament on the spool.",
        examples=[200],
    )
    location: Optional[str] = Field(
        None,
        max_length=64,
        description="Where this spool can be found.",
        examples=["Shelf A"],
    )
    lot_nr: Optional[str] = Field(
        None,
        max_length=64,
        description="Vendor manufacturing lot/batch number of the spool.",
        examples=["52342"],
    )
    comment: Optional[str] = Field(
        None,
        max_length=1024,
        description="Free text comment about this specific spool.",
        examples=[""],
    )
    archived: bool = Field(default=False, description="Whether this spool is archived and should not be used anymore.")
    extra: Optional[dict[str, str]] = Field(
        None,
        description="Extra fields for this spool.",
    )


class SpoolUpdateParameters(SpoolParameters):
    filament_id: Optional[int] = Field(None, description="The ID of the filament type of this spool.")

    @field_validator("filament_id")
    @classmethod
    def prevent_none(cls: type["SpoolUpdateParameters"], v: Optional[int]) -> Optional[int]:
        """Prevent filament_id from being None."""
        if v is None:
            raise ValueError("Value must not be None.")
        return v


class SpoolUseParameters(BaseModel):
    use_length: Optional[float] = Field(None, description="Length of filament to reduce by, in mm.", examples=[2.2])
    use_weight: Optional[float] = Field(None, description="Filament weight to reduce by, in g.", examples=[5.3])


class SpoolMeasureParameters(BaseModel):
    weight: float = Field(description="Current gross weight of the spool, in g.", examples=[200])


@router.get(
    "",
    name="Find spool",
    description=(
        "Get a list of spools that matches the search query. "
        "A websocket is served on the same path to listen for updates to any spool, or added or deleted spools. "
        "See the HTTP Response code 299 for the content of the websocket messages."
    ),
    response_model_exclude_none=True,
    responses={
        200: {"model": list[Spool]},
        299: {"model": SpoolEvent, "description": "Websocket message"},
    },
)
async def find(
    *,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    filament_name_old: Annotated[
        Optional[str],
        Query(alias="filament_name", title="Filament Name", description="See filament.name.", deprecated=True),
    ] = None,
    filament_id_old: Annotated[
        Optional[str],
        Query(
            alias="filament_id",
            title="Filament ID",
            description="See filament.id.",
            deprecated=True,
            pattern=r"^-?\d+(,-?\d+)*$",
        ),
    ] = None,
    filament_material_old: Annotated[
        Optional[str],
        Query(
            alias="filament_material",
            title="Filament Material",
            description="See filament.material.",
            deprecated=True,
        ),
    ] = None,
    vendor_name_old: Annotated[
        Optional[str],
        Query(alias="vendor_name", title="Vendor Name", description="See filament.vendor.name.", deprecated=True),
    ] = None,
    vendor_id_old: Annotated[
        Optional[str],
        Query(
            alias="vendor_id",
            title="Vendor ID",
            description="See filament.vendor.id.",
            deprecated=True,
            pattern=r"^-?\d+(,-?\d+)*$",
        ),
    ] = None,
    filament_name: Annotated[
        Optional[str],
        Query(
            alias="filament.name",
            title="Filament Name",
            description=(
                "Partial case-insensitive search term for the filament name. Separate multiple terms with a comma. "
                "Specify an empty string to match spools with no filament name. "
                "Surround a term with quotes to search for the exact term."
            ),
        ),
    ] = None,
    filament_id: Annotated[
        Optional[str],
        Query(
            alias="filament.id",
            title="Filament ID",
            description="Match an exact filament ID. Separate multiple IDs with a comma.",
            examples=["1", "1,2"],
            pattern=r"^-?\d+(,-?\d+)*$",
        ),
    ] = None,
    filament_material: Annotated[
        Optional[str],
        Query(
            alias="filament.material",
            title="Filament Material",
            description=(
                "Partial case-insensitive search term for the filament material. Separate multiple terms with a comma. "
                "Specify an empty string to match spools with no filament material. "
                "Surround a term with quotes to search for the exact term."
            ),
        ),
    ] = None,
    filament_vendor_name: Annotated[
        Optional[str],
        Query(
            alias="filament.vendor.name",
            title="Vendor Name",
            description=(
                "Partial case-insensitive search term for the filament vendor name. "
                "Separate multiple terms with a comma. "
                "Specify an empty string to match spools with no vendor name. "
                "Surround a term with quotes to search for the exact term."
            ),
        ),
    ] = None,
    filament_vendor_id: Annotated[
        Optional[str],
        Query(
            alias="filament.vendor.id",
            title="Vendor ID",
            description=(
                "Match an exact vendor ID. Separate multiple IDs with a comma. "
                "Set it to -1 to match spools with filaments with no vendor."
            ),
            examples=["1", "1,2"],
            pattern=r"^-?\d+(,-?\d+)*$",
        ),
    ] = None,
    location: Annotated[
        Optional[str],
        Query(
            title="Location",
            description=(
                "Partial case-insensitive search term for the spool location. Separate multiple terms with a comma. "
                "Specify an empty string to match spools with no location. "
                "Surround a term with quotes to search for the exact term."
            ),
        ),
    ] = None,
    lot_nr: Annotated[
        Optional[str],
        Query(
            title="Lot/Batch Number",
            description=(
                "Partial case-insensitive search term for the spool lot number. Separate multiple terms with a comma. "
                "Specify an empty string to match spools with no lot nr. "
                "Surround a term with quotes to search for the exact term."
            ),
        ),
    ] = None,
    allow_archived: Annotated[
        bool,
        Query(title="Allow Archived", description="Whether to include archived spools in the search results."),
    ] = False,
    sort: Annotated[
        Optional[str],
        Query(
            title="Sort",
            description=(
                'Sort the results by the given field. Should be a comma-separate string with "field:direction" items.'
            ),
            example="filament.name:asc,filament.vendor.id:asc,location:desc",
        ),
    ] = None,
    limit: Annotated[
        Optional[int],
        Query(title="Limit", description="Maximum number of items in the response."),
    ] = None,
    offset: Annotated[int, Query(title="Offset", description="Offset in the full result set if a limit is set.")] = 0,
) -> JSONResponse:
    sort_by: dict[str, SortOrder] = {}
    if sort is not None:
        for sort_item in sort.split(","):
            field, direction = sort_item.split(":")
            sort_by[field] = SortOrder[direction.upper()]

    filament_id = filament_id if filament_id is not None else filament_id_old
    if filament_id is not None:
        filament_ids = [int(filament_id_item) for filament_id_item in filament_id.split(",")]
    else:
        filament_ids = None

    filament_vendor_id = filament_vendor_id if filament_vendor_id is not None else vendor_id_old
    if filament_vendor_id is not None:
        filament_vendor_ids = [int(vendor_id_item) for vendor_id_item in filament_vendor_id.split(",")]
    else:
        filament_vendor_ids = None

    db_items, total_count = await spool.find(
        db=db,
        user_id=current_user.id,
        filament_name=filament_name if filament_name is not None else filament_name_old,
        filament_id=filament_ids,
        filament_material=filament_material if filament_material is not None else filament_material_old,
        vendor_name=filament_vendor_name if filament_vendor_name is not None else vendor_name_old,
        vendor_id=filament_vendor_ids,
        location=location,
        lot_nr=lot_nr,
        allow_archived=allow_archived,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    # Set x-total-count header for pagination
    return JSONResponse(
        content=jsonable_encoder(
            (Spool.from_db(db_item) for db_item in db_items),
            exclude_none=True,
        ),
        headers={"x-total-count": str(total_count)},
    )


@router.websocket(
    "",
    name="Listen to spool changes",
)
async def notify_any(
    websocket: WebSocket,
) -> None:
    await websocket.accept()
    websocket_manager.connect(("spool",), websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            if await websocket.receive_text():
                await websocket.send_json({"status": "healthy"})
    except WebSocketDisconnect:
        websocket_manager.disconnect(("spool",), websocket)


@router.get(
    "/{spool_id}",
    name="Get spool",
    description=(
        "Get a specific spool. A websocket is served on the same path to listen for changes to the spool. "
        "See the HTTP Response code 299 for the content of the websocket messages."
    ),
    response_model_exclude_none=True,
    responses={404: {"model": Message}, 299: {"model": SpoolEvent, "description": "Websocket message"}},
)
async def get(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    spool_id: int,
) -> Spool:
    db_item = await spool.get_by_id(db, spool_id, current_user.id)
    return Spool.from_db(db_item)


@router.websocket(
    "/{spool_id}",
    name="Listen to spool changes",
)
async def notify(
    websocket: WebSocket,
    spool_id: int,
) -> None:
    await websocket.accept()
    websocket_manager.connect(("spool", str(spool_id)), websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            if await websocket.receive_text():
                await websocket.send_json({"status": "healthy"})
    except WebSocketDisconnect:
        websocket_manager.disconnect(("spool", str(spool_id)), websocket)


@router.post(
    "",
    name="Add spool",
    description=(
        "Add a new spool to the database. "
        "Only specify either remaining_weight or used_weight. "
        "If no weight is set, the spool will be assumed to be full."
    ),
    response_model_exclude_none=True,
    response_model=Spool,
    responses={
        400: {"model": Message},
    },
)
async def create(  # noqa: ANN201
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    body: SpoolParameters,
):
    if body.remaining_weight is not None and body.used_weight is not None:
        return JSONResponse(
            status_code=400,
            content={"message": "Only specify either remaining_weight or used_weight."},
        )

    if body.extra:
        all_fields = await get_extra_fields(db, EntityType.spool)
        try:
            validate_extra_field_dict(all_fields, body.extra)
        except ValueError as e:
            return JSONResponse(status_code=400, content=Message(message=str(e)).dict())

    try:
        db_item = await spool.create(
            db=db,
            user_id=current_user.id,
            filament_id=body.filament_id,
            price=body.price,
            initial_weight=body.initial_weight,
            spool_weight=body.spool_weight,
            remaining_weight=body.remaining_weight,
            used_weight=body.used_weight,
            first_used=body.first_used,
            last_used=body.last_used,
            location=body.location,
            lot_nr=body.lot_nr,
            comment=body.comment,
            archived=body.archived,
            extra=body.extra,
        )
        return Spool.from_db(db_item)
    except ItemCreateError:
        logger.exception("Failed to create spool.")
        return JSONResponse(
            status_code=400,
            content={"message": "Failed to create spool, see server logs for more information."},
        )


@router.patch(
    "/{spool_id}",
    name="Update spool",
    description=(
        "Update any attribute of a spool. "
        "Only fields specified in the request will be affected. "
        "remaining_weight and used_weight can't be set at the same time. "
        "If extra is set, all existing extra fields will be removed and replaced with the new ones."
    ),
    response_model_exclude_none=True,
    response_model=Spool,
    responses={
        400: {"model": Message},
        404: {"model": Message},
    },
)
async def update(  # noqa: ANN201
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    spool_id: int,
    body: SpoolUpdateParameters,
):
    patch_data = body.model_dump(exclude_unset=True)

    if body.remaining_weight is not None and body.used_weight is not None:
        return JSONResponse(
            status_code=400,
            content={"message": "Only specify either remaining_weight or used_weight."},
        )

    if body.extra:
        all_fields = await get_extra_fields(db, EntityType.spool)
        try:
            validate_extra_field_dict(all_fields, body.extra)
        except ValueError as e:
            return JSONResponse(status_code=400, content=Message(message=str(e)).dict())

    try:
        db_item = await spool.update(
            db=db,
            spool_id=spool_id,
            user_id=current_user.id,
            data=patch_data,
        )
    except ItemCreateError:
        logger.exception("Failed to update spool.")
        return JSONResponse(
            status_code=400,
            content={"message": "Failed to update spool, see server logs for more information."},
        )

    return Spool.from_db(db_item)


@router.delete(
    "/{spool_id}",
    name="Delete spool",
    description="Delete a spool.",
    responses={404: {"model": Message}},
)
async def delete(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    spool_id: int,
) -> Message:
    await spool.delete(db, spool_id, current_user.id)
    return Message(message="Success!")


@router.put(
    "/{spool_id}/use",
    name="Use spool filament",
    description=(
        "Use some length or weight of filament from the spool. Specify either a length or a weight, not both."
    ),
    response_model_exclude_none=True,
    response_model=Spool,
    responses={
        400: {"model": Message},
        404: {"model": Message},
    },
)
async def use(  # noqa: ANN201
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    spool_id: int,
    body: SpoolUseParameters,
    background_tasks: BackgroundTasks,
):
    # Calculate remaining weight before update
    spool_before = await spool.get_by_id(db, spool_id, current_user.id)
    remaining_weight_before = None
    if spool_before.initial_weight is not None:
        remaining_weight_before = max(spool_before.initial_weight - spool_before.used_weight, 0)
    elif spool_before.filament.weight is not None:
        remaining_weight_before = max(spool_before.filament.weight - spool_before.used_weight, 0)

    if body.use_weight is not None:
        await spool.use_weight(db, spool_id, current_user.id, body.use_weight)
    elif body.use_length is not None:
        await spool.use_length(db, spool_id, current_user.id, body.use_length)
    else:
        return JSONResponse(
            status_code=400,
            content={"message": "Either use_weight or use_length must be specified."},
        )
        
    # Re-fetch the spool to ensure it's fresh and relationships are loaded
    # This prevents MissingGreenlet error when accessing relationships after commit
    db_item = await spool.get_by_id(db, spool_id, current_user.id)
        
    # Calculate remaining weight after update
    remaining_weight_after = None
    if db_item.initial_weight is not None:
        remaining_weight_after = max(db_item.initial_weight - db_item.used_weight, 0)
    elif db_item.filament.weight is not None:
        remaining_weight_after = max(db_item.filament.weight - db_item.used_weight, 0)
        
    # Trigger notifications in background
    background_tasks.add_task(
        send_usage_notifications,
        user_id=current_user.id,
        spool_id=spool_id,
        use_weight=body.use_weight,
        use_length=body.use_length,
        remaining_weight_before=remaining_weight_before,
        remaining_weight_after=remaining_weight_after,
        spool_name=f"{db_item.filament.name} (#{spool_id})" if db_item.filament and db_item.filament.name else f"Spool #{spool_id}",
    )
            
    return Spool.from_db(db_item)

async def send_usage_notifications(
    user_id: int,
    spool_id: int,
    use_weight: float | None,
    use_length: float | None,
    remaining_weight_before: float | None,
    remaining_weight_after: float | None,
    spool_name: str,
) -> None:
    """Send usage notifications in the background."""
    from spoolcloud.database.database import get_db_session_context
    from spoolcloud.services.notification_service import NotificationService
    import asyncio

    async with get_db_session_context() as db:
        try:
            # Get user language
            from spoolcloud.database import notification
            config = await notification.get_config(db, user_id)
            language = config.language if config else "zh-CN"
            
            # Translations
            translations = {
                "zh-CN": {
                    "deduction_title": "耗材使用提醒",
                    "deduction_message": "已使用 {usage} ({spool_name})。剩余: {remaining:.1f}g",
                    "deduction_message_no_remaining": "已使用 {usage} ({spool_name})。",
                    "low_supply_title": "余量不足警告",
                    "low_supply_message": "{spool_name} 余量不足！剩余: {remaining:.1f}g",
                },
                "en-US": {
                    "deduction_title": "Filament Used",
                    "deduction_message": "Used {usage} from {spool_name}. Remaining: {remaining:.1f}g",
                    "deduction_message_no_remaining": "Used {usage} from {spool_name}.",
                    "low_supply_title": "Low Supply Warning",
                    "low_supply_message": "{spool_name} is running low! Remaining: {remaining:.1f}g",
                }
            }
            
            t = translations.get(language, translations["zh-CN"])

            # 1. Deduction notification
            usage_str = ""
            if use_weight is not None:
                usage_str = f"{use_weight}g"
            elif use_length is not None:
                usage_str = f"{use_length}mm"
                
            message = t["deduction_message_no_remaining"].format(usage=usage_str, spool_name=spool_name)
            if remaining_weight_after is not None:
                message = t["deduction_message"].format(usage=usage_str, spool_name=spool_name, remaining=remaining_weight_after)

            await NotificationService.send_notification(
                db=db,
                user_id=user_id,
                type="deduction",
                title=t["deduction_title"],
                message=message,
            )
            
            # 2. Low supply notification
            # Trigger if it is below 100g (User requested to trigger every time)
            if remaining_weight_after is not None and remaining_weight_after < 100:
                # Add delay to prevent rate limiting or message grouping
                await asyncio.sleep(1)
                
                await NotificationService.send_notification(
                    db=db,
                    user_id=user_id,
                    type="low_supply",
                    title=t["low_supply_title"],
                    message=t["low_supply_message"].format(spool_name=spool_name, remaining=remaining_weight_after),
                )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")


@router.put(
    "/{spool_id}/measure",
    name="Use spool filament based on the current weight measurement",
    description=("Use some weight of filament from the spool. Specify the current gross weight of the spool."),
    response_model_exclude_none=True,
    response_model=Spool,
    responses={
        400: {"model": Message},
        404: {"model": Message},
    },
)
async def measure(  # noqa: ANN201
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    spool_id: int,
    body: SpoolMeasureParameters,
):
    try:
        await spool.measure(db, spool_id, current_user.id, body.weight)
        # Re-fetch the spool to ensure it's fresh and relationships are loaded
        db_item = await spool.get_by_id(db, spool_id, current_user.id)
        return Spool.from_db(db_item)
    except SpoolMeasureError as e:
        logger.exception("Failed to update spool measurement.")
        return JSONResponse(
            status_code=400,
            content={"message": e.args[0]},
        )
