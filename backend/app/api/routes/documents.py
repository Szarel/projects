import os
import re
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from PyPDF2 import PdfReader

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_session
from app.models.contract import AdjustmentType, ContractStatus, Currency, LeaseContract
from app.models.charge import Charge, ChargeState, PaymentDetail
from app.models.document import Document
from app.models.person import Person, PersonType
from app.models.property import Property, PropertyState
from app.models.property_state import PropertyStateHistory
from app.schemas.document import DocumentCreate, DocumentRead
from app.models.user import User, UserRole
from app.services.ai_extract import extract_contract_fields

router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_contract_pdf(raw: bytes) -> dict:
    """Best-effort extraction of key fields from a lease contract PDF."""
    try:
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return {}

    ai_data = extract_contract_fields(text)

    months = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }

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

    def _find_written_dates() -> list[date]:
        results: list[date] = []
        for m in re.finditer(r"(?i)(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de|del)\s+(\d{4})", text):
            try:
                day = int(m.group(1))
                month = months.get(m.group(2).lower())
                year = int(m.group(3))
                if month:
                    results.append(date(year, month, day))
            except Exception:
                continue
        return results

    def _pick_contract_dates() -> tuple[date | None, date | None]:
        specific_start = re.search(r"(?i)regir el d[ií]a\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", text)
        specific_end = re.search(r"(?i)terminar[aá]? el d[ií]a\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", text)
        start_date = None
        end_date = None
        if specific_start:
            try:
                start_date = date(
                    int(specific_start.group(3)),
                    months.get(specific_start.group(2).lower()) or 1,
                    int(specific_start.group(1)),
                )
            except Exception:
                start_date = None
        if specific_end:
            try:
                end_date = date(
                    int(specific_end.group(3)),
                    months.get(specific_end.group(2).lower()) or 1,
                    int(specific_end.group(1)),
                )
            except Exception:
                end_date = None

        written_dates = _find_written_dates()
        if not start_date or not end_date:
            if len(written_dates) >= 3:
                start_date = start_date or written_dates[1]
                end_date = end_date or written_dates[2]
            elif len(written_dates) >= 2:
                start_date = start_date or written_dates[0]
                end_date = end_date or written_dates[1]
            elif len(written_dates) == 1:
                start_date = start_date or written_dates[0]
        return start_date, end_date

    def _find_int(label: str) -> int | None:
        m = re.search(fr"(?i){label}[^0-9]*(\d{{1,2}})", text)
        return int(m.group(1)) if m else None

    def _find_pay_day() -> int | None:
        m = re.search(r"(?i)(\d{1,2})\s+primeros\s+d[ií]as\s+h[aá]biles", text)
        if m:
            return int(m.group(1))
        if re.search(r"(?i)cinco\s+primeros\s+d[ií]as\s+h[aá]biles", text):
            return 5
        return _find_int("dia de pago|día de pago")

    def _find_amount(label: str) -> Decimal | None:
        m = re.search(fr"(?i){label}[^0-9]*([0-9\.\,]+)", text)
        if not m:
            return None
        raw_amt = m.group(1).replace(".", "").replace(",", ".")
        try:
            return Decimal(raw_amt)
        except Exception:
            return None

    def _find_amounts_any() -> list[Decimal]:
        amounts: list[Decimal] = []
        for m in re.finditer(r"\$?\s*([0-9]{1,3}(?:[\.\,][0-9]{3})*(?:[\.,][0-9]+)?)", text):
            raw_amt = m.group(1).replace(".", "").replace(",", ".")
            try:
                amt = Decimal(raw_amt)
                amounts.append(amt)
            except Exception:
                continue
        return amounts

    def _pick_rent() -> Decimal | None:
        rent = _find_amount("renta mensual|canon|arriendo|renta de arrendamiento")
        if rent:
            return rent
        candidates = _find_amounts_any()
        if not candidates:
            return None
        # Heuristic: take the highest amount to avoid picking addresses or numbers like "611".
        return max(candidates)

    def _find_rut_near(label: str) -> tuple[str | None, str | None]:
        # Returns (rut, name_snippet)
        m = re.search(fr"(?is){label}[^\n]{{0,160}}?rut\s*([0-9\.\-kK]+)", text)
        if not m:
            return None, None
        rut = m.group(1)
        before = text[: m.start(1)]
        snippet = before[-80:]
        return rut, snippet

    def _find_ruts_generic() -> list[tuple[str, str | None]]:
        ruts: list[tuple[str, str | None]] = []
        for m in re.finditer(r"(\d{1,2}\.?\d{3}\.?\d{3}-[0-9Kk])", text):
            rut = m.group(1)
            before = text[: m.start(1)]
            snippet = before[-80:]
            ruts.append((rut, snippet))
        return ruts

    def _extract_name(snippet: str | None) -> str | None:
        if not snippet:
            return None
        parts = re.findall(r"(?i)(don|doña)?\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s']{5,80})", snippet)
        if parts:
            # Take the last candidate, strip markers like don/doña
            name = parts[-1][1].strip()
            return " ".join(name.split())
        return None

    start_written, end_written = _pick_contract_dates()

    arr_rut_raw, arr_snippet = _find_rut_near("arrendatario|arrendadora")
    prop_rut_raw, prop_snippet = _find_rut_near("arrendador|propietario")

    if not arr_rut_raw or not prop_rut_raw:
        generic_ruts = _find_ruts_generic()
        if generic_ruts:
            if not prop_rut_raw and len(generic_ruts) >= 1:
                prop_rut_raw, prop_snippet = generic_ruts[0]
            if not arr_rut_raw and len(generic_ruts) >= 2:
                arr_rut_raw, arr_snippet = generic_ruts[1]

    arr_name = _extract_name(arr_snippet)
    prop_name = _extract_name(prop_snippet)

    return {
        "fecha_inicio": ai_data.get("fecha_inicio")
        or start_written
        or _find_date("inicio"),
        "fecha_fin": ai_data.get("fecha_fin")
        or end_written
        or _find_date("termino|término|fin"),
        "dia_pago": ai_data.get("dia_pago")
        or _find_pay_day()
        or 5,
        "renta_mensual": ai_data.get("renta_mensual") or _pick_rent(),
        "arrendatario_rut": ai_data.get("arrendatario_rut") or arr_rut_raw,
        "propietario_rut": ai_data.get("propietario_rut") or prop_rut_raw,
        "arrendatario_nombre": ai_data.get("arrendatario_nombre") or arr_name,
        "propietario_nombre": ai_data.get("propietario_nombre") or prop_name,
    }


