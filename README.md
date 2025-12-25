# SIGAP – Sistema Integral de Gestion y Administracion de Propiedades

Plataforma integral para corredora de propiedades en Santiago orientada a trazabilidad, automatizacion y escalabilidad SaaS.

## Estructura del repositorio
- docs/: documentacion funcional, modelo de datos, arquitectura, mapa y roadmap.
- backend/: esqueleto inicial FastAPI.
- frontend/: notas iniciales para React + Leaflet.
 - frontend/: SPA con Vite/React/Leaflet para mapa y tabla.
- prompt.md: requerimientos fuente provistos por negocio.

## Prerrequisitos
- Python 3.11+
- Node.js 18+
- PostgreSQL 15 + PostGIS 3

## Inicio rapido (backend)
1. Crear entorno: `python -m venv .venv` y activar.
2. Instalar deps: `pip install -r backend/requirements.txt`.
3. Levantar API: `uvicorn backend.app.main:app --reload`.

## Inicio rapido (frontend)
1. `cd frontend`
2. `npm install`
3. Copiar `.env.example` a `.env` y ajustar `VITE_API_URL` y opcional `VITE_API_TOKEN` (Bearer JWT).
4. Guardar el token en `localStorage.setItem("sigap_token", "<token>")` o en `VITE_API_TOKEN`.
5. `npm run dev`

## Estado
- Documentos base creados en docs/.
- API esqueleto disponible (health y placeholder de propiedades).
- Frontend pendiente de scaffolding (se hara con Vite + React + Leaflet/Mapbox).
