import { ReactNode, useMemo, useState } from "react";
import MapView from "./MapView";
import type { Property } from "../api";

type DashboardProps = {
  properties: Property[];
  geojson: any;
  onSelectProperty: (id: string) => void;
  onDemoSeed: () => void;
  creating: boolean;
  onDeleteProperty: (id: string) => void;
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

export default function Dashboard({ properties, geojson, onSelectProperty, onDemoSeed, creating, onDeleteProperty }: DashboardProps) {
  const [expanded, setExpanded] = useState<CardId | null>(null);

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

  return (
    <>
      <div className="dash-grid">
        <DashCard id="map" title="Mapa" onExpand={setExpanded}>
          <MapView data={geojson} onSelect={onSelectProperty} className="dash-map" />
        </DashCard>

        <DashCard id="list" title="Propiedades" onExpand={setExpanded}>
          <div className="dash-list-head">
            <button className="dash-mini" onClick={onDemoSeed} disabled={creating} type="button">
              {creating ? "Cargando..." : "Cargar demo"}
            </button>
          </div>
          <div className="dash-table">
            <div className="dash-table-head">
              <span>Código</span>
              <span>Dirección</span>
              <span>Estado</span>
                <span>Comuna</span>
                <span></span>
            </div>
            {properties.slice(0, 8).map((p) => (
              <div key={p.id} className="dash-table-row" onClick={() => onSelectProperty(p.id)} role="button" tabIndex={0}>
                <span>{p.codigo}</span>
                <span title={p.direccion_linea1}>{p.direccion_linea1}</span>
                <span className={`badge ${p.estado_actual}`}>{p.estado_actual}</span>
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
