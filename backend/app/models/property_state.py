import uuid

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.sql import func

from app.core.types import GUID
from app.db.session import Base
from app.models.property import PropertyState


class PropertyStateHistory(Base):
    __tablename__ = "estados_propiedad_historial"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    propiedad_id = Column(GUID(), ForeignKey("propiedades.id", ondelete="CASCADE"), nullable=False)
    estado = Column(SAEnum(PropertyState, name="estado_propiedad_hist"), nullable=False)
    motivo = Column(String(300), nullable=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    actor_id = Column(GUID(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
