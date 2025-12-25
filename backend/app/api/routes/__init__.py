from fastapi import APIRouter

from app.api.routes import auth, charges, contracts, persons, properties, documents

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(persons.router)
api_router.include_router(contracts.router)
api_router.include_router(charges.router)
api_router.include_router(documents.router)
