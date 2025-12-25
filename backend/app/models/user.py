import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String
from sqlalchemy.sql import func

from app.core.types import GUID
from app.db.session import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    CORREDOR = "corredor"
    FINANZAS = "finanzas"
    LECTURA = "lectura"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.CORREDOR)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
