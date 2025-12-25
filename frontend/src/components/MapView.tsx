import { MapContainer, TileLayer, Marker, Popup, Tooltip } from "react-leaflet";
import L from "leaflet";

const stateColors: Record<string, string> = {
  arrendada: "#2ecc71",
  disponible: "#f1c40f",
  vendida: "#2980b9",
  en_venta: "#5dade2",
  desocupada: "#e74c3c",
  mantencion: "#e67e22",
  litigio: "#9b59b6",
  inactiva: "#7f8c8d",
};

function iconFor(state: string) {
  const color = stateColors[state] || "#34495e";
  return L.divIcon({
    className: "marker-icon",
    html: `<span style="background:${color}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

type MapViewProps = { data: any; onSelect?: (id: string) => void };

function MapView({ data, onSelect }: MapViewProps) {
  const center = data.features?.length
    ? [data.features[0].geometry.coordinates[1], data.features[0].geometry.coordinates[0]]
    : [-33.45, -70.66];

  return (
    <MapContainer center={center as any} zoom={12} className="map">
      <TileLayer
        attribution="&copy; OpenStreetMap"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {data.features?.map((f: any) => (
        <Marker
          key={f.properties.id}
          position={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
          icon={iconFor(f.properties.estado)}
          eventHandlers={{ click: () => onSelect?.(f.properties.id) }}
        >
          <Tooltip>
            {`${f.properties.codigo} · ${f.properties.estado} · ${f.properties.comuna}`}
          </Tooltip>
          <Popup>
            <div className="popup">
              <strong>{f.properties.codigo}</strong>
              <div>{f.properties.direccion}</div>
              <div>{f.properties.tipo} · {f.properties.comuna}</div>
              <div>Estado: {f.properties.estado}</div>
              {f.properties.arrendatario && <div>Arrendatario: {f.properties.arrendatario}</div>}
              {f.properties.proxima_cobranza && <div>Próxima cobranza: {new Date(f.properties.proxima_cobranza).toLocaleDateString()}</div>}
              {f.properties.fecha_fin_contrato && <div>Fin contrato: {new Date(f.properties.fecha_fin_contrato).toLocaleDateString()}</div>}
              {f.properties.valor_arriendo && <div>Arriendo: ${f.properties.valor_arriendo}</div>}
              {f.properties.valor_venta && <div>Venta: ${f.properties.valor_venta}</div>}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

export default MapView;
