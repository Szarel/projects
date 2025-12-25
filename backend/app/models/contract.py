import uuid
from enum import Enum

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.types import GUID
from app.db.session import Base


class Currency(str, Enum):
    CLP = "CLP"
    UF = "UF"


class AdjustmentType(str, Enum):
    UF = "uf"
    IPC = "ipc"
    FIJO = "fijo"
    NONE = "none"


class ContractStatus(str, Enum):
    VIGENTE = "vigente"
    TERMINADO = "terminado"
    RESCILIADO = "resciliado"
    FIRMADO = "firmado"
    BORRADOR = "borrador"


class LeaseContract(Base):
    __tablename__ = "contratos_arriendo"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    propiedad_id = Column(GUID(), ForeignKey("propiedades.id", ondelete="CASCADE"), nullable=False)
    arrendatario_id = Column(GUID(), ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False)
    propietario_id = Column(GUID(), ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    renta_mensual = Column(Numeric(14, 2), nullable=False)
    moneda = Column(SAEnum(Currency, name="moneda"), nullable=False, default=Currency.CLP)
    reajuste_tipo = Column(SAEnum(AdjustmentType, name="reajuste_tipo"), nullable=False, default=AdjustmentType.NONE)
    reajuste_periodo_meses = Column(Integer, nullable=True)
    reajuste_factor_inicial = Column(Numeric(12, 6), nullable=True)
    dia_pago = Column(Integer, nullable=True)
    garantia_meses = Column(Integer, nullable=True)
    comision_pct = Column(Numeric(5, 2), nullable=True)
    estado = Column(SAEnum(ContractStatus, name="estado_contrato"), nullable=False, default=ContractStatus.BORRADOR)
    notas = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    propiedad = relationship("Property", back_populates="contratos")
