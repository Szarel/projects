import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.types import GUID
from app.db.session import Base


class ChargeState(str, Enum):
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    ATRASADO = "atrasado"
    PARCIAL = "parcial"
    CONDONADO = "condonado"


class Charge(Base):
    __tablename__ = "cobranzas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    contrato_id = Column(GUID(), ForeignKey("contratos_arriendo.id", ondelete="CASCADE"), nullable=False)
    periodo = Column(Date, nullable=False)
    monto_original = Column(Numeric(14, 2), nullable=False)
    monto_ajustado = Column(Numeric(14, 2), nullable=True)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(SAEnum(ChargeState, name="estado_cobranza"), nullable=False, default=ChargeState.PENDIENTE)
    mora_monto = Column(Numeric(14, 2), nullable=True)
    fecha_pago = Column(Date, nullable=True)
    medio_pago = Column(String(100), nullable=True)
    notas = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pagos = relationship("PaymentDetail", back_populates="cobranza", cascade="all, delete-orphan")


class PaymentDetail(Base):
    __tablename__ = "pagos_detalle"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    cobranza_id = Column(GUID(), ForeignKey("cobranzas.id", ondelete="CASCADE"), nullable=False)
    monto_pagado = Column(Numeric(14, 2), nullable=False)
    fecha_pago = Column(Date, nullable=False)
    medio_pago = Column(String(100), nullable=True)
    referencia = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cobranza = relationship("Charge", back_populates="pagos")
