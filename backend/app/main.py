from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(title="SIGAP API", version="0.1.0")

# CORS abierto para desarrollo; ajustar en produccion
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Endpoint basico para monitoreo."""
    return {"status": "ok"}


app.include_router(api_router)
