"""Router setup for the v1 version of the API."""

# ruff: noqa: D103

import asyncio
import logging
from typing import Annotated

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from spoolcloud import env
from spoolcloud.database.database import backup_global_db
from spoolcloud.exceptions import ItemNotFoundError
from spoolcloud.ws import websocket_manager

from . import (
    admin,
    auth,
    export,
    externaldb,
    field,
    filament,
    filament_preset,
    invite_code,
    invite_code,
    models,
    notification,
    other,
    setting,
    spool,
    vendor,
)

# ... (existing code)

app = FastAPI(
    title="SpoolCloud REST API v1",
    version="1.0.0",
    description="""
    REST API for SpoolCloud.
    SpoolCloud 的 REST API。

    The API is served on the path `/api/v1/`.
    API 服务路径为 `/api/v1/`。

    Some endpoints also serve a websocket on the same path. The websocket is used to listen for changes to the data
    that the endpoint serves. The websocket messages are JSON objects. Additionally, there is a root-level websocket
    endpoint that listens for changes to any data in the database.

    部分端点在相同路径上也提供 WebSocket 服务。WebSocket 用于监听端点服务数据的变化。WebSocket 消息为 JSON 对象。此外，还有一个根级别的 WebSocket 端点，用于监听数据库中任何数据的变化。
    """,
)

# Add routers
app.include_router(auth.router)
app.include_router(filament.router)
app.include_router(filament_preset.router)
app.include_router(spool.router)
app.include_router(vendor.router)
app.include_router(setting.router)
app.include_router(notification.router)
app.include_router(field.router)
app.include_router(other.router)
app.include_router(externaldb.router)
app.include_router(export.router)
app.include_router(invite_code.router)
app.include_router(admin.router)

logger = logging.getLogger(__name__)


@app.exception_handler(ItemNotFoundError)
async def itemnotfounderror_exception_handler(_request: Request, exc: ItemNotFoundError) -> Response:
    logger.debug(exc, exc_info=True)
    return JSONResponse(
        status_code=404,
        content={"message": exc.args[0]},
    )


# Add a general info endpoint
@app.get("/info")
async def info() -> models.Info:
    """Return general info about the API."""
    return models.Info(
        version=env.get_version(),
        debug_mode=env.is_debug_mode(),
        automatic_backups=env.is_automatic_backup_enabled(),
        data_dir=str(env.get_data_dir().resolve()),
        logs_dir=str(env.get_logs_dir().resolve()),
        backups_dir=str(env.get_backups_dir().resolve()),
        db_type=str(env.get_database_type() or "sqlite"),
        git_commit=env.get_commit_hash(),
        build_date=env.get_build_date(),
    )


# Add health check endpoint
@app.get("/health")
async def health() -> models.HealthCheck:
    """Return a health check."""
    return models.HealthCheck(status="healthy")


# Add endpoint for triggering a db backup
@app.post(
    "/backup",
    description="Trigger a database backup. Only applicable for SQLite databases.",
    response_model=models.BackupResponse,
    responses={500: {"model": models.Message}},
)
async def backup(
    current_user: Annotated[models.User, Depends(auth.require_admin)],
):  # noqa: ANN201
    """Trigger a database backup."""
    path = await backup_global_db()
    if path is None:
        return JSONResponse(
            status_code=500,
            content={"message": "Backup failed. See server logs for more information."},
        )
    return models.BackupResponse(path=str(path))


@app.websocket(
    "/",
    name="Listen to any changes",
)
async def notify(
    websocket: WebSocket,
    current_user: Annotated[models.User, Depends(auth.get_current_user_ws)],
) -> None:
    await websocket.accept()
    websocket_manager.connect((), websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            if await websocket.receive_text():
                await websocket.send_json({"status": "healthy"})
    except WebSocketDisconnect:
        websocket_manager.disconnect((), websocket)



