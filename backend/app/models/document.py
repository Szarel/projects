import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.types import GUID
from app.db.session import Base


class DocumentEntity(str, Enum):
    PROPIEDAD = "propiedad"
    PERSONA = "persona"
    CONTRATO = "contrato"
    COBRANZA = "cobranza"
    MANTENCION = "mantencion"


class DocumentCategory(str, Enum):
    CONTRATO_ARRIENDO = "contrato_arriendo"
    PROMESA = "promesa"
    ESCRITURA = "escritura"
    INVENTARIO = "inventario"
    LIQUIDACION = "liquidacion"
    EXCEL_HISTORICO = "excel_historico"
    RECIBO = "recibo"
    FACTURA = "factura"


class Document(Base):
    __tablename__ = "documentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    entidad_tipo = Column(String(50), nullable=False)
    entidad_id = Column(GUID(), nullable=False)
    categoria = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    hash = Column(String(128), nullable=True)
    metadata_json = Column(String(2000), nullable=True)
    created_by = Column(GUID(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
