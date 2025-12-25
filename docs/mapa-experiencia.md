# Diseno de mapa interactivo

## Objetivo
Gemelo digital de la cartera inmobiliaria con estados en tiempo real y acceso rapido a ficha completa.

## Datos y capas
- Fuente: endpoint /propiedades.geojson y canal SSE/WebSocket para cambios de estado.
- Colores por estado: arrendada=green, disponible=yellow, vendida=blue, en_venta=lightblue, desocupada=red, mantencion=orange, litigio=purple, inactiva=gray.
- Capas: puntos por propiedad, cluster a nivel ciudad, heatmap de vacancia opcional.

## Interacciones
- Hover: direccion corta, estado, tipo, valor, proximo cobro.
- Click: abre panel lateral con ficha (datos basicos, historial, contratos, documentos, pagos, observaciones).
- Filtros rapidos: estado, tipo, comuna, rango de precio, fecha de vencimiento de contrato, corredor asignado.
- Buscador por direccion o codigo interno.
- Tiempo real: al cambiar estado/pago, actualizar color y popups.

## UX
- Panel derecho persistente con tabs (Overview, Contratos, Finanzas, Documentos, Historial).
- Control de leyenda de colores y filtro en mapa.
- Vista split: mapa + tabla de propiedades sincronizada.
- Modo mobile: mapa pantalla completa con drawer para ficha.

## Tecnico
- Leaflet con tiles publicos (OSM) o Mapbox si se agrega token.
- Debounce en filtros; cache local para pan/zoom.
- Usar geojson-vt si volumen grande; cluster client-side inicial.
