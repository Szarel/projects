from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.charge import ChargeState


class ChargeBase(BaseModel):
    contrato_id: UUID
    periodo: date
    monto_original: Decimal
    monto_ajustado: Optional[Decimal] = None
    fecha_vencimiento: date
    estado: ChargeState = ChargeState.PENDIENTE
    mora_monto: Optional[Decimal] = None
    fecha_pago: Optional[date] = None
    medio_pago: Optional[str] = None
    notas: Optional[str] = None


class ChargeCreate(ChargeBase):
    pass


class ChargeRead(ChargeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    monto_pagado: Decimal
    fecha_pago: Optional[date] = None
    medio_pago: Optional[str] = None
    referencia: Optional[str] = None


class PaymentRead(PaymentCreate):
    id: UUID
    cobranza_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
