"""Invite code endpoints."""

import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from spoolcloud import auth
from spoolcloud.api.v1 import models as v1_models
from spoolcloud.database import database, models

router = APIRouter(prefix="/invite-code", tags=["invite-code (邀请码)"])


async def require_admin(current_user: Annotated[models.User, Depends(auth.get_current_user)]) -> models.User:
    """Dependency to require admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    current_user: Annotated[models.User, Depends(require_admin)],
    db: AsyncSession = Depends(database.get_db_session),
) -> dict:
    """Generate a new invite code (admin only)."""
    # Generate a secure random code
    code = secrets.token_urlsafe(24)  # ~32 chars
    
    invite_code = models.InviteCode(
        code=code,
        created_by_user_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(invite_code)
    await db.commit()
    await db.refresh(invite_code)
    
    return {
        "id": invite_code.id,
        "code": invite_code.code,
        "created_at": invite_code.created_at.isoformat(),
        "used": False,
    }


@router.get("")
async def list_invite_codes(
    current_user: Annotated[models.User, Depends(require_admin)],
    db: AsyncSession = Depends(database.get_db_session),
) -> list[dict]:
    """List all invite codes (admin only)."""
    result = await db.execute(
        select(models.InviteCode)
        .order_by(models.InviteCode.created_at.desc())
    )
    invite_codes = result.scalars().all()
    
    response = []
    for code_obj in invite_codes:
        # Load relationships
        await db.refresh(code_obj, ["used_by"])
        
        response.append({
            "id": code_obj.id,
            "code": code_obj.code,
            "created_at": code_obj.created_at.isoformat(),
            "used": code_obj.used_by_user_id is not None,
            "used_by_username": code_obj.used_by.username if code_obj.used_by else None,
            "used_at": code_obj.used_at.isoformat() if code_obj.used_at else None,
        })
    
    return response


@router.delete("/{invite_code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite_code(
    invite_code_id: int,
    current_user: Annotated[models.User, Depends(require_admin)],
    db: AsyncSession = Depends(database.get_db_session),
) -> None:
    """Delete an unused invite code (admin only)."""
    result = await db.execute(
        select(models.InviteCode).where(models.InviteCode.id == invite_code_id)
    )
    invite_code = result.scalars().first()
    
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )
    
    if invite_code.used_by_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a used invite code",
        )
    
    await db.delete(invite_code)
    await db.commit()


@router.post("/validate")
async def validate_invite_code(
    code: str,
    db: AsyncSession = Depends(database.get_db_session),
) -> dict:
    """Validate an invite code (public endpoint)."""
    result = await db.execute(
        select(models.InviteCode).where(models.InviteCode.code == code)
    )
    invite_code = result.scalars().first()
    
    if not invite_code:
        return {"valid": False, "message": "Invalid invite code"}
    
    if invite_code.used_by_user_id is not None:
        return {"valid": False, "message": "Invite code already used"}
    
    return {"valid": True, "message": "Valid invite code"}
