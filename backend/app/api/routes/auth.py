from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
import httpx

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_active_user

router = APIRouter()
settings = get_settings()


# Schemas
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class GoogleTokenRequest(BaseModel):
    credential: str


# Helper functions
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def is_email_allowed(email: str) -> bool:
    """Check if email is in the allowed list."""
    if not settings.allowed_emails:
        return True  # Allow all if no whitelist set
    allowed = [e.strip().lower() for e in settings.allowed_emails.split(",")]
    return email.lower() in allowed


# Routes
@router.post("/google", response_model=Token)
async def google_auth(
    request: GoogleTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange Google ID token for app JWT.
    Used with Google Sign-In button on frontend.
    """
    # Verify the Google ID token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={request.credential}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    token_info = response.json()

    # Verify the token is for our app
    if token_info.get("aud") != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not issued for this application",
        )

    email = token_info.get("email")
    name = token_info.get("name", email.split("@")[0] if email else "User")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google",
        )

    # Check if email is allowed
    if not is_email_allowed(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not authorized to access this application",
        )

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Check if first user (make admin)
        result = await db.execute(select(User))
        is_first_user = result.first() is None

        user = User(
            email=email,
            hashed_password="",  # No password for OAuth users
            name=name,
            role=UserRole.ADMIN if is_first_user else UserRole.EDITOR,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return current_user


@router.get("/config")
async def get_auth_config():
    """Get OAuth configuration for frontend."""
    return {
        "google_client_id": settings.google_client_id,
    }
