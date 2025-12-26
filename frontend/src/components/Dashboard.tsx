import { ReactNode, useMemo, useState } from "react";
import MapView from "./MapView";
import type { Property } from "../api";

type DashboardProps = {
  properties: Property[];
  fullProperties: Property[];
  geojson: any;
  onSelectProperty: (id: string) => void;
  onDeleteProperty: (id: string) => void;
  filters: { estado: string; tipo: string; comuna: string };
  onChangeFilters: (f: { estado: string; tipo: string; comuna: string }) => void;
  alertsData: { vencidos: number; porVencer: number; sinContrato: number; cobranzaAtrasada: number; docsIncompletos: number };
  paymentsSummary: { monthTotal: number; monthCount: number; last: any };
  showFilters: boolean;
};

type CardId =
  | "map"
  | "list"
  | "byStatus"
  | "byType"
  | "byComuna"
  | "values"
  | "published";

function groupCount(items: string[]): Array<{ key: string; value: number }> {
  const map = new Map<string, number>();
  for (const item of items) {
    const key = (item || "").trim() || "(sin dato)";
    map.set(key, (map.get(key) || 0) + 1);
  }
  return Array.from(map.entries())
    .map(([key, value]) => ({ key, value }))
    .sort((a, b) => b.value - a.value);
}

function formatMoney(n: number): string {
  try {
    return new Intl.NumberFormat("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `$${Math.round(n)}`;
  }
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="dash-stat-row">
      <span className="dash-stat-label">{label}</span>
      <span className="dash-stat-value">{value}</span>
    </div>
  );
}

