from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.property import PropertyState, PropertyType


class PropertyBase(BaseModel):
    codigo: str = Field(..., max_length=50)
    direccion_linea1: str
    comuna: str
    region: str
    tipo: PropertyType
    estado_actual: PropertyState
    valor_arriendo: Optional[Decimal] = None
    valor_venta: Optional[Decimal] = None
    fecha_publicacion: Optional[date] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=50)
    direccion_linea1: Optional[str] = None
    comuna: Optional[str] = None
    region: Optional[str] = None
    tipo: Optional[PropertyType] = None
    estado_actual: Optional[PropertyState] = None
    valor_arriendo: Optional[Decimal] = None
    valor_venta: Optional[Decimal] = None
    fecha_publicacion: Optional[date] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class PropertyRead(PropertyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
