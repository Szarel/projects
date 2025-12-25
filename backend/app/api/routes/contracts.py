from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.contract import LeaseContract
from app.models.property import Property
from app.models.person import Person
from app.schemas.contract import LeaseContractCreate, LeaseContractRead, LeaseContractUpdate
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole

router = APIRouter(prefix="/contracts", tags=["contracts"])


async def _assert_exists(session: AsyncSession, model, entity_id: UUID, not_found_msg: str) -> None:
    obj = await session.get(model, entity_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_msg)


@router.get("", response_model=list[LeaseContractRead])
async def list_contracts(
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> list[LeaseContractRead]:
    result = await session.execute(select(LeaseContract).order_by(LeaseContract.created_at.desc()))
    rows: Sequence[LeaseContract] = result.scalars().all()
    return list(rows)


@router.post("", response_model=LeaseContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: LeaseContractCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
) -> LeaseContractRead:
    await _assert_exists(session, Property, payload.propiedad_id, "Property not found")
    await _assert_exists(session, Person, payload.arrendatario_id, "Tenant not found")
    await _assert_exists(session, Person, payload.propietario_id, "Owner not found")

    contract = LeaseContract(**payload.model_dump())
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


async def _get_contract_or_404(contract_id: UUID, session: AsyncSession) -> LeaseContract:
    contract = await session.get(LeaseContract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


@router.get("/{contract_id}", response_model=LeaseContractRead)
async def get_contract(
    contract_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LeaseContractRead:
    contract = await _get_contract_or_404(contract_id, session)
    return contract


@router.patch("/{contract_id}", response_model=LeaseContractRead)
async def update_contract(
    contract_id: UUID,
    payload: LeaseContractUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR, UserRole.FINANZAS)),
) -> LeaseContractRead:
    contract = await _get_contract_or_404(contract_id, session)

    data = payload.model_dump(exclude_unset=True)

    if "propiedad_id" in data:
        await _assert_exists(session, Property, data["propiedad_id"], "Property not found")
    if "arrendatario_id" in data:
        await _assert_exists(session, Person, data["arrendatario_id"], "Tenant not found")
    if "propietario_id" in data:
        await _assert_exists(session, Person, data["propietario_id"], "Owner not found")

    for field, value in data.items():
        setattr(contract, field, value)

    await session.commit()
    await session.refresh(contract)
    return contract
