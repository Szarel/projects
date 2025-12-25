from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.person import PersonType


class PersonBase(BaseModel):
    tipo: PersonType
    nombres: str = Field(..., max_length=120)
    apellidos: Optional[str] = Field(None, max_length=120)
    rut: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    razon_social: Optional[str] = Field(None, max_length=200)
    giro: Optional[str] = Field(None, max_length=200)
    direccion_contacto: Optional[str] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    tipo: Optional[PersonType] = None
    nombres: Optional[str] = Field(None, max_length=120)
    apellidos: Optional[str] = Field(None, max_length=120)
    rut: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=50)
    razon_social: Optional[str] = Field(None, max_length=200)
    giro: Optional[str] = Field(None, max_length=200)
    direccion_contacto: Optional[str] = None


class PersonRead(PersonBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
