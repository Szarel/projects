from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    entidad_tipo: str
    entidad_id: UUID
    categoria: str


class DocumentRead(DocumentCreate):
    id: UUID
    filename: str
    storage_path: str
    version: int
    created_by: UUID | None
    created_at: datetime
    activo: bool

    model_config = {"from_attributes": True}
