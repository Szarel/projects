import uuid
from enum import Enum

from geoalchemy2 import WKTElement
from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.types import GeoPoint, GUID
from app.db.session import Base


class PropertyState(str, Enum):
    ARRENDADA = "arrendada"
    DISPONIBLE = "disponible"
    VENDIDA = "vendida"
    EN_VENTA = "en_venta"
    DESOCUPADA = "desocupada"
    MANTENCION = "mantencion"
    LITIGIO = "litigio"
    INACTIVA = "inactiva"


class PropertyType(str, Enum):
    CASA = "casa"
    DEPARTAMENTO = "departamento"
    OFICINA = "oficina"
    LOCAL = "local"
    TERRENO = "terreno"


class Property(Base):
    __tablename__ = "propiedades"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(50), unique=True, nullable=False)
    direccion_linea1 = Column(Text, nullable=False)
    comuna = Column(String(80), nullable=False)
    region = Column(String(80), nullable=False)
    lat = Column(Numeric(9, 6), nullable=True)
    lon = Column(Numeric(9, 6), nullable=True)
    # Disable auto-created spatial index to manage it via migrations for cross-DB support
    latlon = Column(GeoPoint(spatial_index=False), nullable=True)
    tipo = Column(SAEnum(PropertyType, name="tipo_propiedad"), nullable=False)
    estado_actual = Column(SAEnum(PropertyState, name="estado_propiedad"), nullable=False)
    valor_arriendo = Column(Numeric(14, 2), nullable=True)
    valor_venta = Column(Numeric(14, 2), nullable=True)
    fecha_publicacion = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    contratos = relationship(
        "LeaseContract", back_populates="propiedad", cascade="all, delete-orphan"
    )

    def set_point(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon
        self.latlon = WKTElement(f"POINT({lon} {lat})", srid=4326)
