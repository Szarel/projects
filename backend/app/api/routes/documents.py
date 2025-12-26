import os
import re
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from PyPDF2 import PdfReader

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_session
from app.models.contract import AdjustmentType, ContractStatus, Currency, LeaseContract
from app.models.document import Document
from app.models.person import Person
from app.models.property import Property, PropertyState
from app.models.property_state import PropertyStateHistory
from app.schemas.document import DocumentCreate, DocumentRead
from app.models.user import User, UserRole

router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_contract_pdf(raw: bytes) -> dict:
    """Best-effort extraction of key fields from a lease contract PDF."""
    try:
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return {}

    def _find_date(label: str) -> date | None:
        m = re.search(fr"(?i){label}[^0-9]*(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})", text)
        if not m:
            return None
        raw_date = m.group(1)
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"):
            try:
                return datetime.strptime(raw_date, fmt).date()
            except Exception:
                continue
        return None

    def _find_int(label: str) -> int | None:
        m = re.search(fr"(?i){label}[^0-9]*(\d{{1,2}})", text)
        return int(m.group(1)) if m else None

    def _find_amount(label: str) -> Decimal | None:
        m = re.search(fr"(?i){label}[^0-9]*([0-9\.\,]+)", text)
        if not m:
            return None
        raw_amt = m.group(1).replace(".", "").replace(",", ".")
        try:
            return Decimal(raw_amt)
        except Exception:
            return None

    return {
        "fecha_inicio": _find_date("inicio"),
        "fecha_fin": _find_date("termino|término|fin"),
        "dia_pago": _find_int("dia de pago|día de pago"),
        "renta_mensual": _find_amount("renta mensual|canon|arriendo"),
    }


async def _attach_contract_from_pdf(
    *,
    session: AsyncSession,
    property_id: uuid.UUID,
    arrendatario_id: uuid.UUID,
    propietario_id: uuid.UUID,
    parsed: dict,
    current_user_id: uuid.UUID,
) -> None:
    prop = await session.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Validate parties exist
    for model, eid, message in (
        (Person, arrendatario_id, "Tenant not found"),
        (Person, propietario_id, "Owner not found"),
    ):
        obj = await session.get(model, eid)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    start_date: date = parsed.get("fecha_inicio") or date.today()
    end_date: date = parsed.get("fecha_fin") or (start_date + timedelta(days=365))
    pay_day: int | None = parsed.get("dia_pago") or 5
    renta: Decimal = parsed.get("renta_mensual") or (prop.valor_arriendo or Decimal("0"))

    contract = LeaseContract(
        propiedad_id=prop.id,
        arrendatario_id=arrendatario_id,
        propietario_id=propietario_id,
        fecha_inicio=start_date,
        fecha_fin=end_date,
        renta_mensual=renta,
        moneda=Currency.CLP,
        reajuste_tipo=AdjustmentType.NONE,
        dia_pago=pay_day,
        estado=ContractStatus.VIGENTE,
        notas="Autogenerado desde PDF de contrato",
    )

    prop.estado_actual = PropertyState.ARRENDADA
    if prop.valor_arriendo is None and renta:
        prop.valor_arriendo = renta

    history = PropertyStateHistory(
        propiedad_id=prop.id,
        estado=PropertyState.ARRENDADA,
        motivo="Contrato de arriendo cargado",
        fecha_inicio=date.today(),
        actor_id=current_user_id,
    )

    session.add(contract)
    session.add(history)


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
    stmt = stmt.where(Document.activo.is_(True))
    result = await session.execute(stmt.order_by(Document.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    entidad_tipo: str = Form(...),
    entidad_id: str = Form(...),
    categoria: str = Form(...),
    file: UploadFile = File(...),
    arrendatario_id: str | None = Form(None),
    propietario_id: str | None = Form(None),
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

    entity_uuid = uuid.UUID(entidad_id)
    document = Document(
        id=doc_id,
        entidad_tipo=entidad_tipo,
        entidad_id=entity_uuid,
        categoria=categoria,
        filename=file.filename,
        storage_path=str(storage_path),
        version=1,
        hash=None,
        created_by=current_user.id,
    )
    session.add(document)

    if entidad_tipo == "propiedad" and categoria == "contrato_arriendo":
        if not arrendatario_id or not propietario_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="arrendatario_id y propietario_id son requeridos para contratos de arriendo")

        async def _resolve_person(raw: str, role: str) -> uuid.UUID:
            """Accept UUID or RUT; returns person UUID or raises 404."""
            cleaned = raw.strip()
            try:
                return uuid.UUID(cleaned)
            except Exception:
                # Try lookup by RUT
                result = await session.execute(select(Person).where(Person.rut == cleaned))
                person = result.scalars().first()
                if not person:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{role} not found (usa UUID o RUT válido)")
                return person.id

        arr_id = await _resolve_person(arrendatario_id, "Tenant")
        prop_id = await _resolve_person(propietario_id, "Owner")

        parsed = _parse_contract_pdf(content)
        await _attach_contract_from_pdf(
            session=session,
            property_id=entity_uuid,
            arrendatario_id=arr_id,
            propietario_id=prop_id,
            parsed=parsed,
            current_user_id=current_user.id,
        )

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
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    path = Path(document.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="File missing; reemplace o cargue nuevamente")
    return FileResponse(path, filename=document.filename)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
):
    document = await session.get(Document, document_id)
    if not document:
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


@router.put("/{document_id}", response_model=DocumentRead)
async def replace_document(
    document_id: uuid.UUID,
    categoria: str | None = Form(None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
) -> DocumentRead:
    document = await session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    storage_root = Path(settings.storage_dir)
    storage_root.mkdir(parents=True, exist_ok=True)

    new_id = uuid.uuid4()
    filename = f"{new_id}_{file.filename}"
    storage_path = storage_root / filename

    content = await file.read()
    storage_path.write_bytes(content)

    document.filename = file.filename
    document.storage_path = str(storage_path)
    document.version = (document.version or 1) + 1
    document.activo = True
    if categoria:
        document.categoria = categoria

    await session.commit()
    await session.refresh(document)
    return document