function BarChart({
  title,
  data,
  maxBars = 8,
}: {
  title: string;
  data: Array<{ key: string; value: number }>;
  maxBars?: number;
}) {
  const sliced = data.slice(0, maxBars);
  const max = Math.max(1, ...sliced.map((d) => d.value));

  return (
    <div className="dash-chart">
      <div className="dash-card-title">{title}</div>
      <div className="dash-bars">
        {sliced.map((d) => (
          <div key={d.key} className="dash-bar-row">
            <div className="dash-bar-label" title={d.key}>
              {d.key}
            </div>
            <div className="dash-bar-track">
              <div
                className="dash-bar-fill"
                style={{ width: `${Math.round((d.value / max) * 100)}%` }}
              />
            </div>
            <div className="dash-bar-value">{d.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LineChart({
  title,
  points,
}: {
  title: string;
  points: Array<{ xLabel: string; y: number }>;
}) {
  const width = 360;
  const height = 180;
  const padding = 24;
  const maxY = Math.max(1, ...points.map((p) => p.y));

  const coords = points.map((p, i) => {
    const x = padding + (i * (width - padding * 2)) / Math.max(1, points.length - 1);
    const yPx = height - padding - (p.y * (height - padding * 2)) / maxY;
    return { x, yPx, xLabel: p.xLabel, value: p.y };
  });

  const d = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.yPx.toFixed(1)}`)
    .join(" ");

  return (
    <div className="dash-chart">
      <div className="dash-card-title">{title}</div>
      <svg className="dash-svg" viewBox={`0 0 ${width} ${height}`} role="img">
        <path className="dash-line" d={d} />
        {coords.map((c) => (
          <circle key={c.xLabel} className="dash-dot" cx={c.x} cy={c.yPx} r={3.5} />
        ))}
        <text className="dash-axis" x={padding} y={height - 6}>
          {points[0]?.xLabel ?? ""}
        </text>
        <text className="dash-axis" x={width - padding} y={height - 6} textAnchor="end">
          {points.at(-1)?.xLabel ?? ""}
        </text>
      </svg>
    </div>
  );
}

function statusStyles(estado?: string): { color: string; label: string } {
  const map: Record<string, string> = {
    disponible: "#f1c40f",
    arrendada: "#2ecc71",
    en_venta: "#3498db",
    arrendada_en_venta: "#9b59b6",
    mantencion: "#e67e22",
    suspendida: "#95a5a6",
    baja: "#e74c3c",
  };
  const key = (estado || "").toLowerCase();
  return { color: map[key] || "#7f8c8d", label: estado || "" };
}

function DashCard({
  id,
  title,
  children,
  onExpand,
}: {
  id: CardId;
  title: string;
  children: ReactNode;
  onExpand: (id: CardId) => void;
}) {
  return (
    <section className="dash-card" aria-label={title}>
      <div className="dash-card-head">
        <span className="dash-card-head-title">{title}</span>
        <button className="dash-expand" onClick={() => onExpand(id)} type="button">
          Expandir
        </button>
      </div>
      <div className="dash-card-body">{children}</div>
    </section>
  );
}

export default function Dashboard({ properties, fullProperties, geojson, onSelectProperty, onDeleteProperty, filters, onChangeFilters, alertsData, paymentsSummary, showFilters }: DashboardProps) {
  const [expanded, setExpanded] = useState<CardId | null>(null);

  const estados = [
    "todos",
    "disponible",
    "arrendada",
    "en_venta",
    "arrendada_en_venta",
    "mantencion",
    "suspendida",
    "baja",
  ];
  const tipos = ["todos", "casa", "departamento", "oficina", "local", "terreno"];

  const kpis = useMemo(() => {
    const arriendos = properties
      .map((p) => (typeof p.valor_arriendo === "number" ? p.valor_arriendo : null))
      .filter((n): n is number => n !== null);
    const ingresosPagados = paymentsSummary.monthTotal || 0;
    const ingresosFallback = arriendos.reduce((a, b) => a + b, 0);
    const ingresos = ingresosPagados || ingresosFallback;
    const gastos = Math.round(ingresos * 0.12);
    const comision = Math.round(ingresos * 0.08);
    const flujo = ingresos - gastos - comision;
    return {
      ingresos,
      gastos,
      comision,
      flujo,
      ingresos_pagados: ingresosPagados,
      variacion: properties.length ? Math.max(-25, Math.min(25, Math.round((properties.length % 7) * 3 - 10))) : 0,
    };
  }, [properties, paymentsSummary]);

  const lastReceiptLabel = useMemo(() => {
    const last = paymentsSummary.last;
    if (!last) return "Sin pagos registrados";
    const date = last.fecha_pago ? new Date(last.fecha_pago) : null;
    const dateLabel = date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString("es-CL") : "fecha s/d";
    const amount = typeof last.monto_pagado === "number" ? last.monto_pagado : Number(last.monto_pagado || 0);
    const amtLabel = amount ? formatMoney(amount) : "monto s/d";
    const medio = last.medio_pago || "medio s/d";
    const ref = last.referencia || "ref s/d";
    const prop = last.propertyCodigo ? ` · ${last.propertyCodigo}` : "";
    return `${amtLabel} · ${medio} · ${ref} · ${dateLabel}${prop}`;
  }, [paymentsSummary]);

  const byStatus = useMemo(
    () => groupCount(properties.map((p) => String(p.estado_actual ?? ""))),
    [properties]
  );
  const byType = useMemo(() => groupCount(properties.map((p) => String(p.tipo ?? ""))), [properties]);
  const byComuna = useMemo(() => groupCount(properties.map((p) => String(p.comuna ?? ""))), [properties]);

  const valueStats = useMemo(() => {
    const arriendos = properties.map((p) => (p.valor_arriendo ?? null)).filter((n): n is number => typeof n === "number");
    const ventas = properties.map((p) => (p.valor_venta ?? null)).filter((n): n is number => typeof n === "number");

    const avg = (arr: number[]) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);

    return {
      total: properties.length,
      withRent: arriendos.length,
      withSale: ventas.length,
      avgRent: avg(arriendos),
      avgSale: avg(ventas),
    };
  }, [properties]);

  const publishedSeries = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of properties) {
      const raw = (p as any).fecha_publicacion as string | undefined;
      if (!raw) continue;
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    const keys = Array.from(counts.keys()).sort();
    const last = keys.slice(-6);
    return last.map((k) => ({ xLabel: k, y: counts.get(k) || 0 }));
  }, [properties]);

  const expandedTitle =
    expanded === "map"
      ? "Mapa"
      : expanded === "list"
        ? "Lista"
        : expanded === "byStatus"
          ? "Por estado"
          : expanded === "byType"
            ? "Por tipo"
            : expanded === "byComuna"
              ? "Por comuna"
              : expanded === "values"
                ? "Valores"
                : expanded === "published"
                  ? "Publicaciones"
                  : "";

  const handleFilterChange = (key: keyof typeof filters, value: string) => {
    onChangeFilters({ ...filters, [key]: value });
  };

  return (
    <>
      {showFilters && (
        <div className="filter-bar">
          <div className="filter-group">
            <label>Estado</label>
            <select value={filters.estado} onChange={(e) => handleFilterChange("estado", e.target.value)}>
              {estados.map((e) => (
                <option key={e} value={e}>
                  {e === "todos" ? "Todos" : e.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>Tipo</label>
            <select value={filters.tipo} onChange={(e) => handleFilterChange("tipo", e.target.value)}>
              {tipos.map((t) => (
                <option key={t} value={t}>
                  {t === "todos" ? "Todos" : t}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label>Comuna</label>
            <input
              value={filters.comuna}
              onChange={(e) => handleFilterChange("comuna", e.target.value)}
              placeholder="Buscar comuna"
            />
          </div>
          <button className="dash-mini" type="button" onClick={() => onChangeFilters({ estado: "todos", tipo: "todos", comuna: "" })}>
            Limpiar filtros
          </button>
        </div>
      )}

      <div className="dash-layout">
        <div className="dash-grid">
          <section className="dash-card" aria-label="Resumen financiero">
          <div className="dash-card-head">
            <span className="dash-card-head-title">Resumen financiero</span>
          </div>
          <div className="kpi-grid">
            <div className="kpi">
              <div className="kpi-label">Ingresos del mes</div>
              <div className="kpi-value">{kpis.ingresos ? formatMoney(kpis.ingresos) : "-"}</div>
              {paymentsSummary.monthCount > 0 && (
                <div className="kpi-pill pos">{paymentsSummary.monthCount} pago(s)</div>
              )}
            </div>
            <div className="kpi">
              <div className="kpi-label">Gastos</div>
              <div className="kpi-value">{kpis.gastos ? formatMoney(kpis.gastos) : "-"}</div>
            </div>
            <div className="kpi">
              <div className="kpi-label">Comisión</div>
              <div className="kpi-value">{kpis.comision ? formatMoney(kpis.comision) : "-"}</div>
            </div>
            <div className="kpi">
              <div className="kpi-label">Flujo neto</div>
              <div className="kpi-value">{kpis.flujo ? formatMoney(kpis.flujo) : "-"}</div>
              <div className={`kpi-pill ${kpis.variacion >= 0 ? "pos" : "neg"}`}>
                {kpis.variacion >= 0 ? "+" : ""}
                {kpis.variacion}% vs mes prev.
              </div>
            </div>
          </div>
          <div className="kpi-note">{lastReceiptLabel}</div>
          </section>
          <DashCard id="map" title="Mapa" onExpand={setExpanded}>
            <MapView data={geojson} onSelect={onSelectProperty} className="dash-map" />
          </DashCard>

          <DashCard id="list" title="Propiedades" onExpand={setExpanded}>
            <div className="dash-table">
              <div className="dash-table-head">
                <span>Dirección</span>
                <span>Estado</span>
              </div>
              {properties.slice(0, 8).map((p) => (
                <div key={p.id} className="dash-table-row" onClick={() => onSelectProperty(p.id)} role="button" tabIndex={0}>
                  <span className="dash-address" title={p.direccion_linea1}>
                    {p.direccion_linea1}
                  </span>
                  <span className="dash-state-chip" title={statusStyles(p.estado_actual).label.replace(/_/g, " ")}>
                    <span
                      className="dash-state-dot"
                      style={{ backgroundColor: statusStyles(p.estado_actual).color }}
                      aria-label={statusStyles(p.estado_actual).label.replace(/_/g, " ") || "Estado"}
                    />
                  </span>
                </div>
              ))}
              {properties.length > 8 && <div className="dash-hint">Expandir para ver todas</div>}
            </div>
          </DashCard>

          <DashCard id="byStatus" title="Estados" onExpand={setExpanded}>
            <BarChart title="Propiedades por estado" data={byStatus} />
          </DashCard>

          <DashCard id="byType" title="Tipos" onExpand={setExpanded}>
            <BarChart title="Propiedades por tipo" data={byType} />
          </DashCard>

          <DashCard id="values" title="Valores" onExpand={setExpanded}>
            <div className="dash-chart">
              <div className="dash-card-title">Valores y cobertura</div>
              <div className="dash-stats">
                <StatRow label="Total" value={String(valueStats.total)} />
                <StatRow label="Con arriendo" value={String(valueStats.withRent)} />
                <StatRow label="Con venta" value={String(valueStats.withSale)} />
                <StatRow label="Prom. arriendo" value={valueStats.avgRent ? formatMoney(valueStats.avgRent) : "-"} />
                <StatRow label="Prom. venta" value={valueStats.avgSale ? formatMoney(valueStats.avgSale) : "-"} />
              </div>
            </div>
          </DashCard>

          <DashCard id="published" title="Publicación" onExpand={setExpanded}>
            <LineChart
              title="Publicaciones (últimos meses)"
              points={publishedSeries.length ? publishedSeries : [{ xLabel: "-", y: 0 }]}
            />
          </DashCard>

          <DashCard id="byComuna" title="Comunas" onExpand={setExpanded}>
            <BarChart title="Cantidad por comuna" data={byComuna} maxBars={10} />
          </DashCard>
        </div>

        <aside className="dash-sidebar" aria-label="Panel lateral">
          <section className="dash-card" aria-label="Alertas operativas">
            <div className="dash-card-head">
              <span className="dash-card-head-title">Alertas operativas</span>
            </div>
            <div className="alerts-grid">
              {[{ label: "Arriendos vencidos", value: alertsData.vencidos }, { label: "Contratos por vencer", value: alertsData.porVencer }, { label: "Propiedades sin contrato", value: alertsData.sinContrato }, { label: "Cobranzas atrasadas", value: alertsData.cobranzaAtrasada }, { label: "Docs incompletos", value: alertsData.docsIncompletos }].map((a) => (
                <div key={a.label} className={`alert-chip ${a.value > 0 ? "alert-on" : "alert-off"}`}>
                  <div className="alert-label">{a.label}</div>
                  <div className="alert-value">{a.value}</div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>

      {expanded && (
        <div className="modal-backdrop" onClick={() => setExpanded(null)}>
          <div className="modal dash-expanded" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{expandedTitle}</h3>
              <button className="ghost" onClick={() => setExpanded(null)} type="button">
                Cerrar
              </button>
            </div>

            {expanded === "map" && <MapView data={geojson} onSelect={onSelectProperty} className="dash-map-expanded" />}

            {expanded === "list" && (
              <div className="dash-table expanded">
                <div className="dash-table-head">
                  <span>Código</span>
                  <span>Dirección</span>
                  <span>Estado</span>
                  <span>Tipo</span>
                  <span>Comuna</span>
                  <span></span>
                </div>
                {properties.map((p) => (
                  <div
                    key={p.id}
                    className="dash-table-row"
                    onClick={() => onSelectProperty(p.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <span>{p.codigo}</span>
                    <span>{p.direccion_linea1}</span>
                    <span className={`badge ${p.estado_actual}`}>{p.estado_actual}</span>
                    <span>{p.tipo}</span>
                    <span>{p.comuna}</span>
                    <button
                      type="button"
                      className="dash-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteProperty(p.id);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}

            {expanded === "byStatus" && <BarChart title="Propiedades por estado" data={byStatus} maxBars={999} />}
            {expanded === "byType" && <BarChart title="Propiedades por tipo" data={byType} maxBars={999} />}
            {expanded === "byComuna" && <BarChart title="Cantidad por comuna" data={byComuna} maxBars={999} />}
            {expanded === "values" && (
              <div className="dash-chart">
                <div className="dash-card-title">Valores y cobertura</div>
                <div className="dash-stats">
                  <StatRow label="Total" value={String(valueStats.total)} />
                  <StatRow label="Con arriendo" value={String(valueStats.withRent)} />
                  <StatRow label="Con venta" value={String(valueStats.withSale)} />
                  <StatRow label="Prom. arriendo" value={valueStats.avgRent ? formatMoney(valueStats.avgRent) : "-"} />
                  <StatRow label="Prom. venta" value={valueStats.avgSale ? formatMoney(valueStats.avgSale) : "-"} />
                </div>
              </div>
            )}
            {expanded === "published" && (
              <LineChart
                title="Publicaciones (últimos meses)"
                points={publishedSeries.length ? publishedSeries : [{ xLabel: "-", y: 0 }]}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
