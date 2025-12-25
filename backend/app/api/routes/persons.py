from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.person import Person
from app.schemas.person import PersonCreate, PersonRead, PersonUpdate
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonRead])
async def list_persons(
    session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)
) -> list[PersonRead]:
    result = await session.execute(select(Person).order_by(Person.created_at.desc()))
    rows: Sequence[Person] = result.scalars().all()
    return list(rows)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(
    payload: PersonCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR)),
) -> PersonRead:
    person = Person(**payload.model_dump())
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return person


async def _get_person_or_404(person_id: UUID, session: AsyncSession) -> Person:
    person = await session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(
    person_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PersonRead:
    person = await _get_person_or_404(person_id, session)
    return person


@router.patch("/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: UUID,
    payload: PersonUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CORREDOR)),
) -> PersonRead:
    person = await _get_person_or_404(person_id, session)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(person, field, value)
    await session.commit()
    await session.refresh(person)
    return person
