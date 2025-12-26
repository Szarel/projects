import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from google.auth.transport import requests as grequests
from google.oauth2 import id_token as google_id_token

from app.core.security import create_access_token, verify_password, get_password_hash
from app.db.session import get_session
from app.models.user import User, UserRole
from app.schemas.user import GoogleLoginRequest, Token, UserCreate, UserRead
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> UserRead:
    existing = await _get_user_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)
) -> Token:
    user = await _get_user_by_email(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@router.post("/google", response_model=Token)
async def login_google(payload: GoogleLoginRequest, session: AsyncSession = Depends(get_session)) -> Token:
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google auth no configurado")

    try:
        id_info = google_id_token.verify_oauth2_token(
            payload.id_token,
            grequests.Request(),
            settings.google_client_id,
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de Google inválido")

    email = id_info.get("email")
    full_name = id_info.get("name")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google no entregó email")

    user = await _get_user_by_email(session, email)
    if user and not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo")

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.CORREDOR,
            hashed_password=get_password_hash(str(uuid.uuid4())),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)
