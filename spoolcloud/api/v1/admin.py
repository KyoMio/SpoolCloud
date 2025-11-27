"""Admin endpoints for user management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from spoolcloud import auth
from spoolcloud.api.v1 import models as v1_models
from spoolcloud.database import database, models
from spoolcloud.api.v1.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin (管理员)"])


@router.get("/users")
async def list_users(
    current_user: Annotated[models.User, Depends(require_admin)],
    db: AsyncSession = Depends(database.get_db_session),
) -> list[dict]:
    """List all users (admin only)."""
    result = await db.execute(
        select(models.User).order_by(models.User.created_at.desc())
    )
    users = result.scalars().all()
    
    response = []
    for user in users:
        # Load invite code relationship
        await db.refresh(user, ["used_invite_code"])
        
        response.append({
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "invite_code_used": user.used_invite_code.code if user.used_invite_code else None,
        })
    
    return response


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[models.User, Depends(require_admin)],
    db: AsyncSession = Depends(database.get_db_session),
) -> None:
    """Delete a user (admin only, cannot delete self)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    await db.delete(user)
    await db.commit()
