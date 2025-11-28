"""Authentication and Authorization module."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from spoolcloud.database.database import get_db_session
from spoolcloud.database.models import APIKey, User, UserRole
from spoolcloud.env import get_auth_secret

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


async def create_user(db: AsyncSession, username: str, password: str) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)
    user = User(username=username, password_hash=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(user)
    return user


async def ensure_admin_user(db: AsyncSession) -> None:
    """Ensure that an admin user exists. If no users exist, create default admin."""
    # Check if any user exists
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    
    if not user:
        # Create default admin user
        import logging
        logger = logging.getLogger(__name__)
        logger.info("No users found. Creating default admin user (admin/admin).")
        
        hashed_password = get_password_hash("admin")
        admin = User(
            username="admin", 
            password_hash=hashed_password, 
            is_admin=True, 
            role=UserRole.ADMIN.value
        )
        db.add(admin)
        await db.commit()
        logger.info("Default admin user created successfully.")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_auth_secret(), algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Get the current user from JWT token or API Key."""
    # 1. Try API Key first
    if api_key:
        # Expect format "Bearer sk-..." or just "sk-..."? 
        # APIKeyHeader usually returns the value.
        # If user sends "Authorization: Bearer <key>", api_key will be "Bearer <key>"
        # We should handle both.
        if api_key.startswith("Bearer "):
            key_value = api_key.split(" ")[1]
        else:
            key_value = api_key
        
        # Check if it looks like an API key (e.g. starts with sk-)
        # If it's a JWT, it might also be passed here if the client uses Authorization header for JWT.
        # So we need to distinguish.
        # Let's assume API keys have a distinct prefix or we try to decode as JWT first?
        # Actually, if oauth2_scheme is used, it extracts Bearer token.
        # If we use APIKeyHeader, it extracts the whole header.
        
        # Strategy:
        # If token is valid JWT, use it.
        # If not, try to treat it as API Key.
        pass

    # Actually, oauth2_scheme will extract the token from "Authorization: Bearer <token>".
    # So `token` variable will hold the token string.
    # If the user provided an API Key as a Bearer token, `token` will be the API Key.
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to decode as JWT
    try:
        payload = jwt.decode(token, get_auth_secret(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        # Not a valid JWT. Check if it is an API Key.
        # API Key format: sk-<prefix>...
        # We need to hash it and check DB.
        # But we don't store the key, we store the hash.
        # Wait, the plan says: "key_hash: String (存储哈希值，不存明文)"
        # And "key_prefix: String".
        # We should probably verify the prefix first to avoid hashing everything.
        
        # In this implementation plan, we didn't specify exact API key format validation here,
        # but we should try to look it up.
        
        # Hash the token (which is the API key)
        # But wait, we need to know WHICH user it belongs to?
        # No, we search by hash.
        # But hashing is one-way. We can't search by hash if we use a salted hash like argon2.
        # If we use SHA256 (fast), we can search.
        # The plan said "key_hash: String".
        # If we use argon2 for API keys, we can't search efficiently.
        # Usually API keys are: prefix + secret.
        # We can store the hash of the secret.
        # But to find the user, we either need to iterate all keys (slow) or store a lookup ID in the key.
        # Or use a fast hash like SHA256 for API keys since they are high entropy.
        # Let's assume SHA256 for API keys.
        
        import hashlib
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key_obj = result.scalars().first()
        
        if api_key_obj:
            # Update last used
            api_key_obj.last_used_at = datetime.utcnow()
            await db.commit()
            
            # Get user
            result = await db.execute(select(User).where(User.id == api_key_obj.user_id))
            user = result.scalars().first()
            if user:
                return user
        
        raise credentials_exception

    # If JWT valid
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
