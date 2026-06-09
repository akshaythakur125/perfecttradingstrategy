import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from services.auth import hash_password, verify_password, create_access_token
from schemas.schemas import LoginRequest, RegisterRequest, TokenResponse
from models.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64


def validate_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at most {MAX_PASSWORD_LENGTH} characters")
    if not re.search(r'[A-Za-z]', password):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter")
    if not re.search(r'[0-9]', password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    return password


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    validate_password(req.password)

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)
