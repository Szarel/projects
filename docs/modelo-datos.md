# Modelo de datos (propuesta PostgreSQL + PostGIS)

## Principales tablas
- propiedades
  - id uuid pk
  - codigo text unique
  - direccion_linea1 text
  - comuna text
  - region text
  - latlon geometry(Point, 4326)
  - tipo (casa, departamento, oficina, local, terreno)
  - estado_actual (arrendada, disponible, vendida, en_venta, desocupada, mantencion, litigio, inactiva)
  - valor_arriendo numeric
  - valor_venta numeric
  - fecha_publicacion date
  - created_at, updated_at
  - fk corredor_id (usuario)
  - indices: gist(latlon), idx_estado_tipo, idx_comuna

- personas
  - id uuid pk
  - tipo (propietario, arrendatario, corredor, proveedor)
  - nombres, apellidos
  - rut text unique null
  - email, telefono
  - razon_social, giro (para empresas)
  - direccion_contacto
  - created_at, updated_at

- propiedad_persona_roles
  - id uuid pk
  - propiedad_id fk
  - persona_id fk
  - rol (dueno, arrendatario_actual, corredor, contacto_visita)
  - vigente_desde, vigente_hasta

- contratos_arriendo
  - id uuid pk
  - propiedad_id fk
  - arrendatario_id fk personas
  - propietario_id fk personas
  - fecha_inicio, fecha_fin
  - renta_mensual numeric
  - moneda (CLP, UF)
  - reajuste_tipo (uf, ipc, fijo, none)
  - reajuste_periodo_meses int
  - reajuste_factor_inicial numeric
  - dia_pago int
  - garantia_meses int
  - comision_pct numeric
  - estado (vigente, terminado, resciliado, firmado, borrador)
  - created_at, updated_at

- cobranzas
  - id uuid pk
  - contrato_id fk
  - periodo date (ej 2024-01-01)
  - monto_original numeric
  - monto_ajustado numeric
  - fecha_vencimiento date
  - estado (pendiente, pagado, atrasado, parcial, condonado)
  - mora_monto numeric
  - fecha_pago date null
  - medio_pago text
  - recibo_doc_id fk documentos null
  - notas text

- pagos_detalle
  - id uuid pk
  - cobranza_id fk
  - monto_pagado numeric
  - fecha_pago date
  - medio_pago text
  - referencia text

- reajustes
  - id uuid pk
  - contrato_id fk
  - periodo_inicio date
  - periodo_fin date
  - factor numeric
  - origen (UF, IPC, manual)
  - detalle jsonb
  - aplicado_en_cobranza boolean

- documentos
  - id uuid pk
  - entidad_tipo (propiedad, persona, contrato, cobranza, mantencion)
  - entidad_id uuid
  - categoria (contrato_arriendo, promesa, escritura, inventario, liquidacion, excel_historico, recibo, factura)
  - filename text
  - storage_path text
  - version int
  - hash sha256 text
  - metadata jsonb (ocr_tags, rut_detectado, etc.)
  - created_by uuid
  - created_at
  - activo boolean default true

- estados_propiedad_historial
  - id uuid pk
  - propiedad_id fk
  - estado
  - motivo text
  - fecha_inicio, fecha_fin
  - actor_id uuid

- gastos
  - id uuid pk
  - propiedad_id fk
  - contrato_id fk null
  - tipo (mantencion, contribuciones, seguro, admin, servicio)
  - descripcion text
  - monto numeric
  - moneda
  - fecha date
  - reembolsable boolean
  - factura_doc_id fk documentos null

- tickets_mantencion
  - id uuid pk
  - propiedad_id fk
  - titulo, descripcion
  - estado (abierto, en_progreso, en_espera, resuelto, cerrado)
  - prioridad (baja, media, alta, critica)
  - costo_estimado numeric
  - costo_real numeric
  - proveedor_id fk personas
  - created_at, updated_at, closed_at

- auditoria
  - id bigserial pk
  - actor_id uuid
  - accion text
  - entidad_tipo text
  - entidad_id uuid
  - diff jsonb
  - created_at timestamptz default now()

## Relaciones clave
- propiedad 1:N contratos_arriendo.
- contrato_arriendo 1:N cobranzas.
- cobranza 1:N pagos_detalle.
- propiedad N:M personas via propiedad_persona_roles.
- documentos asociados a cualquier entidad via (entidad_tipo, entidad_id).
- estados_propiedad_historial garantiza trazabilidad de cada cambio.

## Consideraciones
- Usar enums en BD para estado_propiedad, estado_cobranza, tipo_propiedad, roles.
- PostGIS para consultas geograficas y filtros por zona.
- JSONB para metadata de documentos y calculos de reajuste.
- Particionar cobranzas por ano para escala futura si el volumen crece.
