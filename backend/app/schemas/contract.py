from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.contract import AdjustmentType, ContractStatus, Currency


class LeaseContractBase(BaseModel):
    propiedad_id: UUID
    arrendatario_id: UUID
    propietario_id: UUID
    fecha_inicio: date
    fecha_fin: date
    renta_mensual: Decimal
    moneda: Currency = Currency.CLP
    reajuste_tipo: AdjustmentType = AdjustmentType.NONE
    reajuste_periodo_meses: Optional[int] = None
    reajuste_factor_inicial: Optional[Decimal] = None
    dia_pago: Optional[int] = None
    garantia_meses: Optional[int] = None
    comision_pct: Optional[Decimal] = Field(None, description="Porcentaje de comision de la corredora")
    estado: ContractStatus = ContractStatus.BORRADOR
    notas: Optional[str] = None


class LeaseContractCreate(LeaseContractBase):
    pass


class LeaseContractUpdate(BaseModel):
    propiedad_id: Optional[UUID] = None
    arrendatario_id: Optional[UUID] = None
    propietario_id: Optional[UUID] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    renta_mensual: Optional[Decimal] = None
    moneda: Optional[Currency] = None
    reajuste_tipo: Optional[AdjustmentType] = None
    reajuste_periodo_meses: Optional[int] = None
    reajuste_factor_inicial: Optional[Decimal] = None
    dia_pago: Optional[int] = None
    garantia_meses: Optional[int] = None
    comision_pct: Optional[Decimal] = None
    estado: Optional[ContractStatus] = None
    notas: Optional[str] = None


class LeaseContractRead(LeaseContractBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
