"""Custom SQLAlchemy types for cross-database support."""

import uuid
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-agnostic UUID.

    Uses PostgreSQL's native UUID type, and falls back to a 36-char string for SQLite.
    """

    impl = PG_UUID
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect is None:
            return String(36)
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect):  # type: ignore[override]
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value: Any, dialect):  # type: ignore[override]
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class GeoPoint(TypeDecorator):
    """Geographic point that degrades to text for SQLite."""

    impl = Geography
    cache_ok = True

    def __init__(
        self,
        geometry_type: str = "POINT",
        srid: int = 4326,
        spatial_index: bool = False,
        from_text: str = "ST_GeogFromText",
        name: str = "geography",
    ) -> None:
        super().__init__()
        self.geometry_type = geometry_type
        self.srid = srid
        self.spatial_index = spatial_index
        self.from_text = from_text
        self.name = name

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect is None:
            return String(255)
        if dialect.name == "postgresql":
            return dialect.type_descriptor(
                Geography(
                    geometry_type=self.geometry_type,
                    srid=self.srid,
                    spatial_index=self.spatial_index,
                    from_text=self.from_text,
                    name=self.name,
                )
            )
        return dialect.type_descriptor(String(255))

    def process_bind_param(self, value: Any, dialect):  # type: ignore[override]
        if dialect.name != "postgresql" and value is not None:
            return str(value)
        return value

    def process_result_value(self, value: Any, dialect):  # type: ignore[override]
        return value
