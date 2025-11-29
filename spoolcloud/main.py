"""Main entrypoint to the server."""

import logging
import subprocess
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from prometheus_client import generate_latest
from scheduler.asyncio.scheduler import Scheduler

from spoolcloud import auth, database, env, externaldb
from spoolcloud.api.v1.router import app as v1_app
from spoolcloud.api.v1 import router as api_v1_router
from spoolcloud.client import SinglePageApplication
from spoolcloud.database.database import get_connection_url
from spoolcloud.database import database
from spoolcloud.prometheus.metrics import registry

# Define a console logger
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(name)-26s %(levelname)-8s %(message)s"))

# Setup the spoolcloud logger, which all spoolcloud modules will use
log_level = env.get_logging_level()
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(console_handler)

# Fix uvicorn logging
logging.getLogger("uvicorn").setLevel(log_level)
if logging.getLogger("uvicorn").handlers:
    logging.getLogger("uvicorn").removeHandler(logging.getLogger("uvicorn").handlers[0])
logging.getLogger("uvicorn").addHandler(console_handler)

logging.getLogger("uvicorn.error").setLevel(log_level)
logging.getLogger("uvicorn.error").addHandler(console_handler)

access_handlers = logging.getLogger("uvicorn.access").handlers
if access_handlers:
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("uvicorn.access").removeHandler(access_handlers[0])
    logging.getLogger("uvicorn.access").addHandler(console_handler)

# Get logger instance for this module
logger = logging.getLogger(__name__)


# Setup FastAPI
app = FastAPI(
    debug=env.is_debug_mode(),
    title="SpoolCloud",
    description="""
    REST API for SpoolCloud.
    SpoolCloud 的 REST API。

    The API is served on the path `/api/v1/`.
    API 服务路径为 `/api/v1/`。

    Some endpoints also serve a websocket on the same path. The websocket is used to listen for changes to the data
    that the endpoint serves. The websocket messages are JSON objects. Additionally, there is a root-level websocket
    endpoint that listens for changes to any data in the database.

    部分端点在相同路径上也提供 WebSocket 服务。WebSocket 用于监听端点服务数据的变化。WebSocket 消息为 JSON 对象。此外，还有一个根级别的 WebSocket 端点，用于监听数据库中任何数据的变化。

    ## Authentication / 鉴权

    该项目支持两种鉴权方式：**JWT 令牌 (Token)** 和 **API 密钥 (API Key)**。

    这两种方式都需要在 HTTP 请求头中添加 `Authorization` 字段，格式均为 `Bearer <你的凭证>`。

    ### 1. 使用 JWT 令牌 (适合前端或临时会话)

    **获取 Token:**
    你需要先通过用户名和密码调用登录接口获取 Token。

    *   **接口**: `POST /api/v1/auth/token`
    *   **Content-Type**: `application/x-www-form-urlencoded`
    *   **参数**:
        *   `username`: 你的用户名
        *   `password`: 你的密码

    **响应示例**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
      "token_type": "bearer"
    }
    ```

    **使用方式**:
    在后续请求的 Header 中带上：
    ```http
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR...
    ```

    ### 2. 使用 API 密钥 (适合第三方集成或脚本)

    **获取 API Key**:
    你需要先登录（或使用 JWT）调用接口生成一个永久有效的 API Key。

    *   **接口**: `POST /api/v1/auth/api-key`
    *   **Body**:
        ```json
        {
          "label": "My Script Key"
        }
        ```

    **响应示例**:
    ```json
    {
      "id": 1,
      "key_prefix": "sk-abc12345",
      "label": "My Script Key",
      "created_at": "2023-10-27T10:00:00Z",
      "key": "sk-abc12345..."  // 注意：完整的 Key 只会显示这一次
    }
    ```

    **使用方式**:
    与 JWT 一样，将其放在 Header 中：
    ```http
    Authorization: Bearer sk-abc12345...
    ```
    """,
    version=env.get_version(),
    docs_url=None,  # Disable main app docs
    redoc_url=None,  # Disable main app redoc
)
app.add_middleware(GZipMiddleware)
app.mount(env.get_base_path() + "/api/v1", v1_app)


# Redirect /docs and /redoc to the v1 API documentation
@app.get(env.get_base_path() + "/docs")
def redirect_to_docs() -> Response:
    """Redirect to v1 API documentation."""
    return RedirectResponse(env.get_base_path() + "/api/v1/docs")


