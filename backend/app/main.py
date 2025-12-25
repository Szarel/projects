from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(title="SIGAP API", version="0.1.0")

# CORS abierto para desarrollo; ajustar en produccion
cors_origins = settings.cors_origins_list
allow_credentials = "*" not in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Browsers reject Access-Control-Allow-Origin="*" together with
    # Access-Control-Allow-Credentials=true. If we allow all origins, disable
    # credentials.
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Endpoint basico para monitoreo."""
    return {"status": "ok"}


app.include_router(api_router)
