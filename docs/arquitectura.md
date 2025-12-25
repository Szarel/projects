# Arquitectura tecnica propuesta

## Stack
- Backend API: FastAPI (Python), uvicorn, SQLAlchemy/async + Alembic.
- DB: PostgreSQL + PostGIS.
- Storage documental: S3 compatible (MinIO/local en dev).
- Frontend: React + Vite + TypeScript + Leaflet (o Mapbox) + Zustand/Redux para estado.
- Jobs y alertas: Celery/RQ + Redis para tareas programadas (recordatorios, reajustes, conciliacion).
- Auth: OAuth2 password + JWT (roles: admin, corredor, finanzas, lectura).
- Observabilidad: logging estructurado + health + métricas basicas (prometheus_ready para futuro).

## Modulos backend
- Core dominio: propiedades, personas, contratos, cobranzas, documentos, estados.
- Servicios
  - Geocoding/normalizacion de direccion (API externa o stub).
  - Motor de cobranza y reajuste.
  - Clasificacion de documentos (modelo IA laterable; placeholder inicial).
  - Notificaciones (email/WhatsApp gateway abstraccion).
- API REST
  - /health
  - /auth (login, refresh)
  - /propiedades (CRUD + geojson feed)
  - /contratos (CRUD + recalculo)
  - /cobranzas (listar, marcar pago, conciliacion parcial)
  - /documentos (upload, versionado)
  - /mapa/stream (SSE/WebSocket para cambios en estados)

## Frontend
- SPA con rutas protegidas (React Router).
- Layout: dashboard, mapa, propiedades, contratos, cobranza, documentos, mantencion.
- Estado global para usuario, filtros del mapa, cache de propiedades.
- Mapa: capas por estado con colores y cluster.

## Integracion y despliegue
- Desarrollo: docker-compose (pendiente), usa Postgres, MinIO, Redis.
- Despliegue: contenedores; API y frontend como servicios; DB gestionada.
- CI sugerido: lint + tests + checks de migraciones.

## Seguridad y cumplimiento
- Roles y permisos a nivel de endpoint y filtro de datos (multiempresa futura).
- Auditoria en BD para cambios de entidad.
- Versionado de documentos y hashes.
- Backup de DB y storage.
