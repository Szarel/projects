# Analisis funcional SIGAP

## Vision
Centralizar la operacion inmobiliaria (arriendo, venta, mantencion) con trazabilidad total, datos georreferenciados y flujos auditables.

## Actores y roles
- Administrador: configura catalogos, usuarios, permisos, auditoria.
- Corredor: gestiona propiedades, publica estados, registra visitas y contratos.
- Finanzas: maneja cobranza, pagos, reajustes, reportes.
- Propietario (portal futuro): consulta estado, documentos, pagos.
- Lectura/auditor: acceso de solo lectura y reportes.

## Objetos clave
- Propiedad: direccion normalizada, coordenadas, tipo, estado actual e historial, gastos, observaciones, fotos/documentos.
- Persona: datos de arrendatario, propietario, corredor, proveedor. Soporta multiples roles.
- Contrato de arriendo/venta: vigencia, montos, reajustes, garantias, comisiones.
- Pago y cobranza: programacion mensual, estado pagado/pendiente/atrasado/parcial, recargos, recibos.
- Documentos: contratos, escrituras, inventarios, anexos, comprobantes; versionados y auditados.
- Incidentes/mantenciones: tickets asociados a propiedad con costos y SLA.

## Flujos principales
1) Alta de propiedad -> geocodificacion -> asignar corredor -> estado inicial.
2) Publicacion y arriendo -> evaluacion arrendatario -> contrato -> programacion de cobros -> cobranza automatizada.
3) Venta -> promesa -> escritura -> cierre -> cambio de estado a vendida.
4) Cobranza recurrente -> generacion de boletas/facturas -> registro de pagos -> conciliacion -> reportes a propietario.
5) Reajuste de renta (UF/IPC/fijo) -> calculo -> notificacion -> actualizacion de cobranza.
6) Gestion documental -> carga, clasificacion, versionado -> timeline por propiedad/persona/contrato.
7) Mapa interactivo -> ver estado portfolio en tiempo real, filtros por estado/tipo/comuna.

## Reglas y validaciones
- Cada cambio de estado de propiedad debe registrar actor, motivo y timestamp.
- No se pueden solapar contratos activos de arriendo en una misma propiedad.
- RUT/RUN validado cuando aplique; unicidad por persona.
- Reajustes aplican en ciclos definidos (ej. cada 12 meses); se debe conservar historico de factores.
- Documentos deben registrar hash y version; no se permite borrar fisicamente (solo desactivar).
- Cobranza genera recordatorios automaticos y marcas de atraso; mora calculada por regla configurable.

## Alertas criticas
- Vencimiento de contrato (T-90, T-60, T-30, T-7, T-1).
- Pago atrasado y promesa de pago vencida.
- Garantia por expirar o insuficiente.
- Propiedad en litigio o mantencion prolongada.

## Indicadores iniciales
- Ocupacion (%) por tipo y comuna.
- Rotacion y tiempo promedio de vacancia.
- Mora y recupero por periodo.
- Rentabilidad bruta por propiedad.
- Tickets de mantencion abiertos y SLA.
