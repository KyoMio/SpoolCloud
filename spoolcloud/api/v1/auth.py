"""Auth endpoints."""

import hashlib
import secrets
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from spoolcloud import auth, env
from spoolcloud.api.v1 import models as v1_models
from spoolcloud.database import database, models

router = APIRouter(prefix="/auth", tags=["auth (认证)"])


@router.post("/token", response_model=v1_models.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(database.get_db_session),
) -> v1_models.Token:
    """Login to get an access token."""
    # Find user
    result = await db.execute(select(models.User).where(models.User.username == form_data.username))
    user = result.scalars().first()

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    return v1_models.Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=v1_models.User)
async def read_users_me(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
) -> v1_models.User:
    """Get current user info."""
    return v1_models.User.from_db(current_user)


@router.post("/api-key", response_model=v1_models.APIKeyResponse)
async def create_api_key(
    body: v1_models.APIKeyCreate,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(database.get_db_session),
) -> v1_models.APIKeyResponse:
    """Create a new API key."""
    # Generate key: sk-<prefix>-<secret>
    # We store prefix and hash of secret.
    # Actually, usually we generate a random string.
    # Let's say: sk-<32 chars>
    
    # Generate a random key
    raw_key = "sk-" + secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]  # "sk-xxxxx"
    
    # Hash it
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    api_key = models.APIKey(
        user_id=current_user.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        label=body.label,
        created_at=datetime.utcnow(),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    api_key_dto = v1_models.APIKey.from_db(api_key)
    return v1_models.APIKeyResponse(
        **api_key_dto.model_dump(),
        key=raw_key,
    )


@router.get("/api-key", response_model=list[v1_models.APIKey])
async def list_api_keys(
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(database.get_db_session),
) -> list[v1_models.APIKey]:
    """List API keys."""
    result = await db.execute(select(models.APIKey).where(models.APIKey.user_id == current_user.id))
    return [v1_models.APIKey.from_db(item) for item in result.scalars().all()]


@router.delete("/api-key/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(database.get_db_session),
) -> None:
    """Revoke an API key."""
    result = await db.execute(
        select(models.APIKey).where(models.APIKey.id == api_key_id, models.APIKey.user_id == current_user.id)
    )
    api_key = result.scalars().first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    await db.delete(api_key)
    await db.commit()


class UserCreate(v1_models.BaseModel):
    username: str = v1_models.Field(min_length=3, max_length=64)
    password: str = v1_models.Field(min_length=8)
    invite_code: str = v1_models.Field(min_length=1, description="Invite code required for registration")


@router.post(
    "/register",
    name="Register user",
    description="Register a new user with invite code.",
    response_model=v1_models.User,
    responses={400: {" model": v1_models.Message}, 403: {"model": v1_models.Message}},
)
async def register(
    db: Annotated[AsyncSession, Depends(database.get_db_session)],
    body: UserCreate,
) -> v1_models.User:
    if not env.is_registration_allowed():
        return JSONResponse(
            status_code=403,
            content={"message": "Registration is disabled."},
        )

    # Validate invite code
    result = await db.execute(select(models.InviteCode).where(models.InviteCode.code == body.invite_code))
    invite_code_obj = result.scalars().first()
    
    if not invite_code_obj:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid invite code."},
        )
    
    if invite_code_obj.used_by_user_id is not None:
        return JSONResponse(
            status_code=400,
            content={"message": "Invite code already used."},
        )

    try:
        user = await auth.create_user(db, body.username, body.password)
        
        # Bind invite code to user
        invite_code_obj.used_by_user_id = user.id
        invite_code_obj.used_at = datetime.utcnow()
        await db.commit()
        
        return v1_models.User.from_db(user)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"message": str(e)},
        )


class ChangePassword(v1_models.BaseModel):
    old_password: str = v1_models.Field(min_length=1)
    new_password: str = v1_models.Field(min_length=8)


@router.post(
    "/change-password",
    name="Change password",
    description="Change the current user's password.",
    response_model=v1_models.Message,
    responses={400: {"model": v1_models.Message}, 401: {"model": v1_models.Message}},
)
async def change_password(
    body: ChangePassword,
    current_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(database.get_db_session),
) -> v1_models.Message:
    if not auth.verify_password(body.old_password, current_user.password_hash):
        return JSONResponse(
            status_code=401,
            content={"message": "Incorrect old password."},
        )

    current_user.password_hash = auth.get_password_hash(body.new_password)
    await db.commit()
    
    return v1_models.Message(message="Password changed successfully.")


async def require_admin(current_user: Annotated[models.User, Depends(auth.get_current_user)]) -> models.User:
    """Dependency to require admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(database.get_db_session),
) -> models.User:
    """Get the current user from a websocket connection."""
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=403, detail="Authentication required")

    try:
        user = await auth.get_current_user(token=token, api_key=None, db=db)
        return user
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=403, detail="Invalid credentials")
