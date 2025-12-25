# Frontend (plan inicial)

Proxima implementacion con React + Vite + TypeScript + Leaflet.

## Objetivos de la primera entrega
- Layout base con rutas protegidas.
- Pagina de mapa con capas por estado y filtros rapidos.
- Tabla sincronizada de propiedades.
- Formularios basicos de propiedad/persona.
 - Login basico con JWT (token via backend /auth/login).

## Setup previsto
- `npm create vite@latest frontend -- --template react-ts`
- Instalar deps: react-router-dom, axios, leaflet, zustand/redux, tailwind o mantine (a definir), date-fns.
 - Este repo ya incluye Vite + React + Leaflet + axios.

## Integracion con API
- Base URL configurable via env.
- Servicios: auth, propiedades (incluye endpoint GeoJSON), contratos, cobranzas, documentos.
 - Guardar token en localStorage (`sigap_token`) o `VITE_API_TOKEN` para desarrollo.

## Consideraciones UX
- Colores consistentes con mapa.
- Modo mobile con drawer.
- Manejador de sesiones y expiracion de token.
