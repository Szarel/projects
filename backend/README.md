# Backend FastAPI (esqueleto)

## Configuracion rapida
1. Crear entorno virtual y activar.
2. `pip install -r requirements.txt`.
3. Copiar `.env.example` a `.env` y ajustar `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.
	- Para base auxiliar rapida (sin PostGIS): `DATABASE_URL=sqlite+aiosqlite:///./sigap_dev.db`
4. Si usas Postgres+PostGIS, crea la base apuntada por `DATABASE_URL`.
5. Generar migracion inicial: `alembic revision --autogenerate -m "init"` y luego `alembic upgrade head`.
6. Crear usuario via `/auth/signup` (rol admin recomendado) y obtener token con `/auth/login`.
7. `uvicorn backend.app.main:app --reload`.

## Estructura
- app/main.py: arranque de FastAPI y registro de routers.
- app/api/routes: endpoints (auth JWT, propiedades CRUD + GeoJSON, personas, contratos, cobranzas/pagos).
- app/api/routes/documents: listar/subir/descargar documentos (auth requerido; upload para admin/corredor/finanzas).
- app/models: SQLAlchemy (propiedad, persona, contrato, cobranza, pagos, documentos, historial de estados).
- app/schemas: Pydantic v2 para request/response.
- app/db: configuracion de motor async y Base ORM.
- app/services: logica de dominio (pendiente: cobranza recurrente, reajuste, documentos avanzados).
- alembic/: entorno de migraciones.

## Notas
- CORS controlado por `CORS_ORIGINS` en `.env`.
- Mantener configuracion via variables de entorno (.env) para DB, JWT, storage.
- Alembic listo para autogenerar migraciones; ajustar `alembic.ini` si cambia la URL.
- Los endpoints (excepto /health, /auth/login, /auth/signup) requieren Bearer token JWT.
- Upload de documentos guarda archivos en `STORAGE_DIR` (por defecto `storage/`) y registra metadata en BD.
- Roles: admin/corredor pueden crear/editar propiedades/personas; admin/corredor/finanzas contratos; admin/finanzas cobranzas/pagos; upload docs admin/corredor/finanzas; lecturas requieren token.
