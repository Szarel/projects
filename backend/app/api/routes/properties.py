from datetime import date
from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.session import get_session
from app.models.contract import ContractStatus, LeaseContract
from app.models.document import Document
from app.models.person import Person
from app.models.property import Property
from app.models.property_state import PropertyStateHistory
from app.models.charge import Charge, PaymentDetail
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> list[PropertyRead]:
    result = await session.execute(select(Property).order_by(Property.created_at.desc()))
    rows: Sequence[Property] = result.scalars().all()
    return list(rows)


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR)),
) -> PropertyRead:
    prop = Property(
        codigo=payload.codigo,
        direccion_linea1=payload.direccion_linea1,
        comuna=payload.comuna,
        region=payload.region,
        tipo=payload.tipo,
        estado_actual=payload.estado_actual,
        valor_arriendo=payload.valor_arriendo,
        valor_venta=payload.valor_venta,
        fecha_publicacion=payload.fecha_publicacion,
    )
    if payload.lat is not None and payload.lon is not None:
        prop.set_point(payload.lat, payload.lon)

    session.add(prop)
    await session.commit()
    await session.refresh(prop)
    return prop


@router.get("/geojson")
async def properties_geojson(
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> dict:
    props_result = await session.execute(
        select(Property).where(Property.lat.is_not(None), Property.lon.is_not(None))
    )
    props: list[Property] = list(props_result.scalars().all())

    if not props:
        return {"type": "FeatureCollection", "features": []}

    prop_ids = [p.id for p in props]
    arr_alias = aliased(Person)
    contracts_result = await session.execute(
        select(LeaseContract, arr_alias)
        .join(arr_alias, LeaseContract.arrendatario_id == arr_alias.id)
        .where(
            LeaseContract.propiedad_id.in_(prop_ids),
            LeaseContract.estado == ContractStatus.VIGENTE,
        )
    )

    latest_contract_by_prop: dict[UUID, tuple[LeaseContract, Person]] = {}
    for contract, arrendatario in contracts_result:
        prev = latest_contract_by_prop.get(contract.propiedad_id)
        if prev is None or contract.fecha_inicio > prev[0].fecha_inicio:
            latest_contract_by_prop[contract.propiedad_id] = (contract, arrendatario)

    def next_payment_day(dia_pago: int | None) -> date | None:
        if not dia_pago:
            return None
        today = date.today()
        try:
            candidate = date(today.year, today.month, dia_pago)
        except ValueError:
            return None
        if candidate < today:
            month = today.month + 1
            year = today.year + (1 if month > 12 else 0)
            month = 1 if month > 12 else month
            try:
                candidate = date(year, month, dia_pago)
            except ValueError:
                return None
        return candidate

    features: list[dict] = []
    for prop in props:
        contract_info = latest_contract_by_prop.get(prop.id)
        arr_name = None
        next_cobranza = None
        fecha_fin = None
        if contract_info:
            contract, arr = contract_info
            arr_name = " ".join(filter(None, [arr.nombres, arr.apellidos]))
            fecha_fin = contract.fecha_fin
            next_cobranza = next_payment_day(contract.dia_pago)

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(prop.lon), float(prop.lat)],
                },
                "properties": {
                    "id": str(prop.id),
                    "codigo": prop.codigo,
                    "direccion": prop.direccion_linea1,
                    "estado": prop.estado_actual,
                    "tipo": prop.tipo,
                    "comuna": prop.comuna,
                    "region": prop.region,
                    "valor_arriendo": float(prop.valor_arriendo) if prop.valor_arriendo else None,
                    "valor_venta": float(prop.valor_venta) if prop.valor_venta else None,
                    "arrendatario": arr_name,
                    "fecha_fin_contrato": fecha_fin,
                    "proxima_cobranza": next_cobranza,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


async def _get_property_or_404(property_id: UUID, session: AsyncSession) -> Property:
    prop = await session.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return prop


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PropertyRead:
    prop = await _get_property_or_404(property_id, session)
    return prop


@router.get("/{property_id}/full")
async def get_property_full(
    property_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    prop = await _get_property_or_404(property_id, session)

    history_result = await session.execute(
        select(PropertyStateHistory)
        .where(PropertyStateHistory.propiedad_id == property_id)
        .order_by(PropertyStateHistory.fecha_inicio.desc())
    )
    history = [
        {
            "estado": h.estado,
            "motivo": h.motivo,
            "fecha_inicio": h.fecha_inicio,
            "fecha_fin": h.fecha_fin,
            "actor_id": h.actor_id,
        }
        for h in history_result.scalars().all()
    ]

    arr_alias = aliased(Person)
    owner_alias = aliased(Person)
    contracts_result = await session.execute(
        select(LeaseContract, arr_alias, owner_alias)
        .join(arr_alias, LeaseContract.arrendatario_id == arr_alias.id)
        .join(owner_alias, LeaseContract.propietario_id == owner_alias.id)
        .where(LeaseContract.propiedad_id == property_id)
        .order_by(LeaseContract.fecha_inicio.desc())
    )

    contracts: list[dict] = []
    current_contract: dict | None = None
    contract_ids: list[UUID] = []
    for contract, arr, owner in contracts_result:
        contract_ids.append(contract.id)
        payload = {
            "id": contract.id,
            "estado": contract.estado,
            "fecha_inicio": contract.fecha_inicio,
            "fecha_fin": contract.fecha_fin,
            "renta_mensual": float(contract.renta_mensual),
            "moneda": contract.moneda,
            "dia_pago": contract.dia_pago,
            "reajuste_tipo": contract.reajuste_tipo,
            "reajuste_periodo_meses": contract.reajuste_periodo_meses,
            "arrendatario": {
                "id": arr.id,
                "nombre": " ".join(filter(None, [arr.nombres, arr.apellidos])),
                "rut": arr.rut,
                "email": arr.email,
                "telefono": arr.telefono,
            },
            "propietario": {
                "id": owner.id,
                "nombre": " ".join(filter(None, [owner.nombres, owner.apellidos])),
                "rut": owner.rut,
                "email": owner.email,
                "telefono": owner.telefono,
            },
            "notas": contract.notas,
            "created_at": contract.created_at,
        }
        contracts.append(payload)
        if contract.estado == ContractStatus.VIGENTE and current_contract is None:
            current_contract = payload

    docs_result = await session.execute(
        select(Document)
        .where(
            Document.entidad_tipo == "propiedad",
            Document.entidad_id == property_id,
            Document.activo.is_(True),
        )
        .order_by(Document.created_at.desc())
    )
    documents = [
        {
            "id": d.id,
            "categoria": d.categoria,
            "filename": d.filename,
            "version": d.version,
            "created_at": d.created_at,
            "activo": d.activo,
        }
        for d in docs_result.scalars().all()
    ]

    charges: list[dict] = []
    if contract_ids:
        charges_result = await session.execute(
            select(Charge).where(Charge.contrato_id.in_(contract_ids)).order_by(Charge.fecha_vencimiento.desc())
        )
        charge_ids: list[UUID] = []
        charges_raw = list(charges_result.scalars().all())
        charge_ids = [c.id for c in charges_raw]

        payments_map: dict[UUID, list[dict]] = {}
        if charge_ids:
            payments_result = await session.execute(
                select(PaymentDetail).where(PaymentDetail.cobranza_id.in_(charge_ids))
            )
            for pay in payments_result.scalars().all():
                payments_map.setdefault(pay.cobranza_id, []).append(
                    {
                        "id": pay.id,
                        "monto_pagado": float(pay.monto_pagado),
                        "fecha_pago": pay.fecha_pago,
                        "medio_pago": pay.medio_pago,
                        "referencia": pay.referencia,
                    }
                )

        for charge in charges_raw:
            charges.append(
                {
                    "id": charge.id,
                    "periodo": charge.periodo,
                    "monto_original": float(charge.monto_original),
                    "monto_ajustado": float(charge.monto_ajustado) if charge.monto_ajustado else None,
                    "fecha_vencimiento": charge.fecha_vencimiento,
                    "estado": charge.estado,
                    "fecha_pago": charge.fecha_pago,
                    "pagos": payments_map.get(charge.id, []),
                }
            )

    property_payload = {
        "id": prop.id,
        "codigo": prop.codigo,
        "direccion_linea1": prop.direccion_linea1,
        "comuna": prop.comuna,
        "region": prop.region,
        "tipo": prop.tipo,
        "estado_actual": prop.estado_actual,
        "valor_arriendo": float(prop.valor_arriendo) if prop.valor_arriendo else None,
        "valor_venta": float(prop.valor_venta) if prop.valor_venta else None,
        "lat": float(prop.lat) if prop.lat else None,
        "lon": float(prop.lon) if prop.lon else None,
        "fecha_publicacion": prop.fecha_publicacion,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,
    }

    return {
        "property": property_payload,
        "current_contract": current_contract,
        "state_history": history,
        "contracts": contracts,
        "documents": documents,
        "charges": charges,
    }


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR)),
) -> PropertyRead:
    prop = await _get_property_or_404(property_id, session)
    data = payload.model_dump(exclude_unset=True)
    lat = data.pop("lat", None)
    lon = data.pop("lon", None)

    for field, value in data.items():
        setattr(prop, field, value)

    if lat is not None and lon is not None:
        prop.set_point(lat, lon)

    await session.commit()
    await session.refresh(prop)
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR)),
) -> None:
    prop = await _get_property_or_404(property_id, session)
    await session.delete(prop)
    await session.commit()
    return None
