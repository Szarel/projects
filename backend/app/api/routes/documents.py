import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_session
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentRead
from app.models.user import User, UserRole

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    entidad_tipo: str | None = None,
    entidad_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    stmt = select(Document)
    if entidad_tipo:
        stmt = stmt.where(Document.entidad_tipo == entidad_tipo)
    if entidad_id:
        stmt = stmt.where(Document.entidad_id == uuid.UUID(entidad_id))
    result = await session.execute(stmt.order_by(Document.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    entidad_tipo: str = Form(...),
    entidad_id: str = Form(...),
    categoria: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
) -> DocumentRead:
    storage_root = Path(settings.storage_dir)
    storage_root.mkdir(parents=True, exist_ok=True)

    doc_id = uuid.uuid4()
    filename = f"{doc_id}_{file.filename}"
    storage_path = storage_root / filename

    content = await file.read()
    storage_path.write_bytes(content)

    document = Document(
        id=doc_id,
        entidad_tipo=entidad_tipo,
        entidad_id=uuid.UUID(entidad_id),
        categoria=categoria,
        filename=file.filename,
        storage_path=str(storage_path),
        version=1,
        hash=None,
        created_by=current_user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    document = await session.get(Document, document_id)
    if not document or not document.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    path = Path(document.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="File missing on storage")
    return FileResponse(path, filename=document.filename)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
):
    document = await session.get(Document, document_id)
    if not document or not document.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document.activo = False
    await session.commit()

    # Best-effort: remove file from storage if exists.
    try:
        path = Path(document.storage_path)
        if path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        # Do not fail deletion if file removal fails.
        pass

    return None
