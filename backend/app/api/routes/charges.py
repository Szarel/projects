from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.charge import Charge, ChargeState, PaymentDetail
from app.models.contract import LeaseContract
from app.schemas.charge import ChargeCreate, ChargeRead, PaymentCreate, PaymentRead
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.services.ai_extract import extract_payment_from_image

router = APIRouter(prefix="/charges", tags=["charges"])


async def _get_contract_or_404(contract_id: UUID, session: AsyncSession) -> LeaseContract:
    contract = await session.get(LeaseContract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


async def _get_charge_or_404(charge_id: UUID, session: AsyncSession) -> Charge:
    charge = await session.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge not found")
    return charge


@router.get("", response_model=list[ChargeRead])
async def list_charges(
    contract_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ChargeRead]:
    stmt = select(Charge).order_by(Charge.fecha_vencimiento.desc())
    if contract_id:
        stmt = stmt.where(Charge.contrato_id == contract_id)
    result = await session.execute(stmt)
    rows: Sequence[Charge] = result.scalars().all()
    return list(rows)


@router.post("", response_model=ChargeRead, status_code=status.HTTP_201_CREATED)
async def create_charge(
    payload: ChargeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANZAS)),
) -> ChargeRead:
    await _get_contract_or_404(payload.contrato_id, session)
    charge = Charge(**payload.model_dump())
    session.add(charge)
    await session.commit()
    await session.refresh(charge)
    return charge


@router.post("/{charge_id}/pay", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def pay_charge(
    charge_id: UUID,
    payload: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANZAS)),
) -> PaymentRead:
    charge = await _get_charge_or_404(charge_id, session)

    payment = PaymentDetail(
        cobranza_id=charge.id,
        monto_pagado=payload.monto_pagado,
        fecha_pago=payload.fecha_pago or charge.fecha_vencimiento,
        medio_pago=payload.medio_pago,
        referencia=payload.referencia,
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
    await session.refresh(payment)
    return payment


@router.post("/{charge_id}/pay/ai", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def pay_charge_from_receipt(
    charge_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANZAS)),
) -> PaymentRead:
    charge = await _get_charge_or_404(charge_id, session)

    raw = await file.read()
    parsed = extract_payment_from_image(raw, file.content_type)
    if not parsed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo leer el comprobante")

    try:
        monto = Decimal(str(parsed.get("monto_pagado")))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El comprobante no indica un monto valido")

    fecha_pago_raw = parsed.get("fecha_pago")
    pay_date = charge.fecha_vencimiento
    if fecha_pago_raw:
        try:
            pay_date = datetime.fromisoformat(str(fecha_pago_raw)).date()
        except Exception:
            pay_date = charge.fecha_vencimiento

    payment = PaymentDetail(
        cobranza_id=charge.id,
        monto_pagado=monto,
        fecha_pago=pay_date,
        medio_pago=parsed.get("medio_pago"),
        referencia=parsed.get("referencia"),
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
    await session.refresh(payment)
    return payment