@app.get(env.get_base_path() + "/redoc")
def redirect_to_redoc() -> Response:
    """Redirect to v1 API ReDoc."""
    return RedirectResponse(env.get_base_path() + "/api/v1/redoc")



# WA for prometheus /metrics bind with SinglePageApp at root
@app.get(
    env.get_base_path() + "/metrics",
    response_class=PlainTextResponse,
    name="Get metrics for prometheus",
    description=(
        "Get app metrics for prometheusIf enabled SPOOLCLOUD_METRICS_ENABLED returned metrics by Spools and Filaments"
    ),
)
def get_metrics() -> bytes:
    """Return prometheus metrics."""
    return generate_latest(registry)


base_path = env.get_base_path()
if base_path != "":
    logger.info("Base path is: %s", base_path)

    # If base path is set, add a redirect from non-slash suffix to slash
    # suffix. Otherwise it won't work.
    @app.get(base_path)
    def root_redirect() -> Response:
        """Redirect to base path."""
        return RedirectResponse(base_path + "/")


# Return a dynamic js config file
# This is so that the client side can access the base path variable.
@app.get(env.get_base_path() + "/config.js")
def get_configjs() -> Response:
    """Return a dynamic js config file."""
    if '"' in base_path:
        raise ValueError("Base path contains quotes, which are not allowed.")

    return Response(
        content=f"""
window.SPOOLCLOUD_BASE_PATH = "{base_path}";
""",
        media_type="text/javascript",
    )


# Mount the client side app
app.mount(base_path, app=SinglePageApplication(directory="client/dist", base_path=env.get_base_path()))


def add_cors_middleware() -> None:
    """Add CORS middleware to the FastAPI app based on environment settings."""
    origins = []
    if env.is_debug_mode():
        logger.warning("Running in debug mode, allowing all origins.")
        origins = ["*"]
    elif env.is_cors_defined():
        cors_origins = env.get_cors_origin()
        if cors_origins:
            logger.info("CORS origins defined: %s", cors_origins)
            origins = cors_origins
        else:
            logger.warning("CORS origins are not defined, no CORS will be applied.")

    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )


add_cors_middleware()


def add_file_logging() -> None:
    """Add file logging to the root logger."""
    # Define a file logger with log rotation
    log_file = env.get_logs_dir().joinpath("spoolcloud.log")
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=5)
    file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s", "%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(file_handler)


@app.on_event("startup")
async def startup() -> None:
    """Run the service's startup sequence."""
    # Check that the data directory is writable
    env.check_write_permissions()

    # Don't add file logging until we have verified that the data directory is writable
    add_file_logging()

    logger.info(
        "Starting SpoolCloud v%s (commit: %s) (built: %s)",
        app.version,
        env.get_commit_hash(),
        env.get_build_date(),
    )

    logger.info("Using data directory: %s", env.get_data_dir().resolve())
    logger.info("Using logs directory: %s", env.get_logs_dir().resolve())
    logger.info("Using backups directory: %s", env.get_backups_dir().resolve())

    logger.info("Setting up database...")
    database.setup_db(database.get_connection_url())

    logger.info("Performing migrations...")
    # Run alembic in a subprocess.
    # There is some issue with the uvicorn worker that causes the process to hang when running alembic directly.
    # See: https://github.com/sqlalchemy/alembic/discussions/1155
    project_root = Path(__file__).parent.parent
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=project_root)  # noqa: S603, S607, ASYNC221

    # Ensure admin user exists
    async with database.get_db_session_context() as session:
        await auth.ensure_admin_user(session)

    # Setup scheduler
    schedule = Scheduler()
    database.schedule_tasks(schedule)
    externaldb.schedule_tasks(schedule)

    logger.info("Startup complete.")

    if env.is_docker() and not env.is_data_dir_mounted():
        logger.warning("!!!! WARNING !!!!")
        logger.warning("!!!! WARNING !!!!")
        logger.warning("The data directory is not mounted.")
        logger.warning(
            'SpoolCloud stores its database in the container directory "%s". '
            "If this directory isn't mounted to the host OS, the database will be lost when the container is stopped.",
            env.get_data_dir(),
        )
        logger.warning(
            "Please carefully read the docker part of the README.md file, "
            "and ensure your docker-compose file matches the example.",
        )
        logger.warning("!!!! WARNING !!!!")
        logger.warning("!!!! WARNING !!!!")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