def _normalize_rut(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9kK]", "", value)
    if not cleaned:
        return None
    if cleaned[-1] in {"k", "K"}:
        return cleaned[:-1] + "K"
    return cleaned


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
    def _coerce_date(value: Any, default: date | None = None) -> date | None:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except Exception:
                pass
        return default

    def _coerce_int(value: Any, default: int | None = None) -> int | None:
        try:
            return int(value)
        except Exception:
            return default

    def _coerce_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
        try:
            return Decimal(str(value))
        except Exception:
            return default

    start_date = _coerce_date(parsed.get("fecha_inicio"), date.today())
    end_date = _coerce_date(parsed.get("fecha_fin"), (start_date or date.today()) + timedelta(days=365))
    pay_day: int | None = _coerce_int(parsed.get("dia_pago"), 5)
    renta: Decimal = _coerce_decimal(parsed.get("renta_mensual"), prop.valor_arriendo or Decimal("0"))

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

        async def _resolve_person(raw: str, role: str, fallback_rut: str | None, fallback_name: str | None) -> uuid.UUID:
            """Accept UUID or RUT; if not found, creates a Person for tests."""
            candidates: list[str] = []
            if raw:
                candidates.append(raw.strip())
            if fallback_rut:
                candidates.append(fallback_rut)

            normalized_candidates = [_normalize_rut(c) for c in candidates if c]

            # 1) Try UUID lookup or use provided UUID to create
            for cand in candidates:
                try:
                    cand_uuid = uuid.UUID(cand)
                except Exception:
                    cand_uuid = None
                if cand_uuid:
                    obj = await session.get(Person, cand_uuid)
                    if obj:
                        return obj.id
                    # create with this UUID
                    new_person = Person(
                        id=cand_uuid,
                        tipo=PersonType.ARRENDATARIO if role.lower().startswith("tenant") else PersonType.PROPIETARIO,
                        nombres=fallback_name or f"{role} auto",
                        apellidos=None,
                        rut=_normalize_rut(fallback_rut) or _normalize_rut(raw),
                    )
                    session.add(new_person)
                    await session.flush()
                    return new_person.id

            # 2) Try RUT lookup (normalized)
            for norm in normalized_candidates:
                if not norm:
                    continue
                result = await session.execute(select(Person).where(Person.rut.is_not(None)))
                persons = list(result.scalars().all())
                for person in persons:
                    stored_norm = _normalize_rut(person.rut)
                    if stored_norm and stored_norm == norm:
                        return person.id

            # 3) Create person with normalized rut or no rut
            new_person = Person(
                tipo=PersonType.ARRENDATARIO if role.lower().startswith("tenant") else PersonType.PROPIETARIO,
                nombres=fallback_name or f"{role} auto",
                apellidos=None,
                rut=_normalize_rut(fallback_rut) or _normalize_rut(raw),
            )
            session.add(new_person)
            await session.flush()
            return new_person.id

        parsed = _parse_contract_pdf(content)
        arr_id = await _resolve_person(arrendatario_id or "", "Tenant", parsed.get("arrendatario_rut"), parsed.get("arrendatario_nombre"))
        prop_id = await _resolve_person(propietario_id or "", "Owner", parsed.get("propietario_rut"), parsed.get("propietario_nombre"))

        await _attach_contract_from_pdf(
            session=session,
            property_id=entity_uuid,
            arrendatario_id=arr_id,
            propietario_id=prop_id,
            parsed=parsed,
            current_user_id=current_user.id,
        )

    if entidad_tipo == "propiedad" and categoria == "recibo":
        parsed = extract_payment_from_image(content, file.content_type)
        prop = await session.get(Property, entity_uuid)

        if parsed and prop:
            try:
                amount = Decimal(str(parsed.get("monto_pagado")))
            except Exception:
                amount = None

            if amount:
                raw_date = parsed.get("fecha_pago")
                try:
                    pay_date = datetime.fromisoformat(str(raw_date)).date() if raw_date else date.today()
                except Exception:
                    pay_date = date.today()

                medio = parsed.get("medio_pago")
                referencia = parsed.get("referencia")

                contract_q = await session.execute(
                    select(LeaseContract)
                    .where(LeaseContract.propiedad_id == entity_uuid, LeaseContract.estado == ContractStatus.VIGENTE)
                    .order_by(LeaseContract.fecha_inicio.desc())
                    .limit(1)
                )
                contract = contract_q.scalars().first()

                if contract:
                    periodo = date(pay_date.year, pay_date.month, 1)
                    charge_q = await session.execute(
                        select(Charge).where(Charge.contrato_id == contract.id, Charge.periodo == periodo).limit(1)
                    )
                    charge = charge_q.scalars().first()

                    if not charge:
                        charge = Charge(
                            contrato_id=contract.id,
                            periodo=periodo,
                            monto_original=amount,
                            monto_ajustado=None,
                            fecha_vencimiento=pay_date,
                            estado=ChargeState.PENDIENTE,
                        )
                        session.add(charge)
                        await session.flush()

                    payment = PaymentDetail(
                        cobranza_id=charge.id,
                        monto_pagado=amount,
                        fecha_pago=pay_date,
                        medio_pago=medio,
                        referencia=referencia,
                    )
                    session.add(payment)
                    await session.flush()

                    total_pagado_result = await session.execute(
                        select(func.coalesce(func.sum(PaymentDetail.monto_pagado), 0)).where(
                            PaymentDetail.cobranza_id == charge.id
                        )
                    )
                    total_pagado: Decimal = total_pagado_result.scalar() or Decimal("0")
                    monto_objetivo = charge.monto_ajustado or charge.monto_original

                    if total_pagado >= monto_objetivo:
                        charge.estado = ChargeState.PAGADO
                        charge.fecha_pago = payment.fecha_pago
                    elif total_pagado > 0:
                        charge.estado = ChargeState.PARCIAL
                    else:
                        charge.estado = ChargeState.PENDIENTE

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
