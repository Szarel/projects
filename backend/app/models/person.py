import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.sql import func

from app.core.types import GUID
from app.db.session import Base


class PersonType(str, Enum):
    PROPIETARIO = "propietario"
    ARRENDATARIO = "arrendatario"
    CORREDOR = "corredor"
    PROVEEDOR = "proveedor"


class Person(Base):
    __tablename__ = "personas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tipo = Column(SAEnum(PersonType, name="tipo_persona"), nullable=False)
    nombres = Column(String(120), nullable=False)
    apellidos = Column(String(120), nullable=True)
    rut = Column(String(20), unique=True, nullable=True)
    email = Column(String(200), nullable=True)
    telefono = Column(String(50), nullable=True)
    razon_social = Column(String(200), nullable=True)
    giro = Column(String(200), nullable=True)
    direccion_contacto = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
